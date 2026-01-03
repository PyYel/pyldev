from typing import Literal, Tuple, Union, Optional, List, Annotated, Any
from pydantic import BaseModel, Field

__all__ = [
    "FileElement",  # type hinting
    "TextElement",
    "ImageElement",
    "TableElement",
]


class ImageMetadata(BaseModel):
    """
    Metadata for image elements produced by OCR on extracted images.
    """

    ocr_lang: Optional[str]
    image_format: Optional[str]
    image_dims: Optional[Tuple[int, int]]


class AudioMetadata(BaseModel):
    """
    Metadata for audio extracts.
    """

    transcription_lang: str
    media_format: str
    sampling_frequency: int


class VideoMetadata(BaseModel):
    """
    Metadata for video extracts.
    """

    transcription_lang: str
    media_format: str
    video_dims: Tuple[int, int]


class TextMetadata(BaseModel):
    """
    Metadata for native text elements extracted from document sources.
    """

    bbox: Optional[Tuple[float, float, float, float]]
    ocr_lang: Optional[str]
    ocr_dpi: Optional[int]


class TableMetadata(BaseModel):
    """
    Metadata for table elements extracted from native document sources.
    """

    columns: Optional[List[str]]
    bbox: Optional[Tuple[float, float, float, float]]


class ChunkMetadata(BaseModel):
    """
    Metadata for chunk elements aggregated from different document sources.
    """

    ocr_lang: Optional[str]


class FileMetadata(BaseModel):
    file_name: Optional[str]
    file_format: Optional[str]
    file_date: Optional[str]
    file_author: Optional[str]


class Element(BaseModel):
    """
    Base class for all file Elements.

    Parameters
    ----------
    content: str
        The readable extracted content
    type: Literal
        The type of data represented:
        - ``'text'``: native text from the file
        - ``'table'``: extracted text from a table container
        - ``'image'``: extracted text from a read image
        - ``'chunk'``: aggregated text from multiple sources
    source: Literal
        The extraction process used:
        - ``'native'``: content read direclty from source
        - ``'ocr'``: content extracted using OCR
        - ``'llm'``: content extracted and/or transformed using language models
    index: int
        A marker of the position of the element relative to the file elements order.
        Index is widely impacted by the file type (a timestamp does not work the same as a slide number)
    metadata: Dict
        A subclass of type-specific fields
    file: Dict
        A subclass of source file related metadata
    """

    content: str
    type: Literal["text", "table", "image", "chunk"]
    source: Literal["native", "ocr", "llm"]
    index: int
    file: FileMetadata
    metadata: Union[
        ImageMetadata, AudioMetadata, VideoMetadata, TextMetadata, TableMetadata, Any
    ]

    @classmethod
    def build(cls, *args, **kwargs):
        raise NotImplementedError


class TextElement(Element):
    def __init__(
        self,
        *,
        content: str,
        source: Literal["native", "ocr", "llm"],
        index: int,
        bbox=None,
        ocr_lang=None,
        ocr_dpi=None,
        **kwargs,
    ):
        super().__init__(
            content=content,
            type="text",
            source=source,
            index=index,
            file=FileMetadata(
                file_name=kwargs.get("file_name"),
                file_format=kwargs.get("file_format"),
                file_author=kwargs.get("file_author"),
                file_date=kwargs.get("file_date"),
            ),
            metadata=TextMetadata(bbox=bbox, ocr_lang=ocr_lang, ocr_dpi=ocr_dpi),
        )

    # Legacy / TODO: factories upgrade
    # @classmethod
    # def build(
    #     cls,
    #     *,
    #     content: str,
    #     source: Literal["native", "ocr", "llm"],
    #     index: int,
    #     bbox=None,
    #     ocr_lang=None,
    #     ocr_dpi=None,
    #     **kwargs,
    # ) -> "TextElement":
    #     return cls(
    #         content=content,
    #         type="text",
    #         source=source,
    #         index=index,
    #         file=FileMetadata(
    #             file_name=kwargs.get("file_name"),
    #             file_format=kwargs.get("file_format"),
    #             file_author=kwargs.get("file_author"),
    #             file_date=kwargs.get("file_date"),
    #         ),
    #         metadata=TextMetadata(bbox=bbox, ocr_lang=ocr_lang, ocr_dpi=ocr_dpi),
    #     )


class TableElement(Element):

    def __init__(
        self,
        *,
        content: str,
        source: Literal["native", "ocr", "llm"],
        index: int,
        bbox: Optional[tuple[float, float, float, float]] = None,
        columns: Optional[List[str]] = None,
        file_name: Optional[str] = None,
        file_format: Optional[str] = None,
        file_author: Optional[str] = None,
        file_date: Optional[str] = None,
    ):
        super().__init__(
            content=content,
            type="table",
            source=source,
            index=index,
            file=FileMetadata(
                file_name=file_name,
                file_format=file_format,
                file_author=file_author,
                file_date=file_date,
            ),
            metadata=TableMetadata(columns=columns, bbox=bbox),
        )


class ImageElement(Element):

    def __init__(
        self,
        *,
        content: str,
        index: int,
        source: Literal["ocr"],
        ocr_lang: Optional[str] = None,
        image_format: Optional[str] = None,
        image_dims: Optional[Tuple[int, int]] = None,
        file_name: Optional[str] = None,
        file_format: Optional[str] = None,
        file_author: Optional[str] = None,
        file_date: Optional[str] = None,
    ):
        super().__init__(
            content=content,
            type="image",
            source=source,
            index=index,
            file=FileMetadata(
                file_name=file_name,
                file_format=file_format,
                file_author=file_author,
                file_date=file_date,
            ),
            metadata=ImageMetadata(
                ocr_lang=ocr_lang,
                image_format=image_format,
                image_dims=image_dims,
            ),
        )


# class ChunkElement(Element):
#     """
#     Chunk Element
#     """

#     metadata: ChunkMetadata
#     type: Literal["chunk"] = "chunk"

#     @classmethod
#     def build(
#         cls,
#         *,
#         content: str,
#         index: int,
#         source: Literal["aggregated"],
#         ocr_lang: Optional[str] = None,
#         **kwargs,
#     ) -> "ChunkElement":
#         return cls(
#             content=content,
#             type="chunk",
#             source="aggregated",
#             index=index,
#             file=FileMetadata(
#                 file_name=kwargs.get("file_name"),
#                 file_format=kwargs.get("file_format"),
#                 file_author=kwargs.get("file_author"),
#                 file_date=kwargs.get("file_date"),
#             ),
#             metadata=ChunkMetadata(
#                 ocr_lang=ocr_lang,
#             ),
#         )


FileElement = Annotated[
    Union[
        TextElement,
        TableElement,
        ImageElement,
        # ChunkElement,
    ],
    Field(discriminator="type"),
]
