
import os, sys


ROOT_DIR_PATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if __name__ == "__main__":
    sys.path.append(ROOT_DIR_PATH)

from htmltools import generate_homepage

if __name__ == "__main__":
    generate_homepage(input_dir=os.path.dirname(__file__), output_path=os.path.join(os.path.dirname(__file__), "home.html"))