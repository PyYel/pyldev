import os
import requests
import subprocess
import tempfile
import shutil
from pathlib import Path
import time
from typing import Optional, Union


class GitClient:
    """
    Client base class
    """

    def __init__(
        self,
        git_api_url: str,
        git_repository: str,
        git_token: Optional[str] = None,
        tmp_dir: Optional[str] = None,
    ):

        self.GIT_API_URL = git_api_url
        self.GIT_TOKEN = git_token
        self.GIT_REPOSITORY = git_repository
        self.TMP_DIR = tmp_dir

        if self.TMP_DIR is None:
            self.TMP_DIR = os.path.join(os.getcwd(), "tmp")
            os.makedirs(self.TMP_DIR, exist_ok=True)
            print(f"GitClient >> Temporary directory created: '{self.TMP_DIR}'.")

        return None
