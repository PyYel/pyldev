import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import re
import html
from typing import Literal, Dict, List, Optional, Union
from tqdm import tqdm
import yaml

from pyldev import _config_logger
from .FileConverter import FileConverter

IMG_RE = re.compile(r'<img\s+[^>]*src="([^"]+)"[^>]*>')
IMGUR_HTML_RE = re.compile(r"https?://(?:i\.)?imgur\.com/(\w+)(?:\.\w+)?")


class FileConverterHTML(FileConverter):
    """
    A unified HTML converter.
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

        return None


    def convert(
        self,
        input_paths: Union[str, List[str]],
        output_paths: Optional[Union[str, List[str]]] = None,
    ) -> List[dict[str, Union[str, bool]]]:
        """
        Convert a markdown or text file to PDF.

        Parameters
        ----------
        input_path: str, List[str]
            Path to input file
        output_path: str, List[str], optional
            Path to output HTML file (optional, auto-generated if not provided)

        Returns
        -------
        successes: List[dict[str, Union[str, bool]]]
            List of results:
            [
                {"input_path": input_path, "output_path": output_path, "success": bool}
            ]

        Examples
        --------
        >>> convert(["folder/my_file.docx", "test.md"], ["outputs/test_a.html", "outputs/test_b.html"])
        """

        if isinstance(input_paths, str):
            input_paths = [input_paths]
        if isinstance(output_paths, str):
            output_paths = [output_paths]
        if output_paths is None or len(output_paths) != len(input_paths):
            output_paths = [f"{input_path}.pdf" for input_path in input_paths]

        successes = []
        for input_path, output_path in tqdm(
            zip(input_paths, output_paths), total=len(input_paths)
        ):
            result = {
                "input_path": input_path,
                "output_path": output_path,
                "success": False,
            }

            if input_path.endswith(".html"):
                result["output_path"] = input_path
                result["success"] = True
                self.logger.warning(
                    f"File is already in HTML: {os.path.basename(input_path)}"
                )


            if input_path.endswith(".md"):
                self.logger.debug(
                    f"Converting file {os.path.basename(input_path)} into HTML using Mkdocs."
                )
                result["success"] = self._convert_markdown(input_path, output_path)
            else:
                result["success"] = False
                self.logger.warning(
                    f"Slideshow conversion not supported for file: {os.path.basename(input_path)}"
                )

            successes.append(result)

        return successes

    def _convert_markdown(
        self, input_path: str, output_path: Optional[str] = None
    ) -> bool:
        """Convert a Markdown or text file to HTML via MkDocs (requires mkdocs and wkhtmltopdf binaries)."""

        def _create_default_custom_css():
            """Create a default CSS file for better HTML appearance."""
            css_content = """
            * { box-sizing: border-box; }
            html { font-size: 14px; }
            body { margin: 0; padding: 3rem 2.5rem; max-width: 960px; margin-left: auto; margin-right: auto; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; line-height: 1.65; color: #2b2b2b; background: #ffffff; }
            h1, h2, h3, h4, h5, h6 { font-weight: 600; color: #1f2937; page-break-after: avoid; }
            h1 { font-size: 2rem; margin-top: 0; padding-bottom: 0.4rem; border-bottom: 3px solid #2563eb; }
            h2 { font-size: 1.5rem; margin-top: 2.2rem; padding-bottom: 0.3rem; border-bottom: 1px solid #d1d5db; }
            h3 { font-size: 1.2rem; margin-top: 1.8rem; }
            p { margin: 0.7rem 0; }
            strong { font-weight: 600; }
            em { color: #4b5563; }
            a { color: #2563eb; text-decoration: none; }
            a:hover { text-decoration: underline; }
            code { background: #f3f4f6; padding: 0.15em 0.4em; border-radius: 4px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 0.9em; }
            pre { background: #0f172a; color: #e5e7eb; padding: 1rem 1.2rem; border-radius: 8px; overflow-x: auto; margin: 1.2rem 0; page-break-inside: avoid; }
            pre code { background: none; padding: 0; color: inherit; font-size: 0.85rem; }
            ul, ol { margin: 0.8rem 0; padding-left: 1.6rem; list-style-position: outside; }
            li { margin: 0.35rem 0; }
            ul ul, ol ol, ul ol, ol ul { margin-top: 0.4rem; margin-bottom: 0.4rem; padding-left: 1.6rem; }
            ul ul { list-style-type: circle; }
            ul ul ul { list-style-type: square; }
            table { border-collapse: collapse; width: 100%; margin: 1.2rem 0; page-break-inside: avoid; }
            th, td { border: 1px solid #e5e7eb; padding: 0.6rem 0.8rem; text-align: left; }
            th { background: #f9fafb; font-weight: 600; }
            blockquote { border-left: 4px solid #2563eb; margin: 1.2rem 0; padding-left: 1rem; color: #374151; font-style: italic; }
            img { max-width: 100%; height: auto; display: block; margin: 1.2rem auto; page-break-inside: avoid; }
            .mermaid { text-align: center; margin: 2rem 0; page-break-inside: avoid; }
            @media print { body { padding: 1.5cm; } a::after { content: " (" attr(href) ")"; font-size: 0.8em; color: #6b7280; } }
            .section { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1.2rem 1.5rem; margin: 2rem 0; page-break-inside: avoid; }
            """
            css_path = os.path.join(tempfile.gettempdir(), "pdf_style.css")
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(css_content)
            return css_path

        def _create_default_theme():
            main_html = """<!doctype html>
            <html lang="en">
            <head>
            <meta charset="utf-8">
            <title>{{ page.title }}</title>

            {% for css in extra_css %}
            <link rel="stylesheet" href="{{ css }}">
            {% endfor %}
            </head>
            <body>

            {{ page.content }}

            {% for script in extra_javascript %}
            <script src="{{ script }}"></script>
            {% endfor %}

            <script>
            if (window.mermaid) {
            mermaid.initialize({ startOnLoad: true });
            }
            </script>

            </body>
            </html>
            """
            theme_html = os.path.join(tempfile.gettempdir(), "main.html")
            with open(theme_html, "w", encoding="utf-8") as f:
                f.write(main_html)
            return main_html

        # Ensure output folder exists
        if output_path is None:
            output_path = os.path.join(os.getcwd(), "site_output")
        os.makedirs(output_path, exist_ok=True)

        # Temporary MkDocs project
        temp_dir = tempfile.mkdtemp()
        docs_dir = os.path.join(temp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)

        # Copy or convert input to markdown
        ext = os.path.splitext(input_path)[1].lower()
        if ext == ".md":
            md_path = os.path.join(docs_dir, os.path.basename(input_path))
            shutil.copy(input_path, md_path)
        else:  # .txt -> markdown code block
            md_path = os.path.join(
                docs_dir, os.path.splitext(os.path.basename(input_path))[0] + ".md"
            )
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("```\n" + content + "\n```")

        # Create CSS
        css_path = _create_default_custom_css()
        css_target = os.path.join(docs_dir, "css")
        os.makedirs(css_target, exist_ok=True)
        shutil.copy(css_path, os.path.join(css_target, "style.css"))

        # Create minimal mkdocs.yml
        mkdocs_yml = os.path.join(temp_dir, "mkdocs.yml")
        config = {
            "site_name": os.path.splitext(os.path.basename(input_path))[0],
            "docs_dir": "docs",
            "site_dir": output_path,
            "theme": {
                "name": None,       
                "custom_dir": _create_default_theme()
            },
            "extra_css": _create_default_custom_css(),
            "plugins": [
                {
                    "mermaid2": {
                        "javascript": "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"
                    }
                }
            ],
        }
        with open(mkdocs_yml, "w", encoding="utf-8") as f:
            yaml.dump(config, f, sort_keys=False)

        # Build the MkDocs site
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
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"MkDocs generation error: {e.stderr}")
            return False
