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

output_dir = os.path.join(MAIN_DIR, "file", "test", "outputs")
for dir in [os.path.join(output_dir, dir) for dir in os.listdir(output_dir)]:
    for file in [os.path.join(dir, file) for file in os.listdir(dir)]:
        os.remove(file)
    os.removedirs(dir)

files = [os.path.join(os.path.dirname(__file__), "files", file) for file in os.listdir(os.path.join(os.path.dirname(__file__), "files"))] # test files in /files folder

for file in tqdm(files):


    try:
        if any([file.endswith(extension) for extension in ["docx", "doc", "pdf", "txt", "md"]]):

            extractor = FileExtractorDocument(file_path=file)
            txt_chunks = extractor.extract(force_ocr=False) if "EUIN" in file else extractor.extract()

            os.makedirs(os.path.join(output_dir, os.path.basename(file)))
            for idx, txt_chunk in enumerate(txt_chunks):
                extractor._save_chunks(
                    output_path=os.path.join(output_dir, os.path.basename(file), f"{idx+1}.txt"),
                    text_chunks=[txt_chunk["text"]],
                    format="txt"
                    )

    except Exception as e:
        print(e)