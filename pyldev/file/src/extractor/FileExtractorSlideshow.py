

from abc import ABC
from typing import Optional, Union
from io import BytesIO

from .FileExtractor import FileExtractor

class FileExtractorSlideshow(FileExtractor):

    def __init__(self,
        file_path: Optional[str] = None,
        file_bytes: Optional[BytesIO] = None
    ) -> None:
        """
        Processes slideshow-like files:
        - pptx, odp
        """
        super().__init__()

        
    def read_file(self, *args, **kwargs):
        return super().read_file(*args, **kwargs)
    
    def save_file(self, *args, **kwargs):
        return super().save_file(*args, **kwargs)
    