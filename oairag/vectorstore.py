from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain.vectorstores import PGVector

from .config import Settings

settings = Settings.get_settings()

__EMBEDDINGS = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)


async def generate_vectors_and_store(
    chunks: list[Document], collection: str, document_id: str
):
    vector_store = get_vector_store(__EMBEDDINGS, collection)
    if settings.openai_api_type in ("azure", "azure_ad"):
        for chunk in chunks:
            # Async Add documents is not yet implemented for PGVector
            vector_store.add_documents(documents=[chunk], ids=[document_id])
    else:
        ids = [document_id for _ in range(len(chunks))]
        vector_store.add_documents(documents=chunks, ids=ids)


def get_embeddings_function():
    return __EMBEDDINGS


def get_vector_store(
    embedding_function, collection_name=settings.default_collection
) -> PGVector:
    """
    Get a PGVector store.

    :param embedding_function: The embedding function.
    :param collection_name: The name of the collection. Defaults to app_settings.default_collection.

    :return: PGVector: A PGVector store.
    """
    vector_store = PGVector(
        connection_string=f"postgresql+psycopg2://{settings.postgres_user}:"
        f"{settings.postgres_password}@{settings.postgres_host}"
        f"/{settings.postgres_db}",
        collection_name=collection_name,
        embedding_function=embedding_function,
    )
    vector_store.create_tables_if_not_exists()

    return vector_store
