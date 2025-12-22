import os
from tqdm import tqdm


def count_lines_of_code(root_directory: str):
    total_lines = 0

    # Walk through all files and subdirectories in the given root directory
    for root, dirs, files in os.walk(root_directory):
        # Remove any directory starting with a dot (including '.venv', '__pycache__', etc.)
        dirs[:] = [
            d
            for d in dirs
            if (not d.startswith(".") and d not in [".venv", "__pycache__"])
        ]

        for file in files:
            file_path = os.path.join(root, file)
            if file_path.endswith(".py"):  # Only count Python files
                try:
                    # Open each Python file and count the lines
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        total_lines += len(lines)
                except Exception as e:
                    print(f"Could not read file {file_path}: {e}")

    return total_lines


# Ask for the root directory to analyze
TARGET_DIR_PATH = input("Folder to count lines from: ")
if TARGET_DIR_PATH == "":
    TARGET_DIR_PATH = (
        os.getcwd()
    )  # Use the current working directory if no input is provided

# Calculate and print the total number of lines of code
total_lines = count_lines_of_code(root_directory=TARGET_DIR_PATH)
print(f"Total lines of code in '{TARGET_DIR_PATH}' Python files: {total_lines}")
