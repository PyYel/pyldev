from abc import ABC, abstractmethod
from PIL.Image import Image
import io
from typing import Dict, List, Any, Optional, Union, Literal
import json
import sys, os
from collections import defaultdict

from ..element import FileElement, TextElement
from ..File import File

class FileConverter(File):

    def __init__(self) -> None:
        super().__init__()

        self.SUPPORTED_FORMATS = {
            "document": [".pdf", ".docx", ".doc", ".md", ".txt"],
            "media": [".mp3", ".mp4"],
            "slideshow": [".pptx", ".otp"],
            "spreadsheet": [".xlsx", ".csv"],
        }

    @abstractmethod
    def convert(self, *args, **kwargs):
        raise NotImplementedError
