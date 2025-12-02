import os, sys
from tqdm import tqdm 

MAIN_DIR = os.path.dirname(os.path.dirname((os.path.dirname(__file__))))
if __name__ == "__main__":
    sys.path.append(MAIN_DIR)

from file import (
    FileExtractorDocument,
    FileExtractorMedia,
    FileExtractorSlideshow,
    FileExtractorSpreadsheet,
)


files = [os.path.join(os.path.dirname(__file__), "files", file) for file in os.listdir(os.path.join(os.path.dirname(__file__), "files"))] # test files in /files folder

for file in tqdm(files):

    try:
        if any([file.endswith(extension) for extension in ["docx", "doc", "pdf", "txt", "md"]]):
            extractor = FileExtractorDocument(file_path=file)
            extractor.extract()
            extractor._save_file(output_path=file+".txt")

    except Exception as e:
        print(e)