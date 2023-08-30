import logging
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from langchain.vectorstores import PGVector

from oairag.config import settings
from oairag.schema import DocumentRecord
from oairag.models import DocumentDTO, ProcStatus

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


class DocumentDAO(object):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_document(self, document: DocumentDTO) -> DocumentRecord:
        doc_entry = DocumentRecord(
            file_name=document.file_name,
            process_status=document.process_status,
            collection_name=document.collection_name,
        )

        self.session.add(doc_entry)
        await self.session.commit()
        await self.session.refresh(doc_entry)

        return doc_entry

    async def get_documents(
        self, page: int = 0, size: int = 20
    ) -> Sequence[DocumentRecord]:
        records = await self.session.execute(
            select(DocumentRecord).offset(page * size).limit(size)
        )
        return records.scalars().all()

    async def get_document_count(self) -> int:
        result = await self.session.execute(func.count(DocumentRecord.id))
        return result.scalar()

    async def get_document_by_filename(self, filename: str) -> DocumentRecord | None:
        records = await self.session.execute(
            select(DocumentRecord).where(DocumentRecord.file_name == filename)
        )

        return records.scalar_one_or_none()

    async def get_document_by_id(self, document_id: str) -> DocumentRecord | None:
        records = await self.session.execute(
            select(DocumentRecord).where(DocumentRecord.id == document_id)
        )
        return records.scalars().one_or_none()

    async def update_document_process_status(
        self, filename: str, status: ProcStatus, description: str | None
    ) -> DocumentRecord:
        if filename is None:
            raise ValueError("File name is empty")

        document = await self.get_document_by_filename(filename)

        if document is None:
            raise ValueError(f"Cannot find a document with the filename: [{filename}]")

        document.process_status = status
        document.process_description = description
        await self.session.commit()
        await self.session.refresh(document)
        return document
