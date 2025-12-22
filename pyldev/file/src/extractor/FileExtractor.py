

from abc import ABC, abstractmethod
from file import File
from pyldev import _config_logger
from PIL.Image import Image
import io
from typing import Dict, List, Any, Optional, Union
import pytesseract

class FileExtractor(File):

    def __init__(self) -> None:
        super().__init__()


    @abstractmethod
    def extract(self, *args, **kwargs):
        raise NotImplementedError
    
    

    def _ocr_image(
        self, 
        image: Image, 
        page_num: int,
        language: str = "eng"
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
                    "ocr_dpi": image.info['dpi'],
                }
            }
            
        except Exception as e:
            print(f"Error OCR'ing page {page_num}: {e}")
            return {}