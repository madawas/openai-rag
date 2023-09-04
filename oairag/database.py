import logging
from typing import Sequence, Optional, List

from langchain.vectorstores import PGVector
from pgvector.sqlalchemy import Vector
from pydantic import UUID4
from sqlalchemy import select, func, delete, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from oairag.config import settings
from oairag.models import DocumentResponse, DocumentWithMetadata

LOG = logging.getLogger(__name__)

_engine = create_async_engine(
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}"
    f"/{settings.postgres_db}",
    echo=True,
)

_pg_session = async_sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=_engine
)


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


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON, list[float]: Vector}


class DocumentRecord(Base):
    __tablename__ = "document"

    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[UUID4] = mapped_column(
        primary_key=True, index=True, server_default="uuid_generate_v4()"
    )
    file_name: Mapped[str] = mapped_column(unique=True)
    process_status: Mapped[str]
    process_description: Mapped[Optional[str]]
    collection_name: Mapped[str]
    summary: Mapped[Optional[str]]
    embeddings: Mapped[List["Embedding"]] = relationship(
        back_populates="mapped_doc", passive_deletes=True, lazy="selectin"
    )


class Collection(Base):
    __tablename__ = "langchain_pg_collection"
    uuid: Mapped[UUID4] = mapped_column(primary_key=True)
    name: Mapped[str]
    cmetadata: Mapped[dict]
    embeddings: Mapped["Embedding"] = relationship(
        back_populates="collection", passive_deletes=True
    )


class Embedding(Base):
    __tablename__ = "langchain_pg_embedding"
    uuid: Mapped[UUID4] = mapped_column(primary_key=True)
    collection_id: Mapped[UUID4] = mapped_column(
        ForeignKey("langchain_pg_collection.uuid")
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    document: Mapped[str]
    cmetadata: Mapped[dict]
    custom_id: Mapped[UUID4] = mapped_column(ForeignKey("document.id"))
    collection: Mapped["Collection"] = relationship(back_populates="embeddings")
    mapped_doc: Mapped["DocumentRecord"] = relationship(back_populates="embeddings")


class DocumentDAO(object):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_document(self, document: DocumentResponse) -> DocumentRecord:
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

    async def update_document(self, document: DocumentWithMetadata) -> DocumentRecord:
        if document.file_name is None:
            raise ValueError("File name is empty")

        existing_document = await self.get_document_by_filename(document.file_name)

        if existing_document is None:
            raise ValueError(
                f"Cannot find a document with the filename: [{document.file_name}]"
            )

        if (
            existing_document.process_status != document.process_status
            and document.process_status is not None
        ):
            existing_document.process_status = document.process_status

        if existing_document.process_description != document.process_description:
            existing_document.process_description = document.process_description

        if (
            existing_document.summary != document.summary
            and document.summary is not None
        ):
            existing_document.summary = document.summary

        await self.session.commit()
        await self.session.refresh(existing_document)
        return existing_document

    async def delete_document(self, document_id):
        LOG.debug("Deleting document with id: %s", document_id)
        await self.session.execute(
            delete(DocumentRecord).where(DocumentRecord.id == document_id)
        )
        await self.session.flush()
        await self.session.commit()
