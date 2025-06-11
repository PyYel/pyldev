import os
import requests
from tqdm import tqdm
import subprocess
import glob
from typing import Union, Optional
import shutil
import zipfile
import io

from .GitClient import GitClient

class GitClientGithub(GitClient):
    """
    Github client helper for interacting with Github repositories
    """
    def __init__(self,
                 git_repository: str,
                 git_api_url: str = "https://api.github.com",
                 git_token: Optional[str] = None,
                 tmp_dir: Optional[str] = None):
        """
        Github client helper
        """
        super().__init__(git_api_url=git_api_url, git_token=git_token, git_repository=git_repository, tmp_dir=tmp_dir)

        return None
        

    def fetch_repository_contents(self, path="") -> list[dict[str, str]]:
        """Fetch contents of a directory in the repository"""
        headers = {"Authorization": f"token {self.GIT_TOKEN}"} if self.GIT_TOKEN else {}
        url = f"{self.GIT_API_URL}/repos/{self.GIT_REPOSITORY}/contents/{path}"

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"GitClientGithub >> Error fetching repository contents: {response.status_code}")
            print(response.text)
            return []

        return response.json()


    def download_file(self, file_info):
        """Download a single file from GitHub"""
        
        file_path = os.path.join(self.TMP_DIR, file_info["path"])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # For raw file content
        headers = {"Authorization": f"token {self.GIT_TOKEN}"} if self.GIT_TOKEN else {}
        response = requests.get(file_info["download_url"], headers=headers)

        with open(file_path, "wb") as f:
            f.write(response.content)

        return file_path


    def download_directory(self, path: str = "", endswith: str = ""):
        """
        Download all files in a directory recursively from a relative GitHUb repository.

        Args:
            path: Directory path within the repository to download

        Returns:
            List[str]: List of paths to downloaded files
        """
        downloaded_files = []
        contents = self.fetch_repository_contents(path)

        for item in tqdm(contents, desc="Fetching repository content"):
            if item["type"] == "file" and item["path"].endswith(endswith):
                # Download individual file
                file_path = self.download_file(item)
                downloaded_files.append(file_path)
            elif item["type"] == "dir":
                # Recursively download subdirectory
                subdir_files = self.download_directory(item["path"])
                downloaded_files.extend(subdir_files)

        return downloaded_files


    def download_repository(self, endswith: str = "", branch: str = "main"):
        """
        Download the repository as a ZIP archive, rename the extracted folder to match
        the repository name, and filter for files with specific extension.

        Args:
            endswith: File extension to filter
            branch: The branch to download (defaults to "main")

        Returns:
            List[str]: List of paths to matching files
        """

        # Get repository name for the final directory
        repo_name = os.path.basename(self.GIT_REPOSITORY)
        tmp_extract_dir = os.path.join(self.TMP_DIR, "temp_extract")
        os.makedirs(tmp_extract_dir, exist_ok=True)

        # Clean directory if it exists
        for item in os.listdir(tmp_extract_dir):
            item_path = os.path.join(tmp_extract_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        # Final repository directory path
        final_repo_dir = os.path.join(self.TMP_DIR, repo_name)
        if os.path.exists(final_repo_dir):
            shutil.rmtree(final_repo_dir)

        print(f"GitClientGithub >> Downloading repository {self.GIT_REPOSITORY} (branch: {branch})...")
        headers = {}
        if self.GIT_TOKEN:
            headers["Authorization"] = f"token {self.GIT_TOKEN}"

        # Add branch parameter to the URL
        zip_url = f"https://api.github.com/repos/{self.GIT_REPOSITORY}/zipball/{branch}"

        try:
            response = requests.get(zip_url, headers=headers, stream=True)
            response.raise_for_status()

            # Extract the ZIP content to temporary directory
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(tmp_extract_dir)

            # The ZIP extraction creates a subdirectory with a generated name
            # Find that directory and rename it
            subdirs = [d for d in os.listdir(tmp_extract_dir) if os.path.isdir(os.path.join(tmp_extract_dir, d))]
            if not subdirs:
                print("GitClientGithub >> Failed to download the repository from Github.")
                return []

            source_dir = os.path.join(tmp_extract_dir, subdirs[0])
            # Rename by moving the directory to the final location
            shutil.move(source_dir, final_repo_dir)

            print(f"GitClientGithub >> Repository downloaded, extracted, and renamed to {repo_name}.")
            all_files = []
            matching_files = []
            for root, _, files in os.walk(final_repo_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    all_files.append(file_path)

                    if endswith and file.endswith(endswith):
                        matching_files.append(file_path)

            # Remove non-matching files
            files_to_remove = set(all_files) - set(matching_files)
            for file_path in tqdm(files_to_remove, desc="GitClientGithub >> Removing non-matching files"):
                try:
                    os.remove(file_path)
                except OSError as e:
                    print(f"GitClientGithub >> Error removing file {file_path}: {e}")

            # Remove empty directories
            for root, dirs, files in os.walk(final_repo_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except OSError:
                        pass

            # Clean up temporary extraction directory
            shutil.rmtree(tmp_extract_dir, ignore_errors=True)

            print(f"GitClientGithub >> Removed {len(files_to_remove)} files, kept {len(matching_files)} files.")

            return matching_files

        except requests.RequestException as e:
            print(f"GitClientGithub >> Error downloading repository (branch: {branch}): {e}")
            # Clean up temporary directory in case of error
            shutil.rmtree(tmp_extract_dir, ignore_errors=True)
            return []