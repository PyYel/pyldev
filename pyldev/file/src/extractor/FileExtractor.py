from abc import ABC, abstractmethod
from file import File
from pyldev import _config_logger
from PIL.Image import Image
import io
from typing import Dict, List, Any, Optional, Union, Literal
import json
import sys, os
from collections import defaultdict


from ..element import FileElement, TextElement


class FileExtractor(File):

    def __init__(self) -> None:
        super().__init__()

        self.SUPPORTED_FORMATS = {
            "document": [".pdf", ".docx", ".doc", ".md", ".txt"],
            "media": [".mp3", ".mp4"],
            "slideshow": [".pptx", ".otp"],
            "spreadsheet": [".xlsx", ".csv"],
        }

    @abstractmethod
    def extract(self, *args, **kwargs):
        raise NotImplementedError

    def _save_elements(
        self,
        output_path: str,
        elements: list[FileElement],
        file_name: Optional[str] = None,
        format: Literal["txt", "json"] = "txt",
    ):
        """
        Save batches to disk. format="txt" writes a plain text file with blank-line separators.
        """

        if not isinstance(elements, List):
            elements = [elements]

        if file_name:
            name = file_name
        elif self.file_path:
            name = os.path.basename(self.file_path)
        elif self.file_bytes:
            name = self.file_bytes.name
        else:
            self.logger.warning("Missing file name when saving elements.")
            name = "_default"

        if elements != []:
            os.makedirs(os.path.join(output_path, name))

        if format == "txt":
            for element in elements:
                with open(
                    os.path.join(output_path, name, f"{element.index}.txt"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(element.content + "\n\n")
            return output_path

        elif format == "json":
            for element in elements:
                with open(
                    os.path.join(output_path, name, f"{element.index}.txt"),
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(element.content + "\n\n", f)

        return None

    def _group_elements(
        self,
        elements: List[FileElement],
        index_type: Optional[Literal["page", "slide", "timestamp"]] = "page",
    ) -> List[FileElement]:
        """
        Takes a list of FileElements and returns a list of TextElements, where same
        index FileElement content have been merged together.

        Parameters
        ----------
        elements: List[FileElement]
            List of any ``FileElement`` to merge by index.
        index_type: Optional[str]
            A optional marker to add at the beginning of the grouped content to highlight its index source.

        Returns
        -------
        regruped_elements: List[TextElement]
            List of merged elements (one ``TextElement`` per index)

        Examples
        --------
        >>> grouped_elements = file_extractor._group_elements([
                TextElement(content='hello', index=1)
                ImageElement(content='An other page', index=2)
                ImageElement(content='world', index=1)
            ], index_type='slide')
        >>> print(grouped_elements)
        >>> [{content: 'SLIDE 1:\\n\\nhello world', index=1}, {content: 'SLIDE 2:\\n\\nAn other page', index=2}]
        """

        # Sorts based on FileElement.index value
        grouped_elements = defaultdict(list)
        for element in elements:
            index = element.index
            if index is None:
                continue
            grouped_elements[index].append(element)

        # Merges into same TextElement.content the grouped FileElement.content
        regrouped_elements = []
        for elements in grouped_elements.values():

            index = elements[
                0
            ].index  # Retreive one of the element.index (they are all the same, because grouped by index)
            content = (
                f"{index_type.upper()} {index}:\n\n" if index_type is not None else ""
            )

            for element in elements:
                content += element.content

            regrouped_elements.append(
                TextElement(
                    content=content,
                    source="native",
                    index=index,
                )
            )

        return regrouped_elements
