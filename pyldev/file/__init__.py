# __all__ = [
#     "File"
# ]

from .src.File import File

from .src.extractor.FileExtractorDocument import FileExtractorDocument
from .src.extractor.FileExtractorDocument2 import FileExtractorDocument2
from .src.extractor.FileExtractorMedia import FileExtractorMedia
from .src.extractor.FileExtractorSlideshow import FileExtractorSlideshow
from .src.extractor.FileExtractorSpreadsheet import FileExtractorSpreadsheet

from .src.element import *

from .src.converter.FileConverterPDF import FileConverterPDF