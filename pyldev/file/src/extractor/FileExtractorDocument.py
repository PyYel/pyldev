from __future__ import annotations
from typing import Optional, List, Dict, Any, Iterable
from io import BytesIO
import os
import shutil
from collections import defaultdict

# unstructured
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.text import partition_text
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Image as ImageElement

from pdf2image import convert_from_path
from PIL import Image
import pytesseract

# Base class import (assume present)
from .FileExtractor import FileExtractor



class FileExtractorDocument(FileExtractor):
    """
    Document extractor that:
      - reads bytes/path
      - selects parsing strategy (hi_res / fast / ocr_only) based on system capabilities
      - extracts elements via unstructured.partition
      - groups elements by page/title/delimiters
      - builds text batches ready for RAG ingestion (with optional chunking)
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        file_bytes: Optional[BytesIO] = None,
        prefer_hi_res: bool = True,
        default_strategy: str = "fast",  # fallback strategy
        chunk_size: int = 2000,          # char-based chunk size for batching
        chunk_overlap: int = 200         # char overlap between chunks
    ) -> None:
        """
        """
        super().__init__()

        self.file_path = file_path
        self.chunk_max_char = 1000
        self.chunk_overlap = chunk_overlap
        self.ocr_fallback = True
        self.ocr_lang = "eng"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, force_ocr: bool = False) -> List[Dict[str, Any]]:
        elements = self._extract_with_fallback(self.file_path, force_ocr=force_ocr)
        if not elements:
            return []

        # Group elements by page
        page_map: Dict[int, list] = {}
        for el in elements:
            page = getattr(el.metadata, "page_number", None) #or el.metadata.get("page_number")
            if page is None:
                continue
            page_map.setdefault(page, []).append(el)

        chunks_dicts: List[Dict[str, Any]] = []

        # Chunk per page (guarantees duplication across pages if needed)
        for page_number, page_elements in sorted(page_map.items()):
            page_chunks = chunk_elements(
                page_elements,
                max_characters=self.chunk_max_char,
                overlap=self.chunk_overlap,
            )

            for c in page_chunks:
                text = getattr(c, "text", "").strip()
                if not text:
                    continue

                chunks_dicts.append(
                    {
                        "type": getattr(c, "category", "Text"),
                        "text": text,
                        "metadata": {
                            "page_number": page_number,
                        },
                    }
                )
        chunks_dicts = self._group_chunks_by_page(chunks=chunks_dicts)
        return chunks_dicts


    def _group_chunks_by_page(self,
        chunks: List[Dict[str, Any]],
        separator: str = "\n\n",
    ) -> List[Dict[str, Any]]:
        """
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
                    "type": "Page",
                    "text": separator.join(pages[page_number]).strip(),
                    "metadata": {"page_number": page_number},
                }
            )

        return grouped
    # ------------------------------------------------------------------
    # Extraction orchestration
    # ------------------------------------------------------------------

    def _extract_with_fallback(self, file_path: str, force_ocr: bool = False):
        
        # Extract tex and images
        if not force_ocr:
            elements = self._extract_unstructured_native(file_path)
        else: 
            elements = []
        
        # Image only OCR
        if elements and self.ocr_fallback:
            elements = self._ocr_image_elements(elements)

        # Full document OCR for scanned docs, ...
        if (self.ocr_fallback and self._is_effectively_empty(elements)) or force_ocr:
            elements = self._extract_pdf_ocr(file_path)
            print(elements)

        return elements

    # ------------------------------------------------------------------
    # Native PDF extraction (no OCR)
    # ------------------------------------------------------------------

    def _extract_unstructured_native(self, file_path: str):
        try:
            return partition_pdf(
                filename=file_path,
                strategy="fast",
                languages=["en"],
                infer_table_structure=True,
                extract_images=True,
                extract_image_block_types=["Image"],
                include_page_breaks=False,
                ocr_strategy="never",
            )
        except Exception:
            return []

    # ------------------------------------------------------------------
    # OCR only image elements
    # ------------------------------------------------------------------

    def _ocr_image_elements(self, elements):
        processed = []

        for el in elements:
            if isinstance(el, ImageElement):
                image_path = getattr(el.metadata, "image_path", None) #or el.metadata.get("page_number")
                page_number = getattr(el.metadata, "page_number", None) #or el.metadata.get("page_number")

                if not image_path:
                    continue

                try:
                    img = Image.open(image_path)
                    text = pytesseract.image_to_string(
                        img, lang=self.ocr_lang
                    ).strip()
                except Exception:
                    continue

                if text:
                    processed.extend(
                        partition_text(
                            text=text,
                            metadata={
                                "page_number": page_number,
                                "source": "image_ocr",
                            },
                        )
                    )
            else:
                processed.append(el)

        return processed

    # ------------------------------------------------------------------
    # Full-page OCR fallback (last resort)
    # ------------------------------------------------------------------

    def _extract_pdf_ocr(self, file_path: str):
        try:
            images = convert_from_path(file_path, dpi=300)
        except Exception as e:
            print(e)
            return []
        print(len(images))
        elements = []

        for page_num, img in enumerate(images, start=1):
            text = pytesseract.image_to_string(
                img, lang=self.ocr_lang
            ).strip()

            if not text:
                continue

            elements.extend(
                partition_text(
                    text=text,
                    metadata={"page_number": page_num, "source": "page_ocr"},
                )
            )

        return elements

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_effectively_empty(elements) -> bool:
        if not elements:
            return True
        for el in elements:
            if getattr(el, "text", "").strip():
                return False
        return True