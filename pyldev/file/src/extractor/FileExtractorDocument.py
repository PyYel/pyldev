from __future__ import annotations
from typing import Optional, List, Dict, Any, Iterable
from io import BytesIO
import os
import shutil

# unstructured
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_to_dicts

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
        super().__init__()
        self.file_path = file_path
        self.file_bytes = file_bytes

        self.elements: List[Any] = []
        self.grouped_blocks: List[Dict[str, Any]] = []
        self.text_batches: List[str] = []

        # config
        self.prefer_hi_res = prefer_hi_res
        self.default_strategy = default_strategy
        self.chunk_size = int(chunk_size)
        self.chunk_overlap = int(chunk_overlap)



    # -------------------------
    # Choose partition strategy
    # -------------------------
    def _choose_pdf_strategy(self) -> str:
        """
        Choose PDF parsing strategy:
          - 'hi_res' : requires poppler (python-poppler / poppler-utils)
          - 'ocr_only': requires tesseract
          - 'fast' : safe default (pdfminer / text extraction)
        """
        # detect Poppler: poppler-utils includes `pdftoppm` or `pdftotext`
        has_pdftoppm = self._has_program("pdftoppm")
        has_pdftotext = self._has_program("pdftotext")
        has_tesseract = self._has_program("tesseract")

        if self.prefer_hi_res and (has_pdftoppm or has_pdftotext):
            return "hi_res"
        if has_tesseract:
            return "ocr_only"
        return self.default_strategy

    # -------------------------
    # Extract raw elements
    # -------------------------
    def _extract_elements(self, strategy: Optional[str] = None) -> List[Any]:
        """
        Uses unstructured.partition to extract elements.
        strategy: "hi_res", "fast", "ocr_only" or None -> auto for PDF
        """
        self._read_file()

        # If file_path is available and path extension exists, we can hint partition,
        # but partition(file=BytesIO) + strategy will handle it.
        if not strategy:
            # If file is PDF (by extension), pick pdf strategy detection
            ext = (os.path.splitext(self.file_path or "")[1] or "").lower()
            if ext == ".pdf":
                strategy = self._choose_pdf_strategy()
            else:
                # non-pdf: let unstructured choose best (None -> auto)
                strategy = None

        partition_kwargs = {}
        if strategy:
            partition_kwargs["strategy"] = strategy

        # unstructured accepts file=BytesIO or filename
        if self.file_path:
            # prefer passing filename for unstructured to detect type
            elements = partition(filename=self.file_path, **partition_kwargs)
        else:
            elements = partition(file=self.file_bytes, **partition_kwargs)

        # store
        self.elements = elements
        return elements

    # -------------------------
    # Convert to dicts (serializable)
    # -------------------------
    def to_dicts(self) -> List[Dict[str, Any]]:
        if not self.elements:
            self._extract_elements()
        return elements_to_dicts(self.elements)

    # -------------------------
    # Group elements into blocks
    # -------------------------
    def _group_elements(self, elements: Iterable[Any]) -> List[Dict[str, Any]]:
        """
        Group elements using:
         - explicit Titles / Headings -> start new block
         - page_number metadata -> page boundaries
         - small delimiter heuristics (horizontal rule, --- lines) to split
        Returns a list of blocks: {"title": Optional[str], "page": Optional[int], "content":[str], "meta": [...]}
        """
        blocks: List[Dict[str, Any]] = []
        current = {"title": None, "page": None, "content": [], "meta": []}

        for el in elements:
            # defensive: many unstructured elements provide .to_dict()
            try:
                el_dict = el.to_dict()
            except Exception:
                # fallback if element already dict-like
                el_dict = el if isinstance(el, dict) else {"text": str(el)}

            text = (el_dict.get("text") or "").strip()
            if not text:
                continue

            el_type = el_dict.get("type", "").lower()
            meta_page = el_dict.get("metadata", {}).get("page_number")

            # heading/title detection
            if el_type in ("title", "heading", "h1", "h2", "h3"):
                # push current if has content
                if current["content"]:
                    blocks.append(current)
                current = {"title": text, "page": meta_page, "content": [], "meta": [el_dict]}
                continue

            # delimiter lines heuristic
            if text.strip() in ("---", "***", "___") or (len(text) < 4 and set(text) <= set("-_=")):
                if current["content"]:
                    blocks.append(current)
                    current = {"title": None, "page": meta_page, "content": [], "meta": []}
                continue

            # page change
            if meta_page is not None and current["page"] is not None and meta_page != current["page"]:
                if current["content"]:
                    blocks.append(current)
                    current = {"title": None, "page": meta_page, "content": [], "meta": []}
                else:
                    current["page"] = meta_page

            # append
            current["content"].append(text)
            current["meta"].append(el_dict)

        if current["content"]:
            blocks.append(current)

        self.grouped_blocks = blocks
        return blocks

    # -------------------------
    # Build text blocks and optionally chunk them
    # -------------------------
    def _build_text_batches(self, blocks: List[Dict[str, Any]], chunk: bool = True) -> List[str]:
        """
        Convert grouped blocks into list[str].
        If chunk==True: split long blocks into overlapping char-based chunks.
        """
        batches: List[str] = []

        def _normalize_block(block: Dict[str, Any]) -> str:
            parts = []
            if block.get("title"):
                parts.append(block["title"])
            if block.get("page") is not None:
                parts.append(f"[Page {block['page']}]")
            parts.append("\n".join(block.get("content", [])))
            return "\n".join([p for p in parts if p]).strip()

        for block in blocks:
            text = _normalize_block(block)
            if not text:
                continue

            if not chunk or len(text) <= self.chunk_size:
                batches.append(text)
                continue

            # chunk large block into overlapping slices
            start = 0
            size = self.chunk_size
            overlap = min(self.chunk_overlap, size - 1)
            while start < len(text):
                end = start + size
                chunk_text = text[start:end].strip()
                if chunk_text:
                    batches.append(chunk_text)
                if end >= len(text):
                    break
                start = end - overlap

        self.text_batches = batches
        return batches

    # -------------------------
    # Public extract method (pipeline)
    # -------------------------
    def extract(self, *, strategy: Optional[str] = None, chunk: bool = True) -> List[str]:
        """
        Run the full pipeline:
         1) read_file()
         2) extract elements (strategy auto-detected for pdf)
         3) group by titles/pages/delimiters
         4) build text batches (with chunking/overlap)

        Parameters
        ----------
        strategy: Optional[str]
            Force partition strategy (e.g., "hi_res", "fast", "ocr_only"). If None, auto choose.
        chunk: bool
            Whether to chunk long blocks.
        """
        # 1. read
        self._read_file()

        # 2. extract elements (choose strategy if not provided)
        elements = self._extract_elements(strategy=strategy)

        # 3. group elements
        blocks = self._group_elements(elements)

        # 4. build batches
        batches = self._build_text_batches(blocks, chunk=chunk)

        return batches
