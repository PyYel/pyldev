import logging
import os, sys


class Logger():
    def __init__(self, logs_dir: str = os.getcwd(), progress_dir: str = os.getcwd()):
        """
        Logs verbose and progress bars
        """

        self.logs_dir = logs_dir
        self.progress_dir = progress_dir

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Create handlers
        file_handler = logging.FileHandler(os.path.join(self.logs_dir, "app.log"))
        console_handler = logging.StreamHandler()

        # Set level for handlers
        file_handler.setLevel(logging.DEBUG)
        console_handler.setLevel(logging.DEBUG)

        # Create formatters and add them to handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_debug(self, message):
        self.logger.debug(message)

    def log_info(self, message):
        self.logger.info(message)

    def log_warning(self, message):
        self.logger.warning(message)

    def log_error(self, message):
        self.logger.error(message)

    def log_critical(self, message):
        self.logger.critical(message)

    def log_progress(self, action: str, progress: float):
        """Saves a ``progress`` under a file named ``action.txt``."""

        progress_file = f"{os.path.join(self.progress_dir, action.lower().replace(' ', '_'))}.txt"
        with open(progress_file, "w") as f:
            f.write(f"{progress}")
