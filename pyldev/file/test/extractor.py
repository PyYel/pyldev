import os, sys
from tqdm import tqdm 
import json

MAIN_DIR = os.path.dirname(os.path.dirname((os.path.dirname(__file__))))
if __name__ == "__main__":
    sys.path.append(MAIN_DIR)

from file import (
    FileExtractorDocument,
    FileExtractorMedia,
    FileExtractorSlideshow,
    FileExtractorSpreadsheet,
    FileExtractorDocument2,
)


files = [os.path.join(os.path.dirname(__file__), "files", file) for file in os.listdir(os.path.join(os.path.dirname(__file__), "files"))] # test files in /files folder

for file in tqdm(files):

    try:
        if any([file.endswith(extension) for extension in ["docx", "doc", "pdf", "txt", "md"]]):
            extractor = FileExtractorDocument(file_path=file)
            txt_chunks = extractor.extract()
            extractor._save_chunks(
                output_path=file+".txt",
                text_chunks=txt_chunks,
                format="txt"
                )

            extractor = FileExtractorDocument2()
            txt_chunks = extractor.extract(file_path=file)
            extractor._save_chunks(
                output_path=file+"2.txt",
                text_chunks=[json.dumps(txt_chunk) for txt_chunk in txt_chunks],
                format="txt"
                )

    except Exception as e:
        print(e)