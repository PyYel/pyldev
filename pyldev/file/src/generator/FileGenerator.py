from abc import ABC, abstractmethod

from ..File import File


class FileGenerator(File):

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def extract(self):
        raise NotImplementedError
