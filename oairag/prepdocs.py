"""
This module defines functions for processing uploaded documents, including loading and chunking
content, as well as embedding text chunks and storing them in a vector collection.

It also provides utility functions to determine file formats and split content based on file formats.
"""
import logging
import os
from typing import Optional

from langchain.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
)
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language

from oairag.config import settings
from oairag.exceptions import UnsupportedFileFormatException

LOG = logging.getLogger(__name__)
_EMBEDDINGS = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
_FILE_FORMAT_DICT = {
    "md": "markdown",
    "txt": "text",
    "html": "html",
    "shtml": "html",
    "htm": "html",
    "pdf": "pdf",
}


def _get_file_format(file_path: str) -> Optional[str]:
    """
    Extracts the file format from a given file path.

    :param file_path: The path of the file.

    :returns Optional[str]: The detected file format or None if not supported.
    """
    file_path = os.path.basename(file_path)
    file_extension = file_path.split(".")[-1]
    return _FILE_FORMAT_DICT.get(file_extension, None)


def _load_and_split_content(file_path: str, file_format: str) -> list[Document]:
    """
    Loads and splits the content of a file based on the given file format.

    :param file_path: The path of the file to process.
    :param file_format: The format of the file.

    :returns list[Document]: A list of Document objects containing the split content.

    :raises UnsupportedFileFormatException: If the file format is not supported.
    """
    if file_path is None:
        raise FileNotFoundError(f"File path: {file_path} not found.")

    sentence_endings = [".", "!", "?", "\n\n"]
    words_breaks = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]

    # todo: support token text splitter and add file format based parameters
    if file_format == "html":
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True,
            separators=RecursiveCharacterTextSplitter.get_separators_for_language(
                Language.HTML
            ),
        ).split_documents(UnstructuredHTMLLoader(file_path).load())

    if file_format == "markdown":
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True,
            separators=RecursiveCharacterTextSplitter.get_separators_for_language(
                Language.MARKDOWN
            ),
        ).split_documents(UnstructuredMarkdownLoader(file_path).load())

    if file_format == "pdf":
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True,
            separators=sentence_endings + words_breaks,
        ).split_documents(PyPDFLoader(file_path).load())

    if file_format == "text":
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True,
            separators=sentence_endings + words_breaks,
        ).split_documents(TextLoader(file_path).load())

    raise UnsupportedFileFormatException(
        f"File: {file_path} with format {file_format} is not supported"
    )


def process_document(file_path: str):
    """
    Processes an uploaded document. Runs the flow to chunk the file content and embed the text
    chunks and store it in a vector collection with other metadata

    :param file_path: Absolute path of the uploaded document to process
    """
    LOG.debug("Processing document: %s", file_path)
    file_format = _get_file_format(file_path)
    chunks = _load_and_split_content(file_path, file_format)
    LOG.debug(len(chunks))
    LOG.debug("%s processing complete", file_path)
