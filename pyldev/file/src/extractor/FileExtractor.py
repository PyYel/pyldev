

from abc import ABC, abstractmethod
from file import File

class FileExtractor(File):

    def __init__(self, logs_name: str) -> None:
        super().__init__(logs_name=logs_name)


    @abstractmethod
    def extract(self, *args, **kwargs):
        raise NotImplementedError
    
    
