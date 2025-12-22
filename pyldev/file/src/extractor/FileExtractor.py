from abc import ABC, abstractmethod
from file import File
from pyldev import _config_logger
from PIL.Image import Image
import io
from typing import Dict, List, Any, Optional, Union, Literal
import pytesseract
import json
import sys, os


class FileExtractor(File):

    def __init__(self) -> None:
        super().__init__()

        self.SUPPORTED_FORMATS = {
            "document": [".pdf", ".docx", ".doc"],
            "media": [".mp3", ".mp4"],
            "slideshow": [".pptx", ".otp"],
            "spreadsheet": [".xlsx", ".csv"],
        }

    @abstractmethod
    def extract(self, *args, **kwargs):
        raise NotImplementedError

    def _save_chunks(
        self,
        output_path: str,
        text_chunks: list[str],
        format: Literal["txt", "json"] = "txt",
    ) -> str:
        """
        Save batches to disk. format="txt" writes a plain text file with blank-line separators.
        """

        if isinstance(text_chunks, str):
            text_chunks = [text_chunks]
        # if self.file_path:
        #     name = os.path.basename(self.file_path)
        # elif self.file_bytes:
        #     name = self.file_bytes.name

        if format == "txt":
            for idx, text in enumerate(text_chunks):
                with open(
                    os.path.join(output_path, f"{idx}.txt"), "w", encoding="utf-8"
                ) as f:
                    f.write(text + "\n\n")
            return output_path

        elif format == "json":
            for idx, text in enumerate(text_chunks):
                with open(
                    os.path.join(output_path, f"{idx}.txt"), "w", encoding="utf-8"
                ) as f:
                    json.dump(text, f)

        raise ValueError(f"Unsupported format: {format}")

    def _ocr_image(
        self, image: Image, page_num: int, language: str = "eng"
    ) -> Optional[Dict[str, Any]]:
        """
        Apply OCR to entire page (for scanned content).
        """
        try:

            text = str(pytesseract.image_to_string(image, lang=language)).strip()

            if not text:
                return {}

            return {
                "text": text,
                "type": "text",
                "metadata": {
                    "page_number": page_num,
                    "source": "ocr_full_page",
                    "ocr_lang": language,
                    "ocr_dpi": image.info["dpi"],
                },
            }

        except Exception as e:
            print(f"Error OCR'ing page {page_num}: {e}")
            return {}
