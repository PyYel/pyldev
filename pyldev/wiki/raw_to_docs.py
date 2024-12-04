import os, sys
import shutil
import re

def process_markdown_file(src, dest):
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replaces file explorer relative paths to html relative paths
    # ./ with ../ 
    processed_content = content
    processed_content = re.sub(r'(\(\./)', '(../', content) # For regular markdown
    processed_content = re.sub(r'(src="\./)', r'src="../', content) # For html beacon
    # ../ with ../../
    processed_content = re.sub(r'(\(\.\./)', '(../../', processed_content)
    processed_content = re.sub(r'(src="\.\./)', r'src="../../', processed_content)
    # .../ with ../../../
    processed_content = re.sub(r'(\(\.\.\./)', '(../../../', processed_content)
    processed_content = re.sub(r'(src="\.\.\./)', r'src="../../../', processed_content)
    # ..../ with ../../../../
    processed_content = re.sub(r'(\(\.\.\.\./)', '(../../../../', processed_content)
    processed_content = re.sub(r'(src="\.\.\.\./)', r'src="../../../../', processed_content)

    # Replace .md with /index.html
    processed_content = re.sub(r'\.md', '/index.html', processed_content)

    with open(dest, 'w', encoding='utf-8') as f:
        f.write(processed_content)

def copy_and_process_markdown_files(src_dir, dest_dir):
    for root, dirs, files in os.walk(src_dir):
        # Skip '.venv' and '__pycache__' directories by modifying dirs list
        dirs[:] = [d for d in dirs if (not d.startswith('.') and d not in ['.venv', '__pycache__', "docs", "lab", "site"])]
        
        # Compute the relative path and create the corresponding destination directory
        relative_path = os.path.relpath(root, src_dir)
        dest_path = os.path.join(dest_dir, relative_path)
        os.makedirs(dest_path, exist_ok=True)
        
        for file in files:
            if file.endswith('.md'):
                src_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(dest_path, file)
                process_markdown_file(src_file_path, dest_file_path)

def copy_home_to_index(directory):
    home_file = os.path.join(directory, 'Home.md')
    index_file = os.path.join(directory, 'index.md')
    
    if os.path.exists(home_file):
        shutil.copyfile(home_file, index_file)
        # print(f"processing: Home.md copied as index.md")
    else:
        print(f"{home_file} does not exist.")

def copy_assets_contents(src, dest):
    src = os.path.join(src, "assets")
    dest = os.path.join(dest, "assets")

    if not os.path.exists(dest):
        os.makedirs(dest)

    try:
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dest, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)  
    except:
        print("Warning: no /assets folder found at the root of /wiki.")
        return None


if __name__ == "__main__":
    src_directory = os.path.join(os.path.dirname(__file__), "raw")
    dest_directory = os.path.join(os.path.dirname(__file__), "docs")
    
    # Ensure the destination directory exists
    os.makedirs(dest_directory, exist_ok=True)
    
    # Process the markdown files
    copy_and_process_markdown_files(src_directory, dest_directory)

    # Copies Assets content
    copy_assets_contents(src_directory, dest_directory)

    # creates index.md as a copy of Home.md
    copy_home_to_index(dest_directory)
