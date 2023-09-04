"""
This module defines functions for processing uploaded documents, including loading and chunking
content, as well as embedding text chunks and storing them in a vector collection.

It also provides utility functions to determine file formats and split content based on file formats.
"""
import logging
import os
from typing import Optional

from langchain import OpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
)
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language

from .config import settings
from . import database
from .database import DocumentDAO
from .exceptions import UnsupportedFileFormatException
from .models import ProcStatus, DocumentWithMetadata

LOG = logging.getLogger(__name__)
__EMBEDDINGS = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
__FILE_FORMAT_DICT = {
    "md": "markdown",
    "txt": "text",
    "html": "html",
    "shtml": "html",
    "htm": "html",
    "pdf": "pdf",
}


def __get_file_format(file_path: str) -> Optional[str]:
    """
    Extracts the file format from a given file path.

    :param file_path: The path of the file.

    :returns Optional[str]: The detected file format or None if not supported.
    """
    file_path = os.path.basename(file_path)
    file_extension = file_path.split(".")[-1]
    return __FILE_FORMAT_DICT.get(file_extension, None)


def __load_and_split_content(file_path: str, file_format: str) -> list[Document]:
    """
    Loads and splits the content of a file based on the given file format.

    :param file_path: The path of the file to process.
    :param file_format: The format of the file.

    :returns list[DocumentResponse]: A list of DocumentResponse objects containing the split content.

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


async def __generate_vectors_and_store(
    chunks: list[Document], collection: str, document_id: str
) -> list[str]:
    vector_store = database.get_vector_store(__EMBEDDINGS, collection)
    if settings.openai_api_type == "azure" or settings.openai_api_type == "azure_ad":
        for chunk in chunks:
            # Async Add documents is not yet implemented for PGVector
            return vector_store.add_documents(documents=[chunk], ids=[document_id])
    else:
        ids = [document_id for _ in range(len(chunks))]
        return vector_store.add_documents(documents=chunks, ids=ids)


async def __run_summarize_chain(
    docs: list[Document], llm: OpenAI = None, **kwargs
) -> str:
    if llm is None:
        chain = load_summarize_chain(
            llm=get_llm_model(), chain_type=kwargs.get("chain_type", "refine")
        )
    else:
        chain = load_summarize_chain(
            llm=llm, chain_type=kwargs.get("chain_type", "refine")
        )

    return await chain.arun(docs)


def get_embeddings_function():
    return __EMBEDDINGS


def get_llm_model(**kwargs):
    return OpenAI(
        openai_api_key=settings.openai_api_key,
        model_name=settings.openai_default_llm_model,
        **kwargs,
    )


async def process_document(
    document_dao: DocumentDAO,
    file_path: str,
    document_id: str,
    collection: str,
    generate_summary: bool = False,
):
    """
    Processes an uploaded document. Runs the flow to chunk the file content and embed the text
    chunks and store it in a vector collection with other metadata

    :param document_dao: (DocumentDAO): Document data access object
    :param file_path: (str): Absolute path of the uploaded document to process
    :param document_id: (str): ID of the document
    :param collection: (str): Collection which the document to be added
    :param generate_summary: (bool): Whether to summarize the document
    """
    LOG.debug("Processing document: %s", file_path)
    try:
        file_format = __get_file_format(file_path)
        chunks = __load_and_split_content(file_path, file_format)
        LOG.debug("File [%s] is split in to %d chunks", file_path, len(chunks))
        vectors = await __generate_vectors_and_store(chunks, collection, document_id)

        if generate_summary:
            process_status = ProcStatus.PENDING
            process_description = "Summarizing in progress"
        else:
            process_status = ProcStatus.COMPLETE
            process_description = None

        processed_doc = await document_dao.update_document(
            DocumentWithMetadata(
                file_name=os.path.basename(file_path),
                process_status=process_status,
                prpcess_description=process_description,
                vectors=vectors,
            )
        )
        if generate_summary:
            processed_doc = await summarize(
                DocumentWithMetadata.model_validate(processed_doc)
            )
            processed_doc.process_status = ProcStatus.COMPLETE
            processed_doc.process_description = None
            await document_dao.update_document(processed_doc)
    except Exception as e:
        await document_dao.update_document(
            DocumentWithMetadata(
                file_name=os.path.basename(file_path),
                process_status=ProcStatus.ERROR,
                vectors=repr(e),
            )
        )
    LOG.debug("%s processing complete", file_path)


async def summarize(document: DocumentWithMetadata) -> DocumentWithMetadata:
    doc_list = [
        Document(page_content=e.document, metadata=e.cmetadata)
        for e in document.embeddings
    ]
    summary = await __run_summarize_chain(doc_list)
    document.summary = summary
    return document
