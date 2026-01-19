import shutil
from typing import Union, Optional, List, Dict
from io import BytesIO
import os, sys
import hashlib
import json
import uuid
from abc import ABC, abstractmethod
import unicodedata

from pyldev import _config_logger


class File(ABC):

    def __init__(self) -> None:
        super().__init__()

        self.text_batches: List[str] = []
        self.file_path: Optional[str] = None
        self.file_bytes: Optional[BytesIO] = None

        self.logger = _config_logger(
            logs_name="File",
            logs_output="console",
        )

        self.SUPPORTED_FORMATS = {}

    def _check_supported(self, extractor_type: str, file_path: str):
        """
        Checks if a file is supported using its extension and the ``SUPPORTED_FORMAT`` attribute.
        """
        ext = os.path.splitext(file_path)[-1]
        if ext in self.SUPPORTED_FORMATS[extractor_type]:
            return True
        else:
            self.logger.warning(
                f"Extractor '{extractor_type}' does not support file '{ext}'."
            )
            return False

    def _sanitize_text(self, text: str) -> str:
        # Remove BOM if present
        text = text.lstrip("\ufeff")

        # If null bytes exist, assume UTF-16BE pattern
        if "\x00" in text:
            try:
                # Re-encode as latin1 to recover raw bytes,
                # then decode as UTF-16
                text = text.encode("latin1").decode("utf-16")
            except UnicodeError:
                # Fallback: strip null bytes
                text = text.replace("\x00", "")

        return unicodedata.normalize("NFC", text)

    def _get_soffice_path(self) -> Optional[str]:
        """
        Get the path to LibreOffice soffice binary.

        Returns
        -------
        path: Optional[str]
            Path to soffice binary or None if not found
        """
        if sys.platform == "win32":
            soffice_bin = r"C:\Program Files\LibreOffice\program\soffice.exe"
            if os.path.exists(soffice_bin):
                return soffice_bin
            return shutil.which("soffice")
        else:
            return shutil.which("soffice") or shutil.which("libreoffice")

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

    def _save_file(self, file_path: str) -> None:
        """
        Write self.file_bytes to disk.
        """
        if not self.file_bytes:
            raise ValueError("No file_bytes to save.")

        if not os.path.exists(os.path.dirname(file_path)):
            raise ValueError("Path is inconplete or can't be reached.")

        try:
            self.file_bytes.seek(0)
            with open(file_path, "wb") as f:
                f.write(self.file_bytes.read())
        except Exception as e:
            raise ValueError(f"Error writing file_path: {e}")

    def _hash_content(
        self, content: str, prefixes: List[str], algo: str = "md5"
    ) -> str:
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
