import logging
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from langchain.vectorstores import PGVector

from oairag.config import settings
from oairag.dao import DocumentDAO
from oairag.models import DocumentDTO

LOG = logging.getLogger(__name__)

_engine = create_async_engine(
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}"
    f"/{settings.postgres_db}",
    echo=True,
)

_pg_session = async_sessionmaker(autocommit=False, autoflush=False, bind=_engine)


async def get_db_session():
    db_session = _pg_session()
    try:
        yield db_session
    finally:
        await db_session.close()


def get_vector_store(
    embedding_function, collection_name=settings.default_collection
) -> PGVector:
    vector_store = PGVector(
        connection_string=f"postgresql+psycopg2://{settings.postgres_user}:"
        f"{settings.postgres_password}@{settings.postgres_host}"
        f"/{settings.postgres_db}",
        collection_name=collection_name,
        embedding_function=embedding_function,
    )
    vector_store.create_tables_if_not_exists()

    return vector_store


async def add_document(session: AsyncSession, document: DocumentDTO) -> DocumentDAO:
    doc_entry = DocumentDAO(
        file_name=document.file_name,
        process_status=document.process_status,
    )

    session.add(doc_entry)
    await session.commit()
    await session.refresh(doc_entry)

    return doc_entry


async def get_documents(
    session: AsyncSession, page: int = 0, size: int = 20
) -> Sequence[DocumentDAO]:
    records = await session.execute(select(DocumentDAO).offset(page * size).limit(size))
    return records.scalars().all()


async def get_document_count(session: AsyncSession) -> int:
    result = await session.execute(func.count(DocumentDAO.id))
    return result.scalar()


async def get_document_by_filename(
    session: AsyncSession, filename: str
) -> DocumentDAO | None:
    records = await session.execute(
        select(DocumentDAO).where(DocumentDAO.file_name == filename)
    )

    return records.scalar_one_or_none()


async def get_document_by_id(
    session: AsyncSession, document_id: str
) -> DocumentDAO | None:
    records = await session.execute(
        select(DocumentDAO).where(DocumentDAO.id == document_id)
    )
    return records.scalars().one_or_none()
