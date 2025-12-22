"""
Document extraction class supporting multiple file formats with page-based chunking.
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from collections import defaultdict
import pytesseract
import fitz
import pymupdf
from fitz.table import find_tables
from pdf2image import convert_from_path
from unstructured.partition.text import partition_text

# from unstructured.partition.pdf import partition_pdf, partition_pdf_or_image
from unstructured.partition.docx import partition_docx
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Element
import PIL
from PIL.Image import Image
import io

from pyldev import _config_logger
from .FileExtractor import FileExtractor
from file import *


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
    SUPPORTED_FORMATS = {
        ".pdf": "_extract_pdf_ocr",
        ".docx": "_extract_docx",
        ".pptx": "_extract_pptx",
        ".doc": "_extract_doc",
    }

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

        self.logger = _config_logger(
            logs_name="FileExtractorDocument", logs_output=["console"]
        )

        self.chunk_max_char = chunk_max_char
        self.chunk_overlap = chunk_overlap
        self.ocr_lang = ocr_lang
        self.ocr_dpi = ocr_dpi
        self.group_by_page = group_by_page

    def extract(self, file_path: str) -> List[Dict[str, Any]]:
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

        def _group_chunks_by_page(
            chunks: List[Dict[str, Any]],
            separator: str = "\n\n",
        ) -> List[Dict[str, Any]]:
            """
            Group all chunks belonging to the same page into a single chunk.

            Args:
                chunks: List of chunk dictionaries
                separator: Separator to use when joining chunk texts

            Returns:
                List of grouped chunks (one per page)
            """
            pages = defaultdict(list)
            for chunk in chunks:
                page = chunk.get("metadata", {}).get("page_number")
                if page is None:
                    continue
                pages[page].append(chunk["text"])

            grouped = []
            for page_number in sorted(pages):
                grouped.append(
                    {
                        "text": separator.join(pages[page_number]).strip(),
                        "metadata": {"page_number": page_number},
                    }
                )

            return grouped

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = path.suffix.lower()
        if extension not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format: {extension}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS.keys())}"
            )

        chunks = []
        if file_path.endswith(".pdf"):
            chunks = self._extract_pdf(file_path=file_path)
        elif file_path.endswith(".docx"):
            chunks = self._extract_docx(file_path=file_path)
        if file_path.endswith(".odt"):
            chunks = self._extract_doc(file_path=file_path)

        return _group_chunks_by_page(chunks=chunks)

    def _extract_pdf(
        self, file_path: str, text_threshold: int = 20
    ) -> List[dict[str, Any]]:
        """
        Extract text from PDF using OCR (Tesseract).

        Parameters
        ----------
            file_path: Path to PDF file

        Returns:
            List of Element objects with page metadata
        """

        def _extract_page(
            self, page: fitz.Page, page_num: int, file_path: str
        ) -> List[Dict[str, Any]]:
            """
            Extract content from a single page using hybrid approach.
            """
            elements = []

            # Step 1: Try native text extraction
            native_text = page.get_text("text").strip()
            has_native_text = len(native_text) >= text_threshold

            if has_native_text:
                # Extract native text content with better structure
                text_elements = _extract_text(page, page_num)
                elements.extend(text_elements)

                table_elements = _extract_tables(page, page_num)
                elements.extend(table_elements)

            else:
                # Page is likely scanned - use OCR on entire page
                print(f"  Page {page_num}: Scanned content detected, applying OCR...")
                ocr_element = self._ocr_page(page, page_num)
                if ocr_element:
                    elements.append(ocr_element)

            # Step 2: Extract and OCR embedded images (even on pages with native text)
            image_elements = self._extract_and_ocr_images(page, page_num, file_path)
            elements.extend(image_elements)

            return elements

        def _extract_text(page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
            """
            Extract native text with paragraph-level structure.
            """
            elements = []

            # Use "blocks" to get text with layout information
            blocks = page.get_text("blocks")

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

                element = {
                    "text": text,
                    "type": "text",
                    "metadata": {
                        "page_number": page_num,
                        "source": "native",
                        "block_number": block_num,
                        "bbox": (x0, y0, x1, y1),
                    },
                }
                elements.append(element)

            return elements

        def _extract_tables(page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
            """
            Attempt to extract tables from page using PyMuPDF's table detection.
            Note: This is basic table detection. For advanced needs, consider using
            libraries like camelot-py or tabula-py.
            """
            elements = []

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
                        table_text = df.to_string(index=False)

                        element = {
                            "text": table_text,
                            "type": "table",
                            "metadata": {
                                "page_number": page_num,
                                "source": "native",
                                "table_number": table_num,
                                "rows": len(df),
                                "columns": len(df.columns),
                                "bbox": table.bbox,
                            },
                        }
                        elements.append(element)
                    except Exception as e:
                        print(
                            f"  Warning: Could not extract table {table_num} on page {page_num}: {e}"
                        )

            except AttributeError:
                # find_tables() not available in older PyMuPDF versions
                return []
            except Exception as e:
                print(f"  Warning: Table extraction failed on page {page_num}: {e}")
                return []

            return elements

        def _extract_images(
            page: fitz.Page, page_num: int, file_path: str
        ) -> List[Dict[str, Any]]:
            """
            Extract embedded images and apply OCR to them.
            """
            elements = []

            try:
                image_list = page.get_images(full=True)

                for img_index, img_info in enumerate(image_list):
                    try:
                        xref = img_info[0]

                        # Extract image
                        base_image = page.parent.extract_image(xref)
                        image_bytes = base_image["image"]

                        # Convert to PIL Image
                        imgage = PIL.Image.open(io.BytesIO(image_bytes))

                        # Apply OCR
                        text = pytesseract.image_to_string(
                            imgage, lang=self.ocr_lang
                        ).strip()

                        if text:
                            element = {
                                "text": text,
                                "type": "text",
                                "metadata": {
                                    "page_number": page_num,
                                    "source": "ocr_full_page",
                                    "ocr_lang": self.ocr_lang,
                                    "ocr_dpi": image.info["dpi"],
                                    "image_format": base_image["ext"],
                                    "image_size": (
                                        base_image["width"],
                                        base_image["height"],
                                    ),
                                },
                            }
                            elements.append(element)

                    except Exception as e:
                        print(
                            f"  Warning: Could not OCR image {img_index} on page {page_num}: {e}"
                        )
                        continue

            except Exception as e:
                print(f"  Warning: Image extraction failed on page {page_num}: {e}")

            return elements

        try:
            images = convert_from_path(
                file_path,
                dpi=self.ocr_dpi,
            )
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return []

        elements: List[dict[str, Any]] = []
        for page_num, img in enumerate(images, start=1):
            try:
                text = str(pytesseract.image_to_string(img, lang=self.ocr_lang)).strip()

                if not text:
                    continue

                element = {
                    "text": text,
                    "metadata": {
                        "page_number": page_num,
                        "source": "ocr",
                        "ocr_lang": self.ocr_lang,
                    },
                }
                elements.append(element)

            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
                continue

        return elements

    def _extract_docx(self, file_path: str) -> List[Element]:
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

    def _extract_doc(self, file_path: str) -> List[Element]:
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
