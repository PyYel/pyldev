import os, sys
import shutil

def process_markdown_file(src, dest):
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()
    
    processed_content = content.replace('.md', '')
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(processed_content)

def copy_and_process_markdown_files(src_dir, dest_dir):
    for root, dirs, files in os.walk(src_dir):
        # Skip '.venv' and '__pycache__' directories by modifying dirs list
        dirs[:] = [d for d in dirs if (not os.path.basename(d).startswith('.') and d not in ['.venv', '__pycache__', "docs", "lab", "site"])]
        
        # Compute the relative path and create the corresponding destination directory
        relative_path = os.path.relpath(root, src_dir)
        dest_path = os.path.join(dest_dir, relative_path)
        os.makedirs(dest_path, exist_ok=True)
        
        for file in files:
            if file.endswith('.md'):
                src_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(dest_path, file)
                process_markdown_file(src_file_path, dest_file_path)

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
        return None


if __name__ == "__main__":
    src_directory = os.path.join(os.path.dirname(__file__), "raw")
    dest_directory = os.path.join(os.path.dirname(__file__), "gitlab")
    
    # Ensure the destination directory exists
    os.makedirs(dest_directory, exist_ok=True)
    
    # Process the markdown files
    copy_and_process_markdown_files(src_directory, dest_directory)

    # Copies Assets content
    copy_assets_contents(src_directory, dest_directory)
        
