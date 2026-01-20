import io
import os
import shutil
import subprocess
import tempfile
import glob
import logging
import requests
from pathlib import Path
from markdown_it import MarkdownIt
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Image,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import re
import html
from typing import Literal, Dict, List, Optional, Union
from tqdm import tqdm

from pyldev import _config_logger
from .FileConverter import FileConverter

IMG_RE = re.compile(r'<img\s+[^>]*src="([^"]+)"[^>]*>')
IMGUR_HTML_RE = re.compile(r"https?://(?:i\.)?imgur\.com/(\w+)(?:\.\w+)?")


class FileConverterPDF(FileConverter):
    """
    A unified PDF converter supporting both ReportLab (no external dependencies)
    and wkhtmltopdf (better formatting) conversion methods.
    
    Automatically selects the best available method if 'auto' is specified.
    """

    def __init__(
        self,
        max_image_width: int = 450,
        max_image_height: int = 200,
        custom_css: Optional[str] = None,
    ):
        """
        Args:
            method: "auto" (default, uses wkhtmltopdf if available, falls back to reportlab),
                    "reportlab" (no external dependencies), or 
                    "wkhtmltopdf" (requires wkhtmltopdf and mkdocs)
            max_image_width: Maximum width for images (ReportLab only)
            max_image_height: Maximum height for images (ReportLab only)
            custom_css: Path to a CSS file to style the PDF (wkhtmltopdf only)
        """
        self.max_image_width = max_image_width
        self.max_image_height = max_image_height
        self.custom_css = os.path.abspath(custom_css) if custom_css else None

        self.logger = _config_logger(logs_name="FileConverterPDF")

        # Determine method
        try:
            # Check wkhtmltopdf
            subprocess.run(
                ["wkhtmltopdf", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=True,
            )
            self.method = "wkhtmltopdf"
            self.logger.debug("Auto-selected wkhtmltopdf (available)")
        except Exception as e:
            self.method = "reportlab"
            self.logger.debug(f"Auto-selected reportlab (wkhtmltopdf not available): {e}")

        # ReportLab styles setup
        if self.method == "reportlab":
            self.styles = getSampleStyleSheet()
            self.styles.add(ParagraphStyle("H1", parent=self.styles["Heading1"]))
            self.styles.add(ParagraphStyle("H2", parent=self.styles["Heading2"]))
            self.styles.add(ParagraphStyle("H3", parent=self.styles["Heading3"]))
            self.styles.add(
                ParagraphStyle(
                    "Hyperlink",
                    parent=self.styles["Normal"],
                    textColor=colors.HexColor("#2020EB"),
                    underline=True,
                )
            )

        return None

    def convert(
        self,
        input_paths: Union[str, List[str]],
        output_paths: Optional[List[str]] = None,
    ) -> List[dict[str, Union[str, bool]]]:
        """
        Convert a markdown or text file to PDF.

        Parameters
        ----------
        input_path: str, List[str]
            Path to input .md or .txt file
        output_path: str, List[str], optional
            Path to output PDF file (optional, auto-generated if not provided)

        Returns
        -------
        successes: List[dict[str, Union[str, bool]]]
            List of results:
            [
                {"input_path": input_path, "output_path": output_path, "success": bool}
            ]

        Examples
        --------
        >>> convert(["folder/my_file.docx", "test.md"], ["outputs/test_a.pdf", "outputs/test_b.pdf"])
        """

        if isinstance(input_paths, str):
            input_paths = [input_paths]
        if isinstance(output_paths, str):
            output_paths = [output_paths]
        if output_paths is None or len(output_paths) != len(input_paths):
            output_paths = [f"{input_path}.pdf" for input_path in input_paths]

        successes = []
        for input_path, output_path in tqdm(zip(input_paths, output_paths), total=len(input_paths)):
            result = {
                "input_path": input_path,
                "output_path": output_path,
                "success": False
            }

            if input_path.endswith(".pdf"):
                result["output_path"] = input_path
                result["success"] = True
                self.logger.warning(f"File is already a PDF: {os.path.basename(input_path)}")

            if input_path.endswith(".txt") or input_path.endswith(".md"):
                if self.method == "reportlab":
                    self.logger.debug(f"Converting file {os.path.basename(input_path)} into PDF using reportlab.")
                    result["success"] = self._convert_reportlab(input_path, output_path)
                elif self.method == "wkhtmltopdf":
                    self.logger.debug(f"Converting file {os.path.basename(input_path)} into PDF using wkhtmltopdf.")
                    result["success"] = self._convert_wkhtmltopdf(input_path, output_path)

            elif input_path.endswith(".docx") or input_path.endswith(".doc"):
                self.logger.debug(f"Converting file {os.path.basename(input_path)} into PDF using LibreOffice.")
                result["success"] = self._convert_docx(input_path, output_path)

            elif input_path.endswith(".pptx") or input_path.endswith(".odt"):
                # self.logger.debug(f"Converting file {os.path.basename(input_path)} into PDF using LibreOffice.")
                result["success"] = False
                self.logger.warning(f"Slideshow conversion not supported for file: {os.path.basename(input_path)}")

            successes.append(result)

        return successes
    
    def __call__(self, *args, **kargs):
        return self.convert(*args, **kargs)

    def _convert_reportlab(
        self,
        input_path: str,
        output_path: str,
    ) -> bool:
        """Convert using ReportLab (no external dependencies)"""

        def _inline_to_html(inline_token):
            """
            Convert Markdown inline token to ReportLab-compatible HTML:
            - Bold ``(<b>)``
            - Italic ``(<i>)``
            - External hyperlinks ``(<a href>)`` with special style
            - Internal anchors are plain text
            """
            html_text = ""
            stack = []

            for child in inline_token.children or []:
                if child.type == "text":
                    html_text += html.escape(child.content)

                elif child.type == "strong_open":
                    html_text += "<b>"
                    stack.append("b")
                elif child.type == "strong_close":
                    if stack and stack[-1] == "b":
                        html_text += "</b>"
                        stack.pop()

                elif child.type == "em_open":
                    html_text += "<i>"
                    stack.append("i")
                elif child.type == "em_close":
                    if stack and stack[-1] == "i":
                        html_text += "</i>"
                        stack.pop()

                elif child.type == "link_open":
                    href = child.attrs.get("href", "")
                    if href.startswith("http://") or href.startswith("https://"):
                        html_text += f'<font color="#0000EE"><a href="{href}">'
                        stack.append("a")

                elif child.type == "link_close":
                    if stack and stack[-1] == "a":
                        html_text += "</a></font>"
                        stack.pop()

                else:
                    html_text += html.escape(getattr(child, "content", ""))

            # Close any remaining tags
            while stack:
                tag = stack.pop()
                html_text += f"</{tag}>"

            return html_text

        def _handle_list(tokens, i, story: List, styles):
            """
            Parse a markdown list (ordered or bullet) starting at index i.
            Returns new index after the list.
            """
            list_type = "bullet" if tokens[i].type == "bullet_list_open" else "ordered"
            items = []
            i += 1
            close_type = (
                "bullet_list_close" if list_type == "bullet" else "ordered_list_close"
            )

            while i < len(tokens) and tokens[i].type != close_type:
                if tokens[i].type == "list_item_open":
                    j = i + 1
                    content = ""
                    while tokens[j].type != "list_item_close":
                        if tokens[j].type == "paragraph_open":
                            inline = tokens[j + 1]
                            content += _inline_to_html(inline)
                            j += 3
                        else:
                            j += 1
                    items.append(ListItem(Paragraph(content, styles["Normal"])))
                    i = j + 1
                else:
                    i += 1

            lf = ListFlowable(
                items,
                bulletType="1" if list_type == "ordered" else "bullet",
                start="1",
                bulletFontName="Helvetica",
                bulletFontSize=10,
                leftIndent=12,
            )
            story.append(lf)
            story.append(Spacer(1, 6))
            return i

        def _imgur_html_to_direct(src):
            """Convert Imgur HTML link to direct image link"""
            match = IMGUR_HTML_RE.match(src)
            if match:
                image_id = match.group(1)
                return f"https://i.imgur.com/{image_id}.png"
            return src

        def _fetch_image(src):
            """Fetch and process image for ReportLab"""
            try:
                if src.startswith("http://") or src.startswith("https://"):
                    if "imgur.com" in src:
                        src = _imgur_html_to_direct(src)
                    headers = {"User-Agent": "Mozilla/5.0"}
                    r = requests.get(src, headers=headers, timeout=10)
                    r.raise_for_status()
                    if "image" not in r.headers.get("Content-Type", ""):
                        raise ValueError(f"URL did not return an image: {src}")
                    img = Image(io.BytesIO(r.content))
                else:
                    img = Image(src)

                # Resize if necessary
                if (
                    img.drawWidth > self.max_image_width
                    or img.drawHeight > self.max_image_height
                ):
                    ratio = min(
                        self.max_image_width / img.drawWidth,
                        self.max_image_height / img.drawHeight,
                    )
                    img.drawWidth *= ratio
                    img.drawHeight *= ratio

                return img

            except Exception as e:
                self.logger.error(f"Failed to load image {src}: {e}")
                return Paragraph(
                    f"[Image could not be loaded: {src}]", self.styles["Normal"]
                )

        ext = os.path.splitext(input_path)[1].lower()

        if ext == ".txt":
            # Convert .txt to a code block in markdown
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()
            text = f"```\n{content}\n```"
        else:
            text = Path(input_path).read_text(encoding="utf-8")

        md = MarkdownIt("commonmark").enable("table")
        tokens = md.parse(text)
        story = []

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Headings
            if token.type == "heading_open":
                level = int(token.tag[1])
                inline = tokens[i + 1]
                html_text = _inline_to_html(inline)
                story.append(Paragraph(html_text, self.styles[f"H{level}"]))
                story.append(Spacer(1, 12))
                i += 3
                continue

            # Paragraphs
            if token.type == "paragraph_open":
                inline = tokens[i + 1]
                if inline.content.strip():
                    html_text = _inline_to_html(inline)
                    story.append(Paragraph(html_text, self.styles["Normal"]))
                    story.append(Spacer(1, 8))
                i += 3
                continue

            # Lists
            if token.type in ("bullet_list_open", "ordered_list_open"):
                i = _handle_list(tokens, i, story, self.styles)
                continue

            # HTML image blocks
            if token.type == "html_block":
                match = IMG_RE.search(token.content)
                if match:
                    src = match.group(1)
                    story.append(_fetch_image(src))
                    story.append(Spacer(1, 12))
                i += 1
                continue

            # Tables
            if token.type == "table_open":
                table_data = []
                i += 1
                while tokens[i].type != "table_close":
                    if tokens[i].type == "tr_open":
                        row = []
                        i += 1
                        while tokens[i].type != "tr_close":
                            if tokens[i].type in ("th_open", "td_open"):
                                cell = _inline_to_html(tokens[i + 1])
                                row.append(cell)
                                i += 3
                            else:
                                i += 1
                        table_data.append(row)
                    i += 1

                table = Table(table_data, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 12))
                i += 1
                continue

            i += 1

        # Build PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        doc.build(story)
        self.logger.info(f"PDF generated successfully: {output_path}")
        return True
    
    
    def _convert_wkhtmltopdf(
        self,
        input_path: str,
        output_path: Optional[str] = None,
    ) -> bool:
        """Convert using wkhtmltopdf via MkDocs (requires wkhtmltopdf binaries)"""

        def _create_default_custom_css():
            """Create a default CSS file for better PDF appearance"""
            css_content = """
            /* Remove @page margin - let wkhtmltopdf handle it */
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                font-size: 12pt;  /* Increased from 11pt */
            }
            
            h1, h2, h3, h4, h5, h6 {
                color: #2c3e50;
                page-break-after: avoid;
                margin-top: 1.2em;
                margin-bottom: 0.4em;
            }
            
            h1 { font-size: 26pt; border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }
            h2 { font-size: 22pt; border-bottom: 1px solid #bdc3c7; padding-bottom: 0.2em; }
            h3 { font-size: 18pt; }
            h4 { font-size: 15pt; }
            
            p {
                margin: 0.4em 0;
                text-align: left;  /* Changed from justify for better readability */
            }
            
            code {
                background-color: #f5f5f5;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
            }
            
            pre {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 12px;
                overflow-x: auto;
                page-break-inside: avoid;
                font-size: 11pt;
            }
            
            pre code {
                background-color: transparent;
                padding: 0;
            }
            
            img {
                max-width: 100%;
                height: auto;
                display: block;
                margin: 1em auto;
                page-break-inside: avoid;
            }
            
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
                page-break-inside: avoid;
                font-size: 11pt;
            }
            
            th, td {
                border: 1px solid #ddd;
                padding: 8px 12px;
                text-align: left;
            }
            
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
            
            blockquote {
                border-left: 4px solid #3498db;
                padding-left: 1em;
                margin-left: 0;
                color: #555;
                font-style: italic;
            }
            
            ul, ol {
                margin: 0.4em 0;
                padding-left: 2em;
            }
            
            li {
                margin: 0.2em 0;
            }
            
            /* Avoid breaking elements across pages */
            h1, h2, h3, h4, h5, h6, img, table, pre {
                page-break-inside: avoid;
            }
            """
            
            css_path = os.path.join(tempfile.gettempdir(), "pdf_style.css")
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(css_content)
            
            return css_path
        

        ext = os.path.splitext(input_path)[1].lower()

        # Create temporary directory for MkDocs project
        temp_dir = tempfile.mkdtemp()
        docs_dir = os.path.join(temp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)

        # Prepare markdown file
        if ext == ".md":
            md_path = os.path.join(docs_dir, os.path.basename(input_path))
            shutil.copy(input_path, md_path)
            
            # Copy any images referenced in the markdown to docs directory
            input_dir = os.path.dirname(os.path.abspath(input_path))
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Find image references (markdown and HTML img tags)
            img_patterns = [
                r'!\[.*?\]\((.*?)\)',  # ![alt](path)
                r'<img[^>]+src=["\']([^"\']+)["\']',  # <img src="path">
            ]
            
            for pattern in img_patterns:
                for match in re.finditer(pattern, content):
                    img_path = match.group(1)
                    # Skip URLs
                    if img_path.startswith(('http://', 'https://', 'data:')):
                        continue
                    
                    # Resolve relative paths
                    abs_img_path = os.path.join(input_dir, img_path)
                    if os.path.exists(abs_img_path):
                        # Preserve directory structure
                        rel_dir = os.path.dirname(img_path)
                        target_dir = os.path.join(docs_dir, rel_dir)
                        os.makedirs(target_dir, exist_ok=True)
                        target_path = os.path.join(docs_dir, img_path)
                        shutil.copy2(abs_img_path, target_path)
                        self.logger.debug(f"Copied image: {abs_img_path} -> {target_path}")
        else:  # .txt -> convert to Markdown code block
            md_path = os.path.join(
                docs_dir,
                os.path.splitext(os.path.basename(input_path))[0] + ".md",
            )
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("```\n" + content + "\n```")

        # Create minimal mkdocs.yml
        mkdocs_yml = os.path.join(temp_dir, "mkdocs.yml")
        with open(mkdocs_yml, "w", encoding="utf-8") as f:
            f.write(f"site_name: {os.path.basename(input_path)}\n")
            f.write("theme:\n")
            f.write("  name: material\n")
            f.write("  features: []\n")
            f.write("extra:\n")
            f.write("  generator: false\n")
            f.write("plugins: []\n")

        # Build MkDocs site
        try:
            result = subprocess.run(
                ["mkdocs", "build", "-f", mkdocs_yml],
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            self.logger.info("MkDocs site built successfully")
            self.logger.debug(result.stdout)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"MkDocs generation error: {e.stderr}")
            raise

        # Find generated HTML file
        site_dir = os.path.join(temp_dir, "site")
        html_files = glob.glob(
            os.path.join(site_dir, "**", "index.html"), recursive=True
        )
        if not html_files:
            raise FileNotFoundError(
                "No index.html found in site folder after MkDocs build"
            )
        html_file = html_files[0]

        # Build wkhtmltopdf command
        cmd = [
            "wkhtmltopdf",
            # Page setup
            "--page-size", "A4",
            "--orientation", "Portrait",
            
            # Smaller margins - standard document margins
            "--margin-top", "15mm",
            "--margin-right", "15mm",
            "--margin-bottom", "20mm",  # Slightly larger for footer
            "--margin-left", "15mm",
            
            # Essential for local files
            "--enable-local-file-access",
            "--allow", site_dir,
            
            # Rendering quality
            "--print-media-type",
            "--dpi", "300",
            "--image-quality", "94",
            
            # JavaScript handling
            "--enable-javascript",
            "--javascript-delay", "1000",
            "--no-stop-slow-scripts",
            
            # Encoding
            "--encoding", "UTF-8",
        ]

        # Custom CSS for additional styling
        if self.custom_css is None:
            self.custom_css = _create_default_custom_css()
        cmd += ["--allow", os.path.dirname(self.custom_css)]
        cmd += ["--user-style-sheet", self.custom_css]

        # Add header/footer for more professional look
        cmd += [
            "--footer-center", "[page] / [toPage]",
            "--footer-font-size", "9",
            "--footer-spacing", "5",
        ]

        # Input and output
        cmd += [f"file:///{html_file.replace(os.sep, '/')}", output_path]

        # Execute wkhtmltopdf
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            self.logger.info(f"wkhtmltopdf generation complete: {output_path}")
            self.logger.debug(result.stdout)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"wkhtmltopdf generation error: {e.stderr}")
            return False
        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

        return True


    def _convert_docx(
        self,
        input_path: str,
        output_path: str,
    ) -> bool:
        """
        Converts a document to PDF using LibreOffice
        and renames it to the desired output path.
        """

        if not os.path.exists(input_path):
            self.logger.error(f"File not found: {input_path}")
            return False

        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        soffice_bin = self._get_soffice_path()
        if not soffice_bin:
            self.logger.error("LibreOffice (soffice/libreoffice) not found on PATH")
            return False

        cmd = [
            soffice_bin,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", output_dir,
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
            return False

        # LibreOffice always uses the input basename for the output file
        input_basename = os.path.splitext(os.path.basename(input_path))[0]
        generated_pdf = os.path.join(output_dir, f"{input_basename}.pdf")

        if not os.path.exists(generated_pdf):
            self.logger.error(f"Expected PDF not found: {generated_pdf}")
            return False

        # Rename/move to the exact output_path requested
        try:
            shutil.move(generated_pdf, output_path)
        except Exception as e:
            self.logger.error(f"Failed to rename PDF: {e}")
            return False

        return True