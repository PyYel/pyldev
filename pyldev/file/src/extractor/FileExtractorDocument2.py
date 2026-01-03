"""
Unified Document Extraction Pipeline:
ALL formats → Markdown (with structure) → PDF → Structured chunks with page metadata

This approach provides:
1. Consistent structure extraction across all document types
2. Rich semantic chunking based on document hierarchy
3. Page-accurate metadata for PDF display
4. Single source of truth (markdown) for all processing
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pytesseract
import os
import sys
import io
import json
import subprocess
import shutil
import tempfile
import re
from dataclasses import dataclass, field

# PDF libraries
import pdfplumber
from pdfplumber.page import Page
import pypdfium2 as pdfium

from pyldev import _config_logger
from .FileExtractor import FileExtractor
from ..element import *


@dataclass
class StructuralChunk:
    """
    A chunk with both structural and page metadata.
    """
    content: str
    page_numbers: List[int]
    section: Optional[str] = None
    section_level: Optional[int] = None
    chunk_type: str = "text"  # text, code, list, table
    header_hierarchy: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileExtractorDocument2(FileExtractor):
    """
    Unified extraction pipeline:
    Input → Markdown (structure extraction) → PDF (page mapping) → Structured chunks
    
    Benefits:
    - Consistent structure extraction across all formats
    - Rich semantic metadata
    - Page-accurate references
    - Clean markdown intermediate representation
    
    Supported formats:
    - PDF, DOCX, DOC, ODT, TXT, Markdown, HTML, and more
    
    System dependencies:
    - pandoc: Required for format conversion and structure extraction
    - libreoffice: Optional fallback for some formats
    - tesseract-ocr: Optional for OCR on scanned PDFs
    """

    def __init__(
        self,
        chunk_max_char: int = 1000,
        chunk_overlap: int = 100,
        ocr_lang: str = "eng",
        preserve_hierarchy: bool = True,
        cache_intermediates: bool = True,
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize the unified document extractor.

        Parameters
        ----------
        chunk_max_char
            Maximum characters per chunk
        chunk_overlap
            Character overlap between chunks
        ocr_lang
            Tesseract language code for OCR
        preserve_hierarchy
            If True, include full header hierarchy in chunks
        cache_intermediates
            If True, cache markdown and PDF files
        cache_dir
            Directory for caching (default: temp directory)
        """
        super().__init__()

        self.logger = _config_logger(logs_name="FileExtractorDocument")

        self.chunk_max_char = chunk_max_char
        self.chunk_overlap = chunk_overlap
        self.ocr_lang = ocr_lang
        self.preserve_hierarchy = preserve_hierarchy
        self.cache_intermediates = cache_intermediates
        
        # Setup cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "doc_extractor_cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Check for required dependencies
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required tools are available."""
        self.has_pandoc = shutil.which("pandoc") is not None
        self.has_libreoffice = shutil.which("soffice") is not None or shutil.which("libreoffice") is not None
        self.has_tesseract = shutil.which("tesseract") is not None

        if not self.has_pandoc:
            raise RuntimeError(
                "Pandoc is required for this pipeline. "
                "Install: sudo apt-get install pandoc texlive-xetex"
            )

        if not self.has_tesseract:
            self.logger.warning("Tesseract not found. OCR will not be available.")

    def extract(self, file_path: str) -> Tuple[List[StructuralChunk], str, str]:
        """
        Extract structured chunks from any document format.

        Parameters
        ----------
        file_path: str
            Path to the input document

        Returns
        -------
        chunks: List[StructuralChunk]
            Structured chunks with page and semantic metadata
        markdown_path: str
            Path to the intermediate markdown file
        pdf_path: str
            Path to the final PDF file
        """

        if not os.path.exists(file_path):
            self.logger.error(f"File not found: {file_path}")
            return [], "", ""

        base_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_path)[-1].lower()

        if not self._check_supported(extractor_type="document", file_path=file_path):
            return [], "", ""

        self.logger.info(f"Starting unified extraction for: {base_name}")

        # Step 1: Convert to Markdown
        self.logger.info("Step 1: Converting to Markdown...")
        markdown_path = self._convert_to_markdown(file_path)
        
        if not markdown_path or not os.path.exists(markdown_path):
            self.logger.error("Failed to convert to markdown")
            return [], "", ""

        # Step 2: Extract structure from Markdown
        self.logger.info("Step 2: Extracting document structure...")
        structure = self._extract_structure_from_markdown(markdown_path)

        # Step 3: Convert Markdown to PDF
        self.logger.info("Step 3: Converting Markdown to PDF...")
        pdf_path = self._convert_markdown_to_pdf(markdown_path)
        
        if not pdf_path or not os.path.exists(pdf_path):
            self.logger.error("Failed to convert markdown to PDF")
            return [], markdown_path, ""

        # Step 4: Map structure to page numbers
        self.logger.info("Step 4: Mapping structure to page numbers...")
        page_mapping = self._map_structure_to_pages(structure, pdf_path)

        # Step 5: Create structured chunks
        self.logger.info("Step 5: Creating structured chunks...")
        chunks = self._create_structured_chunks(structure, page_mapping)

        self.logger.info(f"Extraction complete. Generated {len(chunks)} chunks.")

        return chunks, str(markdown_path), str(pdf_path)

    def _convert_to_markdown(self, file_path: str) -> Optional[str]:
        """
        Convert any document format to Markdown using Pandoc.
        
        Parameters
        ----------
        file_path: str
            Path to input file
            
        Returns
        -------
        markdown_path: Optional[str]
            Path to generated markdown file
        """
        
        base_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_path)[-1].lower()
        
        markdown_path = os.path.join(self.cache_dir, f"{base_name}.md")

        # If already markdown, just copy it
        if file_ext in [".md", ".markdown"]:
            shutil.copy(file_path, markdown_path)
            self.logger.info(f"Using existing markdown: {base_name}")
            return str(markdown_path)

        # Special handling for PDF - extract text first
        if file_ext == ".pdf":
            return self._pdf_to_markdown(file_path, markdown_path)

        # For other formats, use Pandoc
        try:
            cmd = [
                "pandoc",
                str(file_path),
                "-o", str(markdown_path),
                "--wrap=none",  # Don't wrap lines
                "--extract-media", os.path.join(os.path.dirname(markdown_path), "media"),  # Extract images
            ]

            # Add format-specific options
            if file_ext in [".docx", ".odt", ".doc"]:
                cmd.extend([
                    "--standalone",
                    "--preserve-tabs",
                ])
            elif file_ext in [".html", ".htm"]:
                cmd.extend([
                    "--from=html",
                ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                self.logger.error(f"Pandoc conversion to markdown failed: {result.stderr}")
                return None

            if not markdown_path.exists():
                self.logger.error(f"Markdown file was not created: {markdown_path}")
                return None

            self.logger.info(f"Converted {base_name} to markdown")
            return str(markdown_path)

        except subprocess.TimeoutExpired:
            self.logger.error(f"Pandoc conversion timed out for {file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error converting to markdown: {e}")
            return None

    def _pdf_to_markdown(self, pdf_path: str, output_path: str) -> Optional[str]:
        """
        Convert PDF to Markdown, preserving structure where possible.
        
        Parameters
        ----------
        pdf_path: Path
            Path to PDF file
        output_path: Path
            Path for output markdown
            
        Returns
        -------
        markdown_path: Optional[str]
            Path to generated markdown
        """
        
        try:
            # First try: Use pandoc if PDF has selectable text
            cmd = [
                "pandoc",
                str(pdf_path),
                "-o", str(output_path),
                "--wrap=none",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                # Check if we got meaningful content
                with open(output_path, "rb") as f:
                    content = f.read().decode(encoding="utf-8")

                if len(content.strip()) > 100:  # At least some content
                    self.logger.info("Converted PDF to markdown using pandoc")
                    return str(output_path)
            
            # Fallback: Extract text with pdfplumber and structure it
            self.logger.info("Falling back to pdfplumber for PDF extraction")
            return self._pdf_to_markdown_fallback(pdf_path, output_path)
            
        except Exception as e:
            self.logger.error(f"Error converting PDF to markdown: {e}")
            return self._pdf_to_markdown_fallback(pdf_path, output_path)

    def _pdf_to_markdown_fallback(self, pdf_path: str, output_path: str) -> Optional[str]:
        """
        Extract text from PDF and structure it as markdown.
        
        Parameters
        ----------
        pdf_path: Path
            Path to PDF file
        output_path: Path
            Path for output markdown
            
        Returns
        -------
        markdown_path: Optional[str]
            Path to generated markdown
        """
        
        try:
            markdown_lines = []
            markdown_lines.append(f"# {os.path.basename(pdf_path)}\n\n")
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    
                    if not text:
                        continue
                    
                    # Add page marker
                    markdown_lines.append(f"## Page {page_num}\n\n")
                    
                    # Try to detect structure (very basic)
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Detect potential headers (all caps, short lines)
                        if len(line) < 60 and line.isupper() and not line.endswith('.'):
                            markdown_lines.append(f"### {line}\n\n")
                        else:
                            markdown_lines.append(f"{line}\n\n")
            
            # Write to file
            with open(output_path, "w") as f:
                f.write("".join(markdown_lines))

            self.logger.info(f"Extracted PDF to markdown with {len(markdown_lines)} lines")
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"PDF to markdown fallback failed: {e}")
            return None

    def _extract_structure_from_markdown(self, markdown_path: str) -> Dict[str, Any]:
        """
        Extract document structure using Pandoc AST.
        
        Parameters
        ----------
        markdown_path: str
            Path to markdown file
            
        Returns
        -------
        structure: Dict[str, Any]
            Document structure with hierarchical information
        """
        
        try:
            # Convert to Pandoc JSON AST
            cmd = [
                "pandoc",
                markdown_path,
                "-t", "json",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                self.logger.error(f"Failed to extract structure: {result.stderr}")
                return {"blocks": [], "headers": [], "sections": []}
            
            ast = json.loads(result.stdout)
            
            # Parse AST into structured representation
            structure = self._parse_pandoc_ast(ast)
            
            self.logger.info(
                f"Extracted structure: {len(structure['headers'])} headers, "
                f"{len(structure['sections'])} sections"
            )
            
            return structure
            
        except Exception as e:
            self.logger.error(f"Error extracting structure: {e}")
            return {"blocks": [], "headers": [], "sections": []}

    def _parse_pandoc_ast(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Pandoc AST into a structured representation.
        
        Parameters
        ----------
        ast: Dict[str, Any]
            Pandoc JSON AST
            
        Returns
        -------
        structure: Dict[str, Any]
            Parsed structure with sections, headers, and content
        """
        
        structure = {
            "blocks": [],
            "headers": [],
            "sections": [],
        }
        
        current_section = None
        header_stack = []  # Track header hierarchy
        
        def extract_text(inlines: List[Dict]) -> str:
            """Extract plain text from inline elements."""
            text_parts = []
            for inline in inlines:
                inline_type = inline.get("t", "")
                if inline_type == "Str":
                    text_parts.append(inline["c"])
                elif inline_type == "Space":
                    text_parts.append(" ")
                elif inline_type == "Code":
                    text_parts.append(f"`{inline['c'][1]}`")
                elif inline_type in ["Emph", "Strong", "Strikeout"]:
                    text_parts.append(extract_text(inline["c"]))
            return "".join(text_parts)
        
        def process_block(block: Dict, block_index: int):
            """Process a single block element."""
            nonlocal current_section, header_stack
            
            block_type = block.get("t", "")
            
            if block_type == "Header":
                level = block["c"][0]
                text = extract_text(block["c"][2])
                
                # Update header stack
                # Remove headers at same or deeper level
                header_stack = [h for h in header_stack if h["level"] < level]
                header_stack.append({"level": level, "text": text})
                
                header_info = {
                    "level": level,
                    "text": text,
                    "block_index": block_index,
                    "hierarchy": [h["text"] for h in header_stack],
                }
                
                structure["headers"].append(header_info)
                
                # Start new section
                if current_section:
                    structure["sections"].append(current_section)
                
                current_section = {
                    "header": text,
                    "level": level,
                    "hierarchy": header_info["hierarchy"].copy(),
                    "start_block": block_index,
                    "blocks": [],
                }
            
            elif block_type == "Para":
                text = extract_text(block["c"])
                block_info = {
                    "type": "paragraph",
                    "content": text,
                    "block_index": block_index,
                }
                structure["blocks"].append(block_info)
                if current_section:
                    current_section["blocks"].append(block_info)
            
            elif block_type == "CodeBlock":
                language = ""
                if block["c"][0][1]:
                    language = block["c"][0][1][0]
                code = block["c"][1]
                
                block_info = {
                    "type": "code",
                    "language": language,
                    "content": code,
                    "block_index": block_index,
                }
                structure["blocks"].append(block_info)
                if current_section:
                    current_section["blocks"].append(block_info)
            
            elif block_type in ["BulletList", "OrderedList"]:
                list_type = "bullet" if block_type == "BulletList" else "ordered"
                
                # Extract list items
                items = []
                list_items = block["c"] if block_type == "BulletList" else block["c"][1]
                
                for item in list_items:
                    item_text_parts = []
                    for item_block in item:
                        if item_block.get("t") == "Para":
                            item_text_parts.append(extract_text(item_block["c"]))
                    items.append(" ".join(item_text_parts))
                
                block_info = {
                    "type": "list",
                    "list_type": list_type,
                    "items": items,
                    "content": "\n".join(f"- {item}" for item in items),
                    "block_index": block_index,
                }
                structure["blocks"].append(block_info)
                if current_section:
                    current_section["blocks"].append(block_info)
            
            elif block_type == "Table":
                block_info = {
                    "type": "table",
                    "content": "[Table content]",  # Simplified for now
                    "block_index": block_index,
                }
                structure["blocks"].append(block_info)
                if current_section:
                    current_section["blocks"].append(block_info)
        
        # Process all blocks
        blocks = ast.get("blocks", [])
        for idx, block in enumerate(blocks):
            process_block(block, idx)
        
        # Add final section
        if current_section:
            structure["sections"].append(current_section)
        
        return structure

    def _convert_markdown_to_pdf(self, markdown_path: str) -> Optional[str]:
        """
        Convert markdown to PDF with proper formatting.
        
        Parameters
        ----------
        markdown_path: str
            Path to markdown file
            
        Returns
        -------
        pdf_path: Optional[str]
            Path to generated PDF
        """
        
        
        pdf_path = self.cache_dir / f"{os.path.splitext(markdown_path)[0]}.pdf"
        
        try:
            cmd = [
                "pandoc",
                str(markdown_path),
                "-o", str(pdf_path),
                "--pdf-engine=xelatex",
                "-V", "geometry:margin=1in",
                "-V", "fontsize=11pt",
                "-V", "linestretch=1.2",
                "--highlight-style=tango",
                "--number-sections",  # Number sections for easier reference
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode != 0:
                self.logger.error(f"Pandoc PDF conversion failed: {result.stderr}")
                return None
            
            if not pdf_path.exists():
                self.logger.error(f"PDF was not created: {pdf_path}")
                return None
            
            self.logger.info(f"Converted markdown to PDF: {pdf_path.name}")
            return str(pdf_path)
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"PDF conversion timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error converting to PDF: {e}")
            return None

    def _map_structure_to_pages(
        self, 
        structure: Dict[str, Any], 
        pdf_path: str
    ) -> Dict[int, int]:
        """
        Map structural blocks to PDF page numbers.
        
        This is done by extracting text from each page and matching it
        to the content in structural blocks.
        
        Parameters
        ----------
        structure: Dict[str, Any]
            Document structure
        pdf_path: str
            Path to PDF file
            
        Returns
        -------
        mapping: Dict[int, int]
            Maps block_index to page_number
        """
        
        mapping = {}
        
        try:
            # Extract text from each page
            page_texts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    # Normalize whitespace
                    text = " ".join(text.split())
                    page_texts.append(text.lower())
            
            # Map each block to a page
            for block in structure["blocks"]:
                block_index = block["block_index"]
                content = block.get("content", "")
                
                if not content:
                    continue
                
                # Normalize content
                content_normalized = " ".join(content.split())[:200].lower()  # First 200 chars
                
                # Find best matching page
                best_page = 1
                best_match_score = 0
                
                for page_num, page_text in enumerate(page_texts, start=1):
                    if content_normalized in page_text:
                        best_page = page_num
                        break
                    
                    # Calculate fuzzy match score
                    # Simple heuristic: count matching words
                    content_words = set(content_normalized.split())
                    page_words = set(page_text.split())
                    match_score = len(content_words & page_words)
                    
                    if match_score > best_match_score:
                        best_match_score = match_score
                        best_page = page_num
                
                mapping[block_index] = best_page
            
            # Also map headers to pages
            for header in structure["headers"]:
                block_index = header["block_index"]
                if block_index not in mapping:
                    # Use next block's page or first page
                    next_blocks = [b for b in structure["blocks"] if b["block_index"] > block_index]
                    if next_blocks:
                        mapping[block_index] = mapping.get(next_blocks[0]["block_index"], 1)
                    else:
                        mapping[block_index] = 1
            
            self.logger.info(f"Mapped {len(mapping)} blocks to pages")
            
            return mapping
            
        except Exception as e:
            self.logger.error(f"Error mapping structure to pages: {e}")
            return {}

    def _create_structured_chunks(
        self, 
        structure: Dict[str, Any], 
        page_mapping: Dict[int, int]
    ) -> List[StructuralChunk]:
        """
        Create structured chunks with page metadata.
        
        Parameters
        ----------
        structure: Dict[str, Any]
            Document structure
        page_mapping: Dict[int, int]
            Mapping from block index to page number
            
        Returns
        -------
        chunks: List[StructuralChunk]
            Structured chunks with semantic and page metadata
        """
        
        chunks = []
        
        # Process each section
        for section in structure["sections"]:
            section_header = section["header"]
            section_level = section["level"]
            section_hierarchy = section["hierarchy"]
            
            # Collect section content
            section_blocks = section["blocks"]
            
            if not section_blocks:
                continue
            
            # Create chunks from section, respecting max size
            current_chunk_content = []
            current_chunk_pages = set()
            current_chunk_type = "text"
            
            for block in section_blocks:
                block_index = block["block_index"]
                block_content = block.get("content", "")
                block_type = block.get("type", "text")
                
                if not block_content:
                    continue
                
                # Get page number
                page_num = page_mapping.get(block_index, 1)
                
                # Check if adding this block would exceed max size
                current_size = sum(len(c) for c in current_chunk_content)
                
                if current_size + len(block_content) > self.chunk_max_char and current_chunk_content:
                    # Save current chunk
                    chunk = StructuralChunk(
                        content="\n\n".join(current_chunk_content),
                        page_numbers=sorted(list(current_chunk_pages)),
                        section=section_header,
                        section_level=section_level,
                        chunk_type=current_chunk_type,
                        header_hierarchy=section_hierarchy if self.preserve_hierarchy else [section_header],
                        metadata={
                            "total_blocks": len(current_chunk_content),
                        }
                    )
                    chunks.append(chunk)
                    
                    # Start new chunk with overlap
                    if self.chunk_overlap > 0 and current_chunk_content:
                        # Keep last block for overlap
                        overlap_content = current_chunk_content[-1]
                        if len(overlap_content) > self.chunk_overlap:
                            overlap_content = overlap_content[-self.chunk_overlap:]
                        current_chunk_content = [overlap_content]
                        current_chunk_pages = {page_num}
                    else:
                        current_chunk_content = []
                        current_chunk_pages = set()
                
                # Add block to current chunk
                current_chunk_content.append(block_content)
                current_chunk_pages.add(page_num)
                current_chunk_type = block_type
            
            # Save final chunk
            if current_chunk_content:
                chunk = StructuralChunk(
                    content="\n\n".join(current_chunk_content),
                    page_numbers=sorted(list(current_chunk_pages)),
                    section=section_header,
                    section_level=section_level,
                    chunk_type=current_chunk_type,
                    header_hierarchy=section_hierarchy if self.preserve_hierarchy else [section_header],
                    metadata={
                        "total_blocks": len(current_chunk_content),
                    }
                )
                chunks.append(chunk)
        
        return chunks
