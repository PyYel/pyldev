

from abc import ABC, abstractmethod
from file import File
from pyldev import _config_logger

class FileExtractor(File):

    def __init__(self) -> None:
        super().__init__()


    @abstractmethod
    def extract(self, *args, **kwargs):
        raise NotImplementedError
    
    
