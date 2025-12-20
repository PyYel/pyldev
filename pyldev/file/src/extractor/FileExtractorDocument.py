"""
Document extraction class supporting multiple file formats with page-based chunking.
"""
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from collections import defaultdict
import pytesseract
from pdf2image import convert_from_path
from unstructured.partition.text import partition_text
from unstructured.partition.docx import partition_docx
from unstructured.partition.pptx import partition_pptx
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Element

from .FileExtractor import FileExtractor

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
        '.pdf': '_extract_pdf_ocr',
        '.docx': '_extract_docx',
        '.pptx': '_extract_pptx',
        '.doc': '_extract_doc',
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
            chunks = self._extract_pdf_ocr(file_path=file_path)
        
        return self._group_chunks_by_page(chunks=chunks)
    
    
    def _group_chunks_by_page(
        self,
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
            grouped.append({
                "text": separator.join(pages[page_number]).strip(),
                "metadata": {"page_number": page_number},
            })
        
        return grouped
    
    
    def _extract_pdf_ocr(self, file_path: str) -> List[dict[str, Any]]:
        """
        Extract text from PDF using OCR (Tesseract).
        
        Parameters
        ----------
            file_path: Path to PDF file
            
        Returns:
            List of Element objects with page metadata
        """
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
                text = str(pytesseract.image_to_string(
                    img, 
                    lang=self.ocr_lang
                )).strip()
                
                if not text:
                    continue
                
                element = {
                    "text": text,
                    "metadata": {
                        "page_number": page_num, 
                        "source": "ocr",
                        "ocr_lang": self.ocr_lang,
                    }
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
                if hasattr(el, 'category') and el.category == "PageBreak":
                    page_number += 1
                    continue
                
                # Set page number in metadata
                if not hasattr(el.metadata, 'page_number') or el.metadata.page_number is None:
                    el.metadata.page_number = page_number
            
            # Filter out page break elements
            elements = [el for el in elements if getattr(el, 'category', None) != "PageBreak"]
            
            return elements
            
        except Exception as e:
            print(f"Error extracting DOCX: {e}")
            return []
    
    def _extract_pptx(self, file_path: str) -> List[Element]:
        """
        Extract text from PPTX file (each slide is a page).
        
        Parameters
        ----------
            file_path: Path to PPTX file
            
        Returns:
            List of Element objects with slide numbers as page metadata
        """
        try:
            elements = partition_pptx(
                filename=file_path,
                include_page_breaks=True,
            )
            
            # Track slide numbers
            slide_number = 1
            for el in elements:
                # Page breaks indicate new slides in PPTX
                if hasattr(el, 'category') and el.category == "PageBreak":
                    slide_number += 1
                    continue
                
                # Set slide number as page number
                if not hasattr(el.metadata, 'page_number') or el.metadata.page_number is None:
                    el.metadata.page_number = slide_number
            
            # Filter out page break elements
            elements = [el for el in elements if getattr(el, 'category', None) != "PageBreak"]
            
            return elements
            
        except Exception as e:
            print(f"Error extracting PPTX: {e}")
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
                if hasattr(el, 'category') and el.category == "PageBreak":
                    page_number += 1
                    continue
                
                if not hasattr(el.metadata, 'page_number') or el.metadata.page_number is None:
                    el.metadata.page_number = page_number
            
            elements = [el for el in elements if getattr(el, 'category', None) != "PageBreak"]
            
            return elements
            
        except Exception as e:
            print(f"Error extracting DOC: {e}")
            print("Note: DOC format may require additional dependencies or conversion tools.")
            return []

