

from abc import ABC, abstractmethod
from file import File

class FileExtractor(File):

    def __init__(self) -> None:
        super().__init__()


    @abstractmethod
    def extract(self, *args, **kwargs):
        raise NotImplementedError
    
    
