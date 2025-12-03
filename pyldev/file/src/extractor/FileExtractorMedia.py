

from abc import ABC
from typing import Optional, Union
from io import BytesIO

from .FileExtractor import FileExtractor

class FileExtractorMedia(FileExtractor):

    def __init__(self,
        file_path: Optional[str] = None,
        file_bytes: Optional[BytesIO] = None
    ) -> None:
        """
        Processes media-like files:
        - Video: mp4, mkw, mov
        - Audio: mp3, wav, flac
        """
        super().__init__()

        
    def _read_file(self, *args, **kwargs):
        return super()._read_file(*args, **kwargs)
    
    def _save_file(self, *args, **kwargs):
        return super()._save_file(*args, **kwargs)
    