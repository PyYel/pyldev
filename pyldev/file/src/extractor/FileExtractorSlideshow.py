from abc import ABC
from typing import Optional, Union
from io import BytesIO

from .FileExtractor import FileExtractor


class FileExtractorSlideshow(FileExtractor):

    def __init__(
        self, file_path: Optional[str] = None, file_bytes: Optional[BytesIO] = None
    ) -> None:
        """
        Processes image-like files:
        - Slideshow: pptx, odp
        - Images: png, jpg
        """
        super().__init__()

    def extract(self, *args, **kwargs):
        return []
