

from abc import ABC, abstractmethod

class File(ABC):

    def __init__(self) -> None:
        super().__init__()


    @abstractmethod
    def read_file(self, *args, **kwargs):
        raise NotImplementedError
    

    @abstractmethod
    def save_file(self, *args, **kwargs):
        raise NotImplementedError
    

    