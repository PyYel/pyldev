import os, sys
from tqdm import tqdm
import json
import shutil

MAIN_DIR = os.path.dirname(os.path.dirname((os.path.dirname(__file__))))
if __name__ == "__main__":
    sys.path.append(MAIN_DIR)

from file import (
    FileExtractorDocument,
    FileExtractorMedia,
    FileExtractorSlideshow,
    FileExtractorSpreadsheet,
)
import pyldev

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

extractor_document = FileExtractorDocument()
extractor_document.logger = pyldev._config_logger(
    logs_name="ExtractorTests",
    logs_output=["console", "file"],
    logs_level="DEBUG",
)

extractor_slideshow = FileExtractorSlideshow()

for file in tqdm(files):

    try:

        elements = extractor_document.extract(file_path=file)
        elements = extractor_document._group_elements(elements=elements)
        extractor_document.file_path = file

        os.makedirs(os.path.join(output_dir, os.path.basename(file)))
        extractor_document._save_elements(
            output_path=output_dir,
            elements=elements,
            format="txt",
        )

        elements = extractor_slideshow.extract(file_path=file)
        extractor_slideshow.file_path = file

        os.makedirs(os.path.join(output_dir, os.path.basename(file)))
        extractor_slideshow._save_elements(
            output_path=output_dir,
            elements=elements,
            format="txt",
        )

    except Exception as e:
        print(e)
