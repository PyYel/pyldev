import logging
import os, sys
from datetime import datetime


class Logger:
    """
    Base logger class.
    """

    def __init__(self, logs_dir: str = os.getcwd()):
        """
        Logs verbose and progress bars. Stdout can be cmd, file, none, or both.
        """

        self.logs_dir = os.path.join(logs_dir, str(datetime.now().strftime("%Y-%m-%d")))

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        return None

    def auto_config(self):
        """
        Will configure logging accordingly to the plateform the program is running on. This
        is the default behaviour. See ``custom_config()`` to override the parameters.
        """

        # If a logger already exists, this prevents duplication of the logger handlers
        if not self.logger.hasHandlers():

            # Create formatters and add them to handlers
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

            # Add handlers to the logger
            if os.name == "nt":
                # Windows OS
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(formatter)

                self.logger.addHandler(console_handler)

                self.logger.info(
                    "Desktop OS environment detected. Logging will be adjusted accordingly."
                )
                self.logger.info("Logging handler configured for console output.")

            else:
                # Others OS
                os.makedirs(self.logs_dir, exist_ok=True)
                file_handler = logging.FileHandler(
                    os.path.join(
                        self.logs_dir, f"{datetime.now().strftime('%H-%M-%S')}-app.log"
                    )
                )
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)

                self.logger.addHandler(file_handler)

                self.logger.info(
                    "Server OS environment detected. Logging will be adjusted accordingly."
                )
                self.logger.info("Logging handler configured for file output.")

            return None

    def custom_config(
        self,
        logs_dir: str = None,
        file_stdout: bool = True,
        console_stdout: bool = True,
    ):
        """
        Overwrites default
        """
        if logs_dir is not None:
            self.logs_dir = logs_dir

        # If a logger already exists, this prevents duplication of the logger handlers
        if not self.logger.hasHandlers():

            os.makedirs(self.logs_dir, exist_ok=True)

            # Create handlers
            file_handler = logging.FileHandler(
                os.path.join(
                    self.logs_dir, f"{datetime.now().strftime('%H-%M-%S')}-app.log"
                )
            )
            console_handler = logging.StreamHandler()

            # Set level for handlers
            file_handler.setLevel(logging.DEBUG)
            console_handler.setLevel(logging.DEBUG)

            # Create formatters and add them to handlers
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # Add handlers to the logger
            if file_stdout and console_stdout:
                self.logger.addHandler(file_handler)
                self.logger.addHandler(console_handler)
                self.logger.info(
                    "Logging handlers configured for both console and file output."
                )
            elif file_stdout:
                self.logger.addHandler(file_handler)
                self.logger.info("Logging handler configured for file output.")
            elif console_stdout:
                self.logger.addHandler(console_handler)
                self.logger.info("Logging handler configured for console output.")
            elif not file_stdout and not console_stdout:
                self.logger.warning(
                    "No logging handler configured. Logging will be muted."
                )

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
