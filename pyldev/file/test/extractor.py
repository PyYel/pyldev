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
os.makedirs(output_dir, exist_ok=True)
for dir in [os.path.join(output_dir, dir) for dir in os.listdir(output_dir)]:
    for file in [os.path.join(dir, file) for file in os.listdir(dir)]:
        os.remove(file)
    os.removedirs(dir)

files = [
    os.path.join(os.path.dirname(__file__), "files", file) 
    for file in os.listdir(os.path.join(os.path.dirname(__file__), "files")) 
    if not file.endswith(".gitignore")
] # test files in /files folder

for file in tqdm(files):

    try:
        if any([file.endswith(extension) for extension in ["docx", "doc", "pdf", "txt", "md"]]):

            extractor = FileExtractorDocument()
            txt_chunks = extractor.extract(file_path=file)
            extractor.file_path = file

            os.makedirs(os.path.join(output_dir, os.path.basename(file)))
            for idx, txt_chunk in enumerate(txt_chunks):
                extractor._save_chunks(
                    output_path=os.path.join(output_dir, os.path.basename(file), f"{idx+1}.txt"),
                    text_chunks=[txt_chunk["text"] for txt_chunk in txt_chunks],
                    format="txt"
                    )

    except Exception as e:
        print(e)    
