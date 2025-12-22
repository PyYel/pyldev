from abc import ABC

from module_1 import Module1


class Module1Class(Module1):
    """
    Module 1 child class that actually does usefull things.
    """

    def __init__(self):
        """
        The purpose and definition of this class. Inherits Module1 abstract class.
        """
        super().__init__()
