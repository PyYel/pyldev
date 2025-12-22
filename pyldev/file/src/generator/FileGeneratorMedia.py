from abc import ABC
from typing import Optional, Union
from io import BytesIO

from .FileGenerator import FileGenerator


class FileGeneratorMedia(FileGenerator):

    def __init__(
        self, file_path: Optional[str] = None, file_bytes: Optional[BytesIO] = None
    ) -> None:
        """
        Processes document-like files:
        - Formatted: docx, doc, pdf
        - Unformattted: txt, md
        """

        super().__init__()

    def _read_file(self, *args, **kwargs):
        return super()._read_file(*args, **kwargs)

    def _save_file(self, *args, **kwargs):
        return super()._save_file(*args, **kwargs)
