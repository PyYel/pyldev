from __future__ import annotations
from typing import Optional, List, Dict, Any, Iterable
from io import BytesIO
import os
import shutil

# unstructured
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_to_dicts
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.text import partition_text
from unstructured.chunking.basic import chunk_elements

# Optional OCR fallback (pure Python wrappers only)
from pdf2image import convert_from_path
import pytesseract

from .FileExtractor import FileExtractor


class FileExtractorDocument2(FileExtractor):
    """
    A fully automatic extractor with:
        - unstructured.partition.pdf for native text
        - OCR fallback when needed (pytesseract + pdf2image)
        - unstructured.chunking.basic for automatic chunk segmentation
    """
    def __init__(
        self,
        ocr_fallback: bool = True,
        ocr_lang: list[str] = ["eng"],
        chunk_max_char: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        super().__init__()
        self.ocr_fallback = ocr_fallback
        self.ocr_lang = ocr_lang
        self.chunk_max_char = chunk_max_char
        self.chunk_overlap = chunk_overlap

    def extract(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Returns list of chunk dicts:
            {
                "type": <element type>,
                "text": <clean chunk>,
                "metadata": { page_number, ... }
            }
        """

        def _is_empty(elements) -> bool:
            if not elements:
                return True
            for el in elements:
                if hasattr(el, "text") and el.text and el.text.strip():
                    return False
            return True
        
        # 1. Attempt native extraction using unstructured
        elements = self._extract_unstructured_native(file_path)
        if _is_empty(elements) and self.ocr_fallback:
            elements = self._extract_ocr_pipeline(file_path)

        # Safety fallback
        if _is_empty(elements):
            return []

        # 2. Chunking (layout-aware)
        chunks = chunk_elements(
            elements,
            max_characters=self.chunk_max_char,
            overlap=self.chunk_overlap,
        )


        # 3. Convert unstructured elements into a simple dict structure
        chunks_dicts = [
            {
                "type": c.category if hasattr(c, "category") else "Text",
                "text": c.text.strip().encode(),
                # "metadata": getattr(c, "metadata", {})
            }
            for c in chunks
            if getattr(c, "text", "").strip()
        ]

        return chunks_dicts
    
    # ----------------------------------------------------------------------
    # Internal: unstructured native extractor
    # ----------------------------------------------------------------------
    def _extract_unstructured_native(self, file_path: str):
        try:
            # enable_ocr=False ensures pure text extraction
            return partition_pdf(
                filename=file_path,
                strategy="fast",
                infer_table_structure=True,
                extract_images=False,
                extract_image_block_types=None,
                include_page_breaks=False,
                languages=self.ocr_lang,
                ocr_strategy="never",
            )
        except Exception:
            return []

    # ----------------------------------------------------------------------
    # Internal: OCR fallback using pure Python wrappers
    # ----------------------------------------------------------------------
    def _extract_ocr_pipeline(self, file_path: str):
        text_pages = []

        try:
            images = convert_from_path(file_path, dpi=300)
        except Exception as e:
            
            return []

        for page_num, img in enumerate(images, start=1):
            txt = pytesseract.image_to_string(img, lang=self.ocr_lang)
            clean = txt.strip()
            if clean:
                text_pages.append((page_num, clean))

        # convert to unstructured text elements
        elements = []
        for page_num, page_text in text_pages:
            elements.extend(
                partition_text(text=page_text, metadata={"page_number": page_num})
            )

        return elements

