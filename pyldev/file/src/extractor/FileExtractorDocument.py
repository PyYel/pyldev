"""
Document extraction class supporting multiple file formats with page-based chunking.
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import pytesseract
import fitz
import pymupdf
from fitz.table import find_tables
from pdf2image import convert_from_path
import os, sys

from unstructured.partition.docx import partition_docx

import PIL
from PIL import Image
import io

from pyldev import _config_logger
from .FileExtractor import FileExtractor
from ..element import *


class FileExtractorDocument(FileExtractor):
    """
    Extracts content from various document formats with page-based chunking.

    Supported formats:
    - PDF (with OCR via Tesseract)
    - DOCX (Microsoft Word)
    - PPTX (Microsoft PowerPoint)
    - DOC (via conversion, if available)
    """

    # Supported file extensions mapped to extraction methods

    def __init__(
        self,
        chunk_max_char: int = 1000,
        chunk_overlap: int = 100,
        ocr_lang: str = "eng",
        ocr_dpi: int = 300,
        group_by_page: bool = True,
    ):
        """
        Initialize the document extractor.

        Parameters
        ----------
        chunk_max_char
            Maximum characters per chunk
        chunk_overlap:
            Character overlap between chunks
        ocr_lang:
            Tesseract language code (e.g., 'eng', 'fra', 'eng+fra')
        ocr_dpi:
            DPI for PDF to image conversion
        group_by_page:
            If True, merge all chunks per page into single text
        """
        super().__init__()

        self.logger = _config_logger(logs_name="FileExtractorDocument")

        self.chunk_max_char = chunk_max_char
        self.chunk_overlap = chunk_overlap
        self.ocr_lang = ocr_lang
        self.ocr_dpi = ocr_dpi
        self.group_by_page = group_by_page

    def extract(self, file_path: str) -> List[FileElement]:
        """
        Extract content from a document file with page-based chunking.

        Parameters
        ----------
            file_path: Path to the document file

        Returns:
            List of dictionaries containing:
                - type: Element type (Title, Text, Page, etc.)
                - text: Extracted text content
                - metadata: Dict with page_number and other metadata

        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file does not exist
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self._check_supported(extractor_type="document", file_path=file_path)
        elements = []
        if file_path.endswith(".pdf"):
            self.logger.info(
                f"Extracting from '{os.path.basename(file_path)}' using PDF methods."
            )
            elements = self._extract_pdf(file_path=file_path)
        elif file_path.endswith(".docx"):
            self.logger.info(
                f"Extracting from '{os.path.basename(file_path)}' using DOCX methods."
            )
            elements = self._extract_docx(file_path=file_path)
        if file_path.endswith(".odt"):
            self.logger.info(
                f"Extracting from '{os.path.basename(file_path)}' using DOC methods."
            )
            elements = self._extract_doc(file_path=file_path)

        return elements

    def _extract_pdf(
        self, file_path: str, text_threshold: int = 20
    ) -> List[FileElement]:
        """
        Extract text from PDF using OCR (Tesseract).

        Parameters
        ----------
            file_path: Path to PDF file

        Returns:
            List of Element objects with page metadata
        """

        def _extract_text(page: fitz.Page, page_num: int) -> List[TextElement]:
            """
            Extract native text with paragraph-level structure.
            """

            # Use "blocks" to get text with layout information
            blocks = page.get_text("blocks")
            elements: List[TextElement] = []
            for block_num, block in enumerate(blocks):
                # block format: (x0, y0, x1, y1, "text", block_no, block_type)
                if len(block) < 5:
                    continue

                x0, y0, x1, y1, text, block_no, block_type = block[:7]

                # block_type: 0 = text, 1 = image
                if block_type != 0:
                    continue

                text = text.strip()
                if not text:
                    continue

                self.logger.debug(f"Found native text from page {page_num}.")
                element = TextElement.build(
                    content=self._sanitize_text(text),
                    source="native",
                    index=page_num,
                    bbox=(float(x0), float(y0), float(x1), float(y1)),
                )
                elements.append(element)

            return elements

        def _extract_tables(page: fitz.Page, page_num: int) -> List[TableElement]:
            """
            Attempt to extract tables from page using PyMuPDF's table detection.
            Note: This is basic table detection. For advanced needs, consider using
            libraries like camelot-py or tabula-py.
            """
            elements: List[TableElement] = []

            try:
                # PyMuPDF 1.23.0+ has find_tables()
                # tables = page.find_tables()
                table_finder = fitz.table.find_tables(page=page)
                if table_finder is None:
                    return []

                for table_num, table in enumerate(table_finder.tables):
                    # Extract table as pandas DataFrame or raw data
                    try:
                        df = table.to_pandas()
                        text = df.to_string(index=False)

                        self.logger.debug(f"Found native table from page {page_num}.")
                        element = TableElement.build(
                            content=self._sanitize_text(text),
                            source="native",
                            index=page_num,
                            columns=df.columns.to_list(),
                            bbox=table.bbox,
                        )
                        elements.append(element)

                    except Exception as e:
                        self.logger.warning(
                            f"Could not extract table {table_num} on page {page_num}: {e}"
                        )

            except AttributeError:
                # find_tables() not available in older PyMuPDF versions
                return []
            except Exception as e:
                self.logger.error(f"Table extraction failed on page {page_num}: {e}")
                return []

            return elements

        def _extract_images(page: fitz.Page, page_num: int) -> List[ImageElement]:
            """
            Extract embedded images and apply OCR to them.
            """
            elements: List[ImageElement] = []

            try:
                image_list = page.get_images(full=True)

                for img_index, img_info in enumerate(image_list):
                    try:
                        xref = img_info[0]

                        # Extract image
                        base_image = page.parent.extract_image(xref)
                        image_bytes = base_image["image"]

                        # Convert to PIL Image
                        image = Image.open(io.BytesIO(image_bytes))

                        # Apply OCR
                        text = pytesseract.image_to_string(
                            image, lang=self.ocr_lang
                        ).strip()

                        if text is None:
                            continue

                        self.logger.debug(
                            f"Performed OCR on embedded image from page {page_num}."
                        )
                        element = ImageElement.build(
                            content=text,
                            index=page_num,
                            source="ocr",
                            ocr_lang=self.ocr_lang,
                            image_format=base_image["ext"],
                            image_size=(
                                base_image["width"],
                                base_image["height"],
                            ),
                        )
                        elements.append(element)

                    except Exception as e:
                        self.logger.error(
                            f"Could not OCR image {img_index} on page {page_num}: {e}"
                        )
                        continue

            except Exception as e:
                print(f"  Warning: Image extraction failed on page {page_num}: {e}")

            return elements

        def _extract_scan(page: fitz.Page, page_num: int) -> List[ImageElement]:
            """
            Extract embedded images and apply OCR to them.
            """
            elements: List[ImageElement] = []

            try:
                # Convert page to image
                pix = page.get_pixmap(dpi=self.ocr_dpi)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                # Apply OCR
                text = pytesseract.image_to_string(img, lang=self.ocr_lang).strip()

                if text is None:
                    return []

                self.logger.debug(f"Performed OCR on scanned page {page_num}.")
                element = ImageElement.build(
                    content=text,
                    index=page_num,
                    source="ocr",
                    ocr_lang=self.ocr_lang,
                    image_format=".pdf",
                    image_size=(
                        pix.width,
                        pix.height,
                    ),
                )
                elements.append(element)
                return elements

            except Exception as e:
                self.logger.error(f"Could not OCR scanned page {page_num}: {e}")
                return []

        # =====================
        # PDF EXTRACTION LOGIC
        # =====================

        if not os.path.exists(file_path):
            self.logger.error(f"PDF not found: {file_path}")
            return []

        elements: List[FileElement] = []
        try:
            doc = fitz.open(file_path)

            for page_num in range(len(doc)):

                page = doc[page_num]

                native_text = page.get_text("text").strip()
                has_native_text = len(native_text) >= text_threshold

                # Page has readable content
                if has_native_text:
                    self.logger.info(
                        f"Extracting readable text from '{os.path.basename(file_path)}' page {page_num}."
                    )
                    text_elements = _extract_text(page, page_num)
                    elements.extend(text_elements)

                    table_elements = _extract_tables(page, page_num)
                    elements.extend(table_elements)

                    image_elements = _extract_images(page, page_num)
                    elements.extend(image_elements)

                # Page is likely scanned - use OCR on entire page
                else:
                    self.logger.info(
                        f"Performing OCR scan from '{os.path.basename(file_path)}' page {page_num}."
                    )
                    ocr_element = _extract_scan(page, page_num)
                    elements.extend(ocr_element)

            doc.close()

        except Exception as e:
            self.logger.error(f"Error processing PDF {file_path}: {e}")
            return []

        return elements

    def _extract_docx(self, file_path: str) -> List[FileElement]:
        """
        Extract text from DOCX file.

        Parameters
        ----------
            file_path: Path to DOCX file

        Returns:
            List of Element objects with page metadata
        """
        try:
            elements = partition_docx(
                filename=file_path,
                include_page_breaks=True,
            )

            # Add page numbers based on page breaks
            page_number = 1
            for el in elements:
                # Check if element is a page break
                if hasattr(el, "category") and el.category == "PageBreak":
                    page_number += 1
                    continue

                # Set page number in metadata
                if (
                    not hasattr(el.metadata, "page_number")
                    or el.metadata.page_number is None
                ):
                    el.metadata.page_number = page_number

            # Filter out page break elements
            elements = [
                el for el in elements if getattr(el, "category", None) != "PageBreak"
            ]

            return elements

        except Exception as e:
            print(f"Error extracting DOCX: {e}")
            return []

    def _extract_doc(self, file_path: str) -> List[FileElement]:
        """
        Extract text from DOC file (legacy Word format).

        Note: This requires conversion to DOCX first, which may need
        additional tools like LibreOffice or antiword.

        Parameters
        ----------
            file_path: Path to DOC file

        Returns:
            List of Element objects with page metadata
        """
        try:
            # Try using unstructured's auto partition which handles DOC
            from unstructured.partition.auto import partition

            elements = partition(
                filename=file_path,
                include_page_breaks=True,
            )

            # Process page numbers similar to DOCX
            page_number = 1
            for el in elements:
                if hasattr(el, "category") and el.category == "PageBreak":
                    page_number += 1
                    continue

                if (
                    not hasattr(el.metadata, "page_number")
                    or el.metadata.page_number is None
                ):
                    el.metadata.page_number = page_number

            elements = [
                el for el in elements if getattr(el, "category", None) != "PageBreak"
            ]

            return elements

        except Exception as e:
            print(f"Error extracting DOC: {e}")
            print(
                "Note: DOC format may require additional dependencies or conversion tools."
            )
            return []
