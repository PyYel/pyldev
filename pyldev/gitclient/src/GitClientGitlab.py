import os
import requests
from urllib.parse import quote
from tqdm import tqdm
from typing import Optional, Union
import shutil
import io
import zipfile

from .GitClient import GitClient


class GitClientGitlab(GitClient):
    """
    GitLab client helper for interacting with GitLab repositories
    """

    def __init__(
        self,
        git_repository: str,
        git_api_url: str = "https://gitlab.com/api/v4",
        git_token: Optional[str] = None,
        tmp_dir: Optional[str] = None,
    ):
        """
        GitLab client helper initialization
        """
        super().__init__(
            git_api_url=git_api_url,
            git_token=git_token,
            git_repository=git_repository,
            tmp_dir=tmp_dir,
        )

        return None

    def fetch_repository_contents(self, path="") -> list[dict[str, str]]:
        """
        Fetch contents of a directory in the GitLab repository

        Args:
            path: Path within the repository to fetch

        Returns:
            List of file and directory objects
        """
        headers = {"PRIVATE-TOKEN": self.GIT_TOKEN} if self.GIT_TOKEN else {}

        # URL encode the repository path and the file/directory path
        encoded_repo = quote(self.GIT_REPOSITORY, safe="")
        encoded_path = quote(path, safe="")

        # GitLab API endpoint for repository tree
        url = f"{self.GIT_API_URL}/projects/{encoded_repo}/repository/tree"

        # Add path parameter if specified
        params = {"path": path} if path else {}

        response = requests.get(url, headers=headers, params=params, verify=False)

        if response.status_code != 200:
            print(
                f"GitClientGitlab >> Error fetching repository contents: {response.status_code}"
            )
            print(response.text)
            return []

        # Transform GitLab API response to match the expected format
        contents = response.json()
        transformed_contents = []

        for item in contents:
            # Get additional file info for files (not directories)
            if item["type"] == "blob":
                file_info = self._get_file_info(item["path"])
                transformed_contents.append(
                    {
                        "name": item["name"],
                        "path": item["path"],
                        "type": "file" if item["type"] == "blob" else "dir",
                        "download_url": file_info.get("download_url", ""),
                        "size": file_info.get("size", 0),
                    }
                )
            else:
                transformed_contents.append(
                    {"name": item["name"], "path": item["path"], "type": "dir"}
                )

        return transformed_contents

    def _get_file_info(self, file_path):
        """
        Get detailed information about a specific file

        Args:
            file_path: Path to the file within the repository

        Returns:
            Dict with file information including download URL
        """
        headers = {"PRIVATE-TOKEN": self.GIT_TOKEN} if self.GIT_TOKEN else {}

        # URL encode the repository path and the file path
        encoded_repo = quote(self.GIT_REPOSITORY, safe="")
        encoded_file_path = quote(file_path, safe="")

        # GitLab API endpoint for file content
        url = f"{self.GIT_API_URL}/projects/{encoded_repo}/repository/files/{encoded_file_path}"
        params = {"ref": "main"}  # Default branch, could be configurable

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(
                f"GitClientGitlab >> Error fetching file info: {response.status_code}"
            )
            return {}

        file_info = response.json()

        # Create a raw content URL (GitLab doesn't provide this directly in the API)
        raw_url = f"{self.GIT_API_URL}/projects/{encoded_repo}/repository/files/{encoded_file_path}/raw?ref=main"

        return {
            "download_url": raw_url,
            "size": file_info.get("size", 0),
            "content": file_info.get("content", ""),
            "encoding": file_info.get("encoding", ""),
        }

    def download_file(self, file_info):
        """
        Download a single file from GitLab

        Args:
            file_info: Dictionary containing file information

        Returns:
            Path to the downloaded file
        """
        file_path = os.path.join(self.TMP_DIR, file_info["path"])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        headers = {"PRIVATE-TOKEN": self.GIT_TOKEN} if self.GIT_TOKEN else {}

        # Use the download_url from file_info
        response = requests.get(
            file_info["download_url"], headers=headers, verify=False
        )

        if response.status_code != 200:
            print(f"GitClientGitlab >> Error downloading file: {response.status_code}")
            return None

        with open(file_path, "wb") as f:
            f.write(response.content)

        return file_path

    def download_directory(self, path="", endswith: str = ""):
        """
        Download all files in a directory recursively

        Args:
            path: Directory path within the repository

        Returns:
            List of downloaded file paths
        """
        contents = self.fetch_repository_contents(path)
        downloaded_files = []

        for item in tqdm(contents, desc="Fetching repository content"):
            if item["type"] == "file" and item["path"].endswith(endswith):
                file_path = self.download_file(item)
                if file_path:
                    downloaded_files.append(file_path)
            elif item["type"] == "dir":
                # Recursively download subdirectories
                sub_files = self.download_directory(item["path"])
                downloaded_files.extend(sub_files)

        return downloaded_files

    def download_repository(self, endswith: str = "", branch: str = ""):
        """
        Download the repository as a ZIP archive, rename the extracted folder to match
        the repository name, and filter for files with specific extension.

        Args:
            endswith: File extension to filter
            branch: The branch to download (defaults to "main")
            path: Directory path within the repository (defaults to root)

        Returns:
            List[str]: List of paths to matching files
        """

        repo_name = os.path.basename(self.GIT_REPOSITORY)
        tmp_extract_dir = os.path.join(self.TMP_DIR, "temp_extract")
        os.makedirs(tmp_extract_dir, exist_ok=True)

        for item in os.listdir(tmp_extract_dir):
            item_path = os.path.join(tmp_extract_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        final_repo_dir = os.path.join(self.TMP_DIR, repo_name)
        if os.path.exists(final_repo_dir):
            shutil.rmtree(final_repo_dir)

        print(
            f"GitClientGitlab >> Downloading repository '{self.GIT_REPOSITORY}' (branch: '{branch}')..."
        )
        headers = {}
        if self.GIT_TOKEN:
            headers["PRIVATE-TOKEN"] = self.GIT_TOKEN

        encoded_repo = self.GIT_REPOSITORY.replace("/", "%2F")

        metadata_url = (
            f"{self.GIT_API_URL}/projects/{encoded_repo}/repository/branches/{branch}"
        )
        metadata = requests.get(metadata_url, headers=headers, verify=False).json()
        commit_sha = metadata["commit"]["id"]

        zip_url = f"{self.GIT_API_URL}/projects/{encoded_repo}/repository/archive.zip?sha={commit_sha}"
        try:
            response = requests.get(zip_url, headers=headers, stream=True, verify=False)
            response.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(tmp_extract_dir)

            # The ZIP extraction creates a subdirectory with a generated name
            # Find that directory and rename it
            subdirs = [
                d
                for d in os.listdir(tmp_extract_dir)
                if os.path.isdir(os.path.join(tmp_extract_dir, d))
            ]
            if not subdirs:
                print(
                    "GitClientGitlab >> Failed to download the repository from GitLab."
                )
                return []

            source_dir = os.path.join(tmp_extract_dir, subdirs[0])
            # Rename by moving the directory to the final location
            shutil.move(source_dir, final_repo_dir)

            print(
                f"GitClientGitlab >> Repository downloaded, extracted, and renamed to {repo_name}."
            )
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
            for file_path in tqdm(
                files_to_remove, desc="GitClientGitlab >> Removing non-matching files"
            ):
                try:
                    os.remove(file_path)
                except OSError as e:
                    print(f"GitClientGitlab >> Error removing file {file_path}: {e}")

            # Remove empty directories
            for root, dirs, files in os.walk(final_repo_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except OSError:
                        pass

            shutil.rmtree(tmp_extract_dir, ignore_errors=True)
            print(
                f"GitClientGitlab >> Removed {len(files_to_remove)} files, kept {len(matching_files)} files."
            )

            return matching_files

        except requests.RequestException as e:
            print(
                f"GitClientGitlab >> Error downloading repository (branch: {branch}): {e}"
            )
            # Clean up temporary directory in case of error
            shutil.rmtree(tmp_extract_dir, ignore_errors=True)
            return []
