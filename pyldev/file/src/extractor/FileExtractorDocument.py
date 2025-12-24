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
                        self.logger.warning(f"Image extraction failed on page {page_num} for object {obj_index}: {e}")

            except Exception as e:
                self.logger.error(f"PDF loading page {page_num} failed before image extaction: {e}")

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
                    pdfium_page = pdfium_pdf.get_page(page_num-1) # pdfplumber index starts at 1

                    # Check if page has native text
                    native_text = plumber_page.extract_text()
                    has_native_text = (
                        native_text and len(native_text.strip()) >= text_threshold
                    )

                    if has_native_text:
                        self.logger.info(
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
                        self.logger.info(
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
        Converts a document to PDF using LibreOffice.
        Returns the path to the generated PDF.
        """

        input_path = file_path
        output_dir = os.path.join(os.path.dirname(file_path))

        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            input_path,
        ]

        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        pdf_name = Path(input_path).with_suffix(".pdf").name
        pdf_path = os.path.join(output_dir, pdf_name)

        return self._extract_pdf(file_path=pdf_path)


    # def _extract_docx(self, file_path: str) -> List[FileElement]:
    #     """
    #     Extract text, tables, and images from DOCX files.
    #     Uses python-docx (MIT License) for structured extraction and OCR for embedded images.

    #     Parameters
    #     ----------
    #         file_path: Path to DOCX file

    #     Returns:
    #         List of Element objects with page/paragraph metadata
    #     """

    #     def _extract_text_and_tables(
    #         doc: Document,
    #     ) -> tuple[List[TextElement], List[TableElement]]:
    #         """
    #         Extract text paragraphs and tables from the document.
    #         """

    #         text_elements: List[TextElement] = []
    #         table_elements: List[TableElement] = []

    #         element_index = 0

    #         for block in doc.element.body:
    #             # Handle paragraphs
    #             if block.tag.endswith("p"):
    #                 para_obj = None
    #                 # Find corresponding paragraph object
    #                 for para in doc.paragraphs:
    #                     if para._element == block:
    #                         para_obj = para
    #                         break

    #                 if para_obj and para_obj.text.strip():
    #                     text = para_obj.text.strip()

    #                     self.logger.debug(
    #                         f"Found text paragraph at index {element_index}."
    #                     )
    #                     element = TextElement.build(
    #                         content=self._sanitize_text(text),
    #                         source="native",
    #                         index=element_index,
    #                     )
    #                     text_elements.append(element)
    #                     element_index += 1

    #             # Handle tables
    #             elif block.tag.endswith("tbl"):
    #                 table_obj = None
    #                 # Find corresponding table object
    #                 for table in doc.tables:
    #                     if table._element == block:
    #                         table_obj = table
    #                         break

    #                 if table_obj:
    #                     try:
    #                         # Extract table data
    #                         data = []
    #                         for row in table_obj.rows:
    #                             row_data = [cell.text.strip() for cell in row.cells]
    #                             data.append(row_data)

    #                         if data and len(data) > 1:  # At least header + one row
    #                             # Convert to string representation
    #                             df = pd.DataFrame(data[1:], columns=data[0])
    #                             text = df.to_string(index=False)

    #                             self.logger.debug(
    #                                 f"Found table at index {element_index}."
    #                             )
    #                             element = TableElement.build(
    #                                 content=self._sanitize_text(text),
    #                                 source="native",
    #                                 index=element_index,
    #                                 columns=data[0],
    #                             )
    #                             table_elements.append(element)
    #                             element_index += 1

    #                     except Exception as e:
    #                         self.logger.warning(
    #                             f"Could not extract table at index {element_index}: {e}"
    #                         )

    #         return text_elements, table_elements

    #     def _extract_images(file_path: str) -> List[ImageElement]:
    #         """
    #         Extract embedded images from DOCX and apply OCR.
    #         DOCX files are ZIP archives containing images in word/media/.
    #         """
    #         elements: List[ImageElement] = []

    #         try:
    #             with zipfile.ZipFile(file_path, "r") as docx_zip:
    #                 # List all files in the media directory
    #                 media_files = [
    #                     name
    #                     for name in docx_zip.namelist()
    #                     if name.startswith("word/media/")
    #                 ]

    #                 for img_index, media_file in enumerate(media_files):
    #                     try:
    #                         # Read image data
    #                         image_data = docx_zip.read(media_file)

    #                         # Determine image format from filename
    #                         ext = os.path.splitext(media_file)[1].lower()
    #                         if ext not in [
    #                             ".png",
    #                             ".jpg",
    #                             ".jpeg",
    #                             ".gif",
    #                             ".bmp",
    #                             ".tiff",
    #                         ]:
    #                             continue

    #                         image = Image.open(io.BytesIO(image_data))

    #                         text = pytesseract.image_to_string(
    #                             image, lang=self.ocr_lang
    #                         ).strip()

    #                         if not text:
    #                             continue

    #                         self.logger.debug(
    #                             f"Performed OCR on embedded image {img_index}."
    #                         )
    #                         element = ImageElement.build(
    #                             content=self._sanitize_text(text),
    #                             index=img_index,
    #                             source="ocr",
    #                             ocr_lang=self.ocr_lang,
    #                             image_format=ext,
    #                             image_size=(image.width, image.height),
    #                         )
    #                         elements.append(element)

    #                     except Exception as e:
    #                         self.logger.error(
    #                             f"Could not OCR image {img_index} ({media_file}): {e}"
    #                         )
    #                         continue

    #         except Exception as e:
    #             self.logger.error(f"Error extracting images from DOCX: {e}")

    #         return elements

    #     # =====================
    #     # DOCX EXTRACTION LOGIC
    #     # =====================

    #     if not os.path.exists(file_path):
    #         self.logger.error(f"DOCX file not found: {file_path}")
    #         return []

    #     elements: List[FileElement] = []

    #     try:

    #         self.logger.info(
    #             f"Extracting content from '{os.path.basename(file_path)}'."
    #         )

    #         # Load document
    #         doc = docx.Document(file_path)

    #         # Extract text and tables
    #         text_elements, table_elements = _extract_text_and_tables(doc)
    #         elements.extend(text_elements)
    #         elements.extend(table_elements)

    #         # Extract and OCR images
    #         image_elements = _extract_images(file_path)
    #         elements.extend(image_elements)

    #     except Exception as e:
    #         self.logger.error(f"Error processing DOCX {file_path}: {e}")
    #         return []

    #     return elements

    # def _extract_doc(self, file_path: str) -> List[FileElement]:
    #     """
    #     Extract text, tables, and images from DOC files (legacy Word format).
    #     Uses LibreOffice to convert to DOCX first, then processes as DOCX.
    #     Also handles ODT (LibreOffice) files.

    #     Parameters
    #     ----------
    #         file_path: Path to DOC or ODT file

    #     Returns:
    #         List of Element objects with page/paragraph metadata
    #     """

    #     def _extract_text_from_odt(file_path: str) -> List[TextElement]:
    #         """
    #         Extract text from ODT using direct XML parsing.
    #         ODT files are ZIP archives with content in content.xml.
    #         """
    #         elements: List[TextElement] = []

    #         try:
    #             with zipfile.ZipFile(file_path, "r") as odt_zip:
    #                 # Read the content.xml file
    #                 content_xml = odt_zip.read("content.xml")

    #                 # Parse XML
    #                 root = etree.fromstring(content_xml)

    #                 # Define namespaces
    #                 namespaces = {
    #                     "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    #                     "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    #                 }

    #                 element_index = 0

    #                 # Extract text paragraphs
    #                 for para in root.xpath("//text:p", namespaces=namespaces):
    #                     text = "".join(para.itertext()).strip()
    #                     if text:
    #                         self.logger.debug(
    #                             f"Found text paragraph at index {element_index}."
    #                         )
    #                         element = TextElement.build(
    #                             content=self._sanitize_text(text),
    #                             source="native",
    #                             index=element_index,
    #                         )
    #                         elements.append(element)
    #                         element_index += 1

    #         except Exception as e:
    #             self.logger.error(f"Error extracting text from ODT: {e}")

    #         return elements

    #     def _extract_images_from_odt(file_path: str) -> List[ImageElement]:
    #         """
    #         Extract embedded images from ODT and apply OCR.
    #         ODT files are ZIP archives containing images in Pictures/.
    #         """
    #         elements: List[ImageElement] = []

    #         try:
    #             with zipfile.ZipFile(file_path, "r") as odt_zip:
    #                 # List all files in the Pictures directory
    #                 image_files = [
    #                     name
    #                     for name in odt_zip.namelist()
    #                     if name.startswith("Pictures/")
    #                 ]

    #                 for img_index, image_file in enumerate(image_files):
    #                     try:
    #                         # Read image data
    #                         image_data = odt_zip.read(image_file)

    #                         # Determine image format
    #                         ext = os.path.splitext(image_file)[1].lower()
    #                         if ext not in [
    #                             ".png",
    #                             ".jpg",
    #                             ".jpeg",
    #                             ".gif",
    #                             ".bmp",
    #                             ".tiff",
    #                         ]:
    #                             continue

    #                         # Convert to PIL Image
    #                         image = Image.open(io.BytesIO(image_data))

    #                         # Apply OCR
    #                         text = pytesseract.image_to_string(
    #                             image, lang=self.ocr_lang
    #                         ).strip()

    #                         if not text:
    #                             continue

    #                         self.logger.debug(
    #                             f"Performed OCR on embedded image {img_index}."
    #                         )
    #                         element = ImageElement.build(
    #                             content=self._sanitize_text(text),
    #                             index=img_index,
    #                             source="ocr",
    #                             ocr_lang=self.ocr_lang,
    #                             image_format=ext,
    #                             image_size=(image.width, image.height),
    #                         )
    #                         elements.append(element)

    #                     except Exception as e:
    #                         self.logger.error(
    #                             f"Could not OCR image {img_index} ({image_file}): {e}"
    #                         )
    #                         continue

    #         except Exception as e:
    #             self.logger.error(f"Error extracting images from ODT: {e}")

    #         return elements

    #     def _convert_doc_to_docx(input_path: str, output_path: str) -> bool:
    #         """
    #         Convert DOC to DOCX using LibreOffice in headless mode.
    #         """
    #         try:
    #             import subprocess

    #             output_dir = os.path.dirname(output_path)
    #             if not output_dir:
    #                 output_dir = "."

    #             # Use LibreOffice to convert
    #             result = subprocess.run(
    #                 [
    #                     "soffice",
    #                     "--headless",
    #                     "--convert-to",
    #                     "docx",
    #                     "--outdir",
    #                     output_dir,
    #                     input_path,
    #                 ],
    #                 capture_output=True,
    #                 text=True,
    #                 timeout=60,
    #             )

    #             if result.returncode != 0:
    #                 self.logger.error(f"LibreOffice conversion failed: {result.stderr}")
    #                 return False

    #             # Check if output file was created
    #             base_name = os.path.splitext(os.path.basename(input_path))[0]
    #             expected_output = os.path.join(output_dir, f"{base_name}.docx")

    #             if os.path.exists(expected_output):
    #                 if expected_output != output_path:
    #                     os.rename(expected_output, output_path)
    #                 return True

    #             return False

    #         except Exception as e:
    #             self.logger.error(f"Error converting DOC to DOCX: {e}")
    #             return False

    #     # =====================
    #     # DOC/ODT EXTRACTION LOGIC
    #     # =====================

    #     if not os.path.exists(file_path):
    #         self.logger.error(f"Document file not found: {file_path}")
    #         return []

    #     elements: List[FileElement] = []
    #     file_ext = os.path.splitext(file_path)[1].lower()

    #     try:
    #         # Handle ODT files directly
    #         if file_ext == ".odt":
    #             self.logger.info(
    #                 f"Extracting content from ODT '{os.path.basename(file_path)}'."
    #             )

    #             text_elements = _extract_text_from_odt(file_path)
    #             elements.extend(text_elements)

    #             image_elements = _extract_images_from_odt(file_path)
    #             elements.extend(image_elements)

    #         # Handle DOC files by converting to DOCX
    #         elif file_ext == ".doc":
    #             self.logger.info(
    #                 f"Converting DOC to DOCX: '{os.path.basename(file_path)}'."
    #             )

    #             # Create temporary DOCX file
    #             temp_docx = file_path.replace(".doc", "_temp.docx")

    #             if _convert_doc_to_docx(file_path, temp_docx):
    #                 self.logger.info(f"Extracting content from converted DOCX.")

    #                 # Extract from converted DOCX
    #                 elements = self._extract_docx(temp_docx)

    #                 # Clean up temporary file
    #                 try:
    #                     os.remove(temp_docx)
    #                 except:
    #                     pass
    #             else:
    #                 self.logger.error(f"Failed to convert DOC to DOCX: {file_path}")
    #                 return []

    #         else:
    #             self.logger.error(f"Unsupported file format: {file_ext}")
    #             return []

    #     except Exception as e:
    #         self.logger.error(f"Error processing document {file_path}: {e}")
    #         return []

    #     return elements
