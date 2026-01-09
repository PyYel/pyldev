
import os, sys
from tqdm import tqdm
import json
import shutil

MAIN_DIR = os.path.dirname(os.path.dirname((os.path.dirname(__file__))))
if __name__ == "__main__":
    sys.path.append(MAIN_DIR)

from file import *

os.environ["LOGS_LEVEL"] = "INFO"
# os.environ["LOGS_DIR"] = os.path.dirname(__file__)
os.environ["LOGS_OUTPUT"] = "file, console"

output_dir = os.path.join(MAIN_DIR, "file", "test", "outputs")
os.makedirs(output_dir, exist_ok=True)
for dir in [os.path.join(output_dir, dir) for dir in os.listdir(output_dir)]:
    for file in [os.path.join(dir, file) for file in os.listdir(dir)]:
        os.remove(file)
    os.removedirs(dir)

files = [
    os.path.join(os.path.dirname(__file__), "files", file)
    for file in os.listdir(os.path.join(os.path.dirname(__file__), "files"))
    if not file.endswith(".gitignore")
]  # test files in /files folder

output_paths = [os.path.join(output_dir, os.path.basename(file) + ".pdf") for file in files]

converter = FileConverterPDF()

converter.convert(files)

