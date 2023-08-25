import logging
import os
from typing import Optional

from langchain.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader
)
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language
from pypdf import PdfReader

from oairag.config import settings
from oairag.exceptions import UnsupportedFileFormatException

LOG = logging.getLogger(__name__)
_EMBEDDINGS = OpenAIEmbeddings()
_FILE_FORMAT_DICT = {
    "md": "markdown",
    "txt": "text",
    "html": "html",
    "shtml": "html",
    "htm": "html",
    "pdf": "pdf"
}


def _get_file_format(file_path: str) -> Optional[str]:
    """Gets the file format from the file name.
    Returns None if the file format is not supported.
    Args:
        file_path (str): The file path of the file whose format needs to be retrieved.
    Returns:
        str: The file format.
    """
    file_path = os.path.basename(file_path)
    file_extension = file_path.split(".")[-1]
    return _FILE_FORMAT_DICT.get(file_extension, None)


def _load_and_split_content(file_path: str, file_format: str) -> list[Document]:
    if file_path is None:
        raise FileNotFoundError(f"File path: {file_path} not found.")

    sentence_endings = [".", "!", "?", "\n\n"]
    words_breaks = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]

    # todo: support token text splitter and add file format based parameters
    if file_format == 'html':
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True,
            separators=RecursiveCharacterTextSplitter.get_separators_for_language(Language.HTML)
        ).split_documents(UnstructuredHTMLLoader(file_path).load())

    if file_format == 'markdown':
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True,
            separators=RecursiveCharacterTextSplitter.get_separators_for_language(Language.MARKDOWN)
        ).split_documents(UnstructuredMarkdownLoader(file_path).load())

    if file_format == 'pdf':
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True,
            separators=sentence_endings + words_breaks
        ).split_documents(PyPDFLoader(file_path).load())

    if file_format == 'text':
        return RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True,
            separators=sentence_endings + words_breaks
        ).split_documents(TextLoader(file_path).load())

    raise UnsupportedFileFormatException(
        f"File: {file_path} with format {file_format} is not supported")


def process_document(file_path: str):
    """
    Processes an uploaded document. Runs the flow to chunk the file content and embed the text
    chunks and store it in a vector collection with other metadata

    :param file_path: Absolute path of the uploaded document to process
    """
    LOG.debug(f"Processing document: {file_path}")
    file_format = _get_file_format(file_path)
    chunks = _load_and_split_content(file_path, file_format)
    LOG.debug(len(chunks))
    LOG.debug(f"{file_path} processing complete")


def get_document_text(filename: str) -> list:
    offset = 0
    page_map = []
    reader = PdfReader(os.path.join(settings.doc_upload_dir, filename))
    pages = reader.pages
    for page_num, p in enumerate(pages):
        page_text = p.extract_text()
        page_map.append((page_num, offset, page_text))
        offset += len(page_text)
    LOG.debug(page_map)
    return page_map
