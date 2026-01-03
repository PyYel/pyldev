"""
Document extraction class supporting multiple file formats with page-based chunking.
Uses only open-source, commercially-friendly libraries.
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import pytesseract
import os
import sys
import io
import pandas as pd
import subprocess
import shutil

# PDF libraries - all open source
# from pdfplumber import open as plumber_open
import pdfplumber
from pdfplumber.page import Page
import pypdfium2 as pdfium
from pypdfium2 import PdfPage, PdfImage, PdfBitmap

from pyldev import _config_logger
from .FileExtractor import FileExtractor
from ..element import *


class FileExtractorDocument(FileExtractor):
    """
    Extracts content from various document formats with page-based chunking.
    Uses only open-source, commercially-friendly libraries.

    Supported formats:
    - PDF (with OCR via Tesseract)
    - DOCX (Microsoft Word)
    - ODT (LibreOffice)
    - DOC (via LibreOffice conversion)

    System dependencies:
    - tesseract-ocr: Required for OCR
    - libreoffice: Optional, only for .doc conversion
    """

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
        file_path: str
            Path to the document file

        Returns
        -------
        elements: List[FileElement]
            List of ``FileElement``.
        """

        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return []

        if not self._check_supported(extractor_type="document", file_path=file_path):
            return []

        elements = []
        if file_path.endswith(".pdf"):
            self.logger.info(
                f"Extracting from '{os.path.basename(file_path)}' using PDF methods."
            )
            elements = self._extract_pdf(file_path=file_path)
        else:
            self.logger.info(
                f"Extracting from '{os.path.basename(file_path)}' using PDF methods."
            )
            elements = self._extract_other(file_path=file_path)

        # elif file_path.endswith(".docx"):
        #     self.logger.info(
        #         f"Extracting from '{os.path.basename(file_path)}' using DOCX methods."
        #     )
        #     elements = self._extract_docx(file_path=file_path)
        # elif file_path.endswith(".odt") or file_path.endswith(".doc"):
        #     self.logger.info(
        #         f"Extracting from '{os.path.basename(file_path)}' using DOC/ODT methods."
        #     )
        #     elements = self._extract_doc(file_path=file_path)

        return elements

    def _extract_pdf(
        self, file_path: str, text_threshold: int = 20
    ) -> List[FileElement]:
        """
        Extract text from PDF.

        Parameters
        ----------
        file_path: str
            Path to PDF file.
        text_threshold: int
            Minimum characters to consider page as having native text.

        Returns
        -------
        elements: List[FileElement]
            List of ``FileElement``.
        """

        def _extract_text(page: Page, page_num: int) -> List[TextElement]:
            """
            Extract native text using pdfplumber with layout information.
            """
            elements: List[TextElement] = []

            try:
                words = page.extract_words()

                if not words:
                    return elements

                # Group words into text blocks by proximity
                lines = {}
                for word in words:
                    y = round(word["top"])  # Round to group nearby words
                    if y not in lines:
                        lines[y] = []
                    lines[y].append(word)

                # Sort lines by y-coordinate
                for y in sorted(lines.keys()):
                    line_words = sorted(lines[y], key=lambda w: w["x0"])
                    text = " ".join([w["text"] for w in line_words]).strip()

                    if not text:
                        continue

                    # Calculate bounding box for the line
                    x0 = min(w["x0"] for w in line_words)
                    y0 = min(w["top"] for w in line_words)
                    x1 = max(w["x1"] for w in line_words)
                    y1 = max(w["bottom"] for w in line_words)

                    self.logger.debug(f"Found native text from page {page_num}.")
                    element = TextElement.build(
                        content=self._sanitize_text(text),
                        source="native",
                        index=page_num,
                        bbox=(float(x0), float(y0), float(x1), float(y1)),
                    )
                    elements.append(element)

            except Exception as e:
                self.logger.warning(f"Error extracting text with pdfplumber: {e}")

            return elements

        def _extract_tables(page: Page, page_num: int) -> List[TableElement]:
            """
            Extract tables using pdfplumber's table detection.
            """
            elements: List[TableElement] = []

            try:
                tables = page.extract_tables()

                if not tables:
                    return elements

                for table_num, table_data in enumerate(tables):
                    try:
                        if not table_data or len(table_data) < 2:
                            continue

                        df = pd.DataFrame(table_data[1:], columns=table_data[0])
                        text = df.to_string(index=False)

                        self.logger.debug(f"Found native table from page {page_num}.")

                        element = TableElement.build(
                            content=self._sanitize_text(text),
                            source="native",
                            index=page_num,
                            columns=[str(col) for col in table_data[0]],
                            bbox=None,
                        )
                        elements.append(element)

                    except Exception as e:
                        self.logger.warning(
                            f"Could not extract table {table_num} on page {page_num}: {e}"
                        )

            except Exception as e:
                self.logger.error(f"Table extraction failed on page {page_num}: {e}")

            return elements

        def _extract_images(page: pdfium.PdfPage, page_num: int) -> List[ImageElement]:
            """
            Extract embedded images and applies OCR.
            """

            elements: List[ImageElement] = []

            try:

                page_objects = page.get_objects()

                for obj_index, obj in enumerate(page_objects):
                    try:
                        if isinstance(obj, PdfImage):
                            bitmap = obj.get_bitmap()
                            pil_image = bitmap.to_pil()

                            text = pytesseract.image_to_string(
                                pil_image, lang=self.ocr_lang
                            ).strip()

                            if not text:
                                continue

                            self.logger.debug(
                                f"Performed OCR on embedded image object {obj_index} from page {page_num}."
                            )

                            element = ImageElement.build(
                                content=self._sanitize_text(text),
                                index=page_num,
                                source="ocr",
                                ocr_lang=self.ocr_lang,
                                image_size=obj.get_px_size(),
                            )
                            elements.append(element)

                    except Exception as e:
                        self.logger.warning(
                            f"Image extraction failed on page {page_num} for object {obj_index}: {e}"
                        )

            except Exception as e:
                self.logger.error(
                    f"PDF loading page {page_num} failed before image extaction: {e}"
                )

            return elements

        def _extract_page(page: pdfium.PdfPage, page_num: int) -> List[ImageElement]:
            """
            Convert PDF page to image and apply OCR.
            """
            elements: List[ImageElement] = []

            try:

                # Render page to bitmap
                # scale: 1.0 = 72 DPI, 2.0 = 144 DPI, 4.0 = 288 DPI
                bitmap: PdfBitmap = page.render(
                    scale=4,
                    rotation=0,
                )

                image = bitmap.to_pil()

                text = pytesseract.image_to_string(image, lang=self.ocr_lang).strip()

                if not text:
                    return elements

                self.logger.debug(f"Performed OCR on page {page_num}.")
                element = ImageElement.build(
                    content=self._sanitize_text(text),
                    index=page_num,
                    source="ocr",
                    ocr_lang=self.ocr_lang,
                    image_format=".pdf",
                    image_size=(image.width, image.height),
                )
                elements.append(element)

            except Exception as e:
                self.logger.error(f"Could not OCR page {page_num}: {e}")

            return elements

        # =====================
        # PDF EXTRACTION LOGIC
        # =====================

        if not os.path.exists(file_path):
            self.logger.error(f"PDF not found: {file_path}")
            return []

        elements: List[FileElement] = []

        try:

            # Open as bytes to prevent concurring opening conflicts
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            pdfium_pdf = pdfium.PdfDocument(file_path, autoclose=True)

            # Open with pdfplumber for better extraction
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as plumber_pdf:

                # This gets pdf plumber page
                for page_num, plumber_page in enumerate(plumber_pdf.pages, start=1):
                    # This gets pdfium page
                    pdfium_page = pdfium_pdf.get_page(
                        page_num - 1
                    )  # pdfplumber index starts at 1

                    # Check if page has native text
                    native_text = plumber_page.extract_text()
                    has_native_text = (
                        native_text and len(native_text.strip()) >= text_threshold
                    )

                    if has_native_text:
                        self.logger.debug(
                            f"Extracting content from '{os.path.basename(file_path)}' page {page_num}."
                        )

                        # Extract text with layout
                        text_elements = _extract_text(plumber_page, page_num)
                        elements.extend(text_elements)

                        # Extract tables
                        table_elements = _extract_tables(plumber_page, page_num)
                        elements.extend(table_elements)

                        # Extract images (limited functionality)
                        image_elements = _extract_images(pdfium_page, page_num)
                        elements.extend(image_elements)

                    else:
                        # Page is likely scanned - use OCR on entire page
                        self.logger.debug(
                            f"Performing OCR scan from '{os.path.basename(file_path)}' page {page_num}."
                        )
                        ocr_elements = _extract_page(pdfium_page, page_num)
                        elements.extend(ocr_elements)

            pdfium_pdf.close()

        except Exception as e:
            self.logger.error(f"Error processing PDF {file_path}: {e}")
            return []

        return elements

    def _extract_other(self, file_path: str) -> List[FileElement]:
        """
        Converts a document to PDF using LibreOffice,
        keeps the PDF, then extracts content from it.
        """

        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        input_path = os.path.abspath(file_path)
        input_dir = os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        pdf_path = os.path.join(input_dir, f"{base_name}.pdf")

        os.makedirs(input_dir, exist_ok=True)

        soffice_bin = self._get_soffice_path()
        if not soffice_bin:
            self.logger.error("LibreOffice (soffice/libreoffice) not found on PATH")
            return []
        
        cmd = [
            soffice_bin,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            input_dir,
            input_path,
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"LibreOffice conversion failed: {e.stderr}")
            return []

        if not os.path.exists(pdf_path):
            self.logger.error(f"PDF was not created: {pdf_path}")
            return []

        return self._extract_pdf(file_path=pdf_path)
