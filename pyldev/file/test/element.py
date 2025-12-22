import os, sys


MAIN_DIR = os.path.dirname(os.path.dirname((os.path.dirname(__file__))))
if __name__ == "__main__":
    sys.path.append(MAIN_DIR)

from file import *


def test(el: FileElement):

    if el.type == "image":
        print(el.metadata.image_dims)
    elif el.type == "text":
        print(el.metadata.bbox)


el = TextElement.build(content="test", source="native", index=1, bbox=(1, 1, 1, 1))
test(el=el)
el = ImageElement.build(content="test", source="ocr", index=1, image_dims=(1, 1))
test(el=el)
