
import shutil
from typing import Union, Optional, List, Dict
from io import BytesIO
import os, sys
import hashlib
import json
import uuid
import logging
from datetime import datetime

from abc import ABC, abstractmethod

class File(ABC):

    def __init__(self, logs_name: str) -> None:
        super().__init__()

        self.text_batches: List[str] = []
        self.file_path: Optional[str] = None
        self.file_bytes: Optional[BytesIO] = None

        self._config_logger(logs_name=logs_name)


    def _read_file(self) -> BytesIO:
        """
        Populate self.file_bytes from self.file_path if needed.
        Returns BytesIO.
        """
        if self.file_bytes:
            return self.file_bytes

        if not self.file_path:
            raise ValueError("No file_path or file_bytes provided.")

        try:
            with open(self.file_path, "rb") as f:
                self.file_bytes = BytesIO(f.read())
        except Exception as e:
            raise ValueError(f"Error reading file_path: {e}")

        return self.file_bytes

    def _save_chunks(self, 
        output_path: str, 
        text_chunks: list[str],
        format: str = "txt") -> str:
        """
        Save batches to disk. format="txt" writes a plain text file with blank-line separators.
        """

        if self.file_path: name = os.path.basename(self.file_path)
        elif self.file_bytes: name = self.file_bytes.name

        # os.makedirs(self.file_path, exist_ok=True)

        if format == "txt":
            with open(output_path, "w", encoding="utf-8") as fh:
                for b in text_chunks:
                    fh.write(b + "\n\n")
            return output_path
        
        elif format == "json":
            json.dumps()
            

        raise ValueError(f"Unsupported format: {format}")
    
    # Utilities
    def _has_program(self, name: str) -> bool:
        """Return True if executable is on PATH (used for poppler/tesseract)."""
        return shutil.which(name) is not None
    


    def _hash_content(self, content: str, prefixes: List[str], algo: str = "md5") -> str:
        """
        Hashes a document content into a unique id of format <prefixes>-<hashed_content>.
        Useful to automatically overwrite a stored document when a document with the same 
        timestamp and content is written into Elasticsearch or SQL.

        Parameters
        ----------
        content : str
            The text content to hash.
        prefixes : list[str]
            A list of prefixes (such as metadata, timestamps...) to prefix the hashed content with.
        algo : str, optional
            The hashing algorithm to use. Supported: "md5", "sha1", "sha256", "uuid5".
            Default is "md5".

        Returns
        -------
        hashed_id : str
            The unique hashed ID.

        Examples
        --------
        >>> print(_hash_content("Message from Caroline: Merry Christmas!", ["2024/12/25", "103010"], algo="md5"))
        '2024/12/25-103010-4432e1c6d1c4f0db2f157d501ae242a7'
        >>> print(_hash_content("Message from Caroline: Merry Christmas!", ["2024/12/25", "103010"], algo="sha256"))
        '2024/12/25-103010-84f6b29a7fa3e11e5f0b0f5d63c024c97b51a9c5f457d07d41b58738e2e0d7f4'
        >>> print(_hash_content("Message from Caroline: Merry Christmas!", ["2024/12/25", "103010"], algo="uuid5"))
        '2024/12/25-103010-4b28f4a0-6bcf-55cc-95b3-2e3d5a64f155'
        """
        base = "-".join(prefixes) + "-" + content

        if algo == "md5":
            digest = hashlib.md5(base.encode()).hexdigest()
        elif algo == "sha1":
            digest = hashlib.sha1(base.encode()).hexdigest()
        elif algo == "sha256":
            digest = hashlib.sha256(base.encode()).hexdigest()
        elif algo == "uuid5":
            digest = str(uuid.uuid5(uuid.NAMESPACE_DNS, base))
        else:
            raise ValueError(f"Unsupported algo: {algo}")

        return f"{'-'.join(prefixes)}-{digest}"

    def _config_logger(self, 
                       logs_name: str, 
                       logs_dir: Optional[str] = None, 
                       logs_level: str = os.getenv("LOGS_LEVEL", "INFO"),
                       logs_output: list[str] = ["console", "file"]):
        """
        Will configure logging accordingly to the plateform the program is running on. This
        is the default behaviour. See ``custom_config()`` to override the parameters.
        """

        if logs_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:  logs_level="INFO"
        if logs_dir is None: logs_dir = os.path.join(os.getcwd(), "logs", str(datetime.now().strftime("%Y-%m-%d")))
        os.makedirs(logs_dir, exist_ok=True)

        self.logger = logging.getLogger(logs_name)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # If a logger already exists, this prevents duplication of the logger handlers
        if self.logger.hasHandlers():
            for handler in self.logger.handlers:
                handler.close()

        # Creates/recreates the handler(s)
        if not self.logger.hasHandlers():

            if "console" in logs_output:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging._nameToLevel[logs_level])
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
                self.logger.info("Logging handler configured for console output.")

            if "file" in logs_output:
                file_handler = logging.FileHandler(os.path.join(logs_dir, f"{datetime.now().strftime('%H-%M-%S')}-app.log"))
                file_handler.setLevel(logging._nameToLevel[logs_level])
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                self.logger.info("Logging handler configured for file output.")

        return None