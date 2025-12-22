import os, sys

from logger import Logger


class LoggerPrintIntercept(Logger):
    """
    An improved logger that also tracks print debugs.

    TODO: add a PyYel (print) logs only interceptor.
    """

    def __init__(self, logs_dir: str = os.getcwd()):
        """
        Initializes the standard Logger function with a ``print()`` statement interceptor. This catch any stdout output, such as ``tqdm`` progress bar...
        """
        super().__init__(logs_dir=logs_dir)

        self.original_stdout = sys.stdout

        return None

    def write(self, message: str):
        """Saves the message to the history."""
        if message.strip():  # Avoid logging empty lines
            self.log_debug(message.strip())  # Log using the parent logger

        return None

    def start(self):
        """Redirect ``sys.stdout``."""
        sys.stdout = self
        return None

    def stop(self):
        """Restore the original ``sys.stdout``."""
        sys.stdout = self.original_stdout
        return None
