import logging
from typing import Sequence, Optional, List, Any

from pgvector.sqlalchemy import Vector
from pydantic import UUID4
from sqlalchemy import select, func, delete, ForeignKey, Row, RowMapping
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import Settings
from .models import DocumentResponse, DocumentWithMetadata, CollectionModel

LOG = logging.getLogger(__name__)

settings = Settings.get_settings()

_engine = create_async_engine(
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}"
    f"/{settings.postgres_db}",
    echo=True,
)

_pg_session = async_sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=_engine
)


async def get_db_session() -> AsyncSession:
    """
    Get an asynchronous database session.

    :return: AsyncSession: A database session.
    """
    db_session = _pg_session()
    try:
        yield db_session
    finally:
        await db_session.close()


class Base(DeclarativeBase):
    """
    Base class for SQLAlchemy declarative models.
    """

    type_annotation_map = {dict: JSON, list[float]: Vector}


class DocumentRecord(Base):
    """
    Represents a document record in the database.
    """

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


class CollectionRecord(Base):
    """
    Represents a collection in the database.
    """

    __tablename__ = "langchain_pg_collection"
    uuid: Mapped[UUID4] = mapped_column(primary_key=True)
    name: Mapped[str]
    cmetadata: Mapped[dict]
    embeddings: Mapped["Embedding"] = relationship(
        back_populates="collection", passive_deletes=True
    )


class Embedding(Base):
    """
    Represents an embedding in the database.
    """

    __tablename__ = "langchain_pg_embedding"
    uuid: Mapped[UUID4] = mapped_column(primary_key=True)
    collection_id: Mapped[UUID4] = mapped_column(
        ForeignKey("langchain_pg_collection.uuid")
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    document: Mapped[str]
    cmetadata: Mapped[dict]
    custom_id: Mapped[UUID4] = mapped_column(ForeignKey("document.id"))
    collection: Mapped["CollectionRecord"] = relationship(back_populates="embeddings")
    mapped_doc: Mapped["DocumentRecord"] = relationship(back_populates="embeddings")


class DocumentDAO(object):
    """
    Data Access Object (DAO) for managing document records.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the DocumentDAO.

        :param session: An asynchronous database session.
        """
        self.session = session

    async def add_document(self, document: DocumentResponse) -> DocumentRecord:
        """
        Add a document to the database.

        :param document: The document to add.

        :return: DocumentRecord: The added document record.
        """
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
        """
        Get a list of documents from the database.

        :param page: The page number. Defaults to 0.
        :param size: The number of documents per page. Defaults to 20.

        :return: Sequence[DocumentRecord]: A list of document records.
        """
        records = await self.session.execute(
            select(DocumentRecord).offset(page * size).limit(size)
        )
        return records.scalars().all()

    async def get_document_count(self) -> int:
        """
        Get the total count of documents in the database.

        :return: int: The document count.
        """
        result = await self.session.execute(func.count(DocumentRecord.id))
        return result.scalar()

    async def get_document_by_filename(self, filename: str) -> DocumentRecord | None:
        """
        Get a document record by filename.

        :param filename: The filename of the document.

        :return: DocumentRecord | None: The document record if found, else None.
        """
        records = await self.session.execute(
            select(DocumentRecord).where(DocumentRecord.file_name == filename)
        )

        return records.scalar_one_or_none()

    async def get_document_by_id(self, document_id: str) -> DocumentRecord | None:
        """
        Get a document record by ID.

        :param document_id: The ID of the document.

        :return: DocumentRecord | None: The document record if found, else None.
        """
        records = await self.session.execute(
            select(DocumentRecord).where(DocumentRecord.id == document_id)
        )
        return records.scalars().one_or_none()

    async def update_document(self, document: DocumentWithMetadata) -> DocumentRecord:
        """
        Update a document record.

        :param document: The updated document.

        :return: DocumentRecord: The updated document record.
        """
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
        """
        Delete a document record by ID.

        :param document_id: The ID of the document.
        """
        LOG.debug("Deleting document with id: %s", document_id)
        await self.session.execute(
            delete(DocumentRecord).where(DocumentRecord.id == document_id)
        )
        await self.session.flush()
        await self.session.commit()


class CollectionDAO(object):
    """
    Data Access Object (DAO) for managing collections
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the CollectionDAO.

        :param session: An asynchronous database session.
        """
        self.session = session

    async def create_collection(self, collection: CollectionModel) -> CollectionRecord:
        """
        Create a new collection in the database.

        :param collection: The collection to create.

        :return: CollectionRecord: The created collection record.
        """
        collection = CollectionRecord(
            name=collection.name, cmetadata=collection.cmetadata
        )

        self.session.add(collection)
        await self.session.commit()
        await self.session.refresh(collection)

        return collection

    async def get_collection_by_id(
        self, collection_id: str, with_documents: bool = False
    ) -> tuple[CollectionRecord | None, Sequence[Row | RowMapping | Any] | None]:
        """
        Get a collection by its ID and optionally retrieve associated documents.

        :param collection_id: The ID of the collection to retrieve.
        :param with_documents: Whether to include associated documents.

        :return: tuple[CollectionRecord | None, Sequence[Row | RowMapping | Any] | None]:
            A tuple containing the collection record (or None if not found)
            and a list of associated documents (or None if with_documents is False).
        """
        documents = None
        rows = await self.session.execute(
            select(CollectionRecord).where(CollectionRecord.uuid == collection_id)
        )
        collection = rows.scalars().one_or_none()
        if collection and with_documents:
            rows = await self.session.execute(
                select(DocumentRecord.file_name).where(
                    DocumentRecord.collection_name == collection.name
                )
            )
            documents = rows.scalars().all()

        return collection, documents

    async def get_collection_count(self) -> int:
        """
        Get the total count of collections in the database.

        :return: int: The collection count.
        """
        result = await self.session.execute(func.count(CollectionRecord.uuid))
        return result.scalar()

    async def get_collection_list(
        self, page: int = 0, size: int = 20
    ) -> Sequence[CollectionRecord]:
        """
        Get a list of collections with optional pagination.

        :param page: The page number. Defaults to 0.
        :param size: The number of collections per page. Defaults to 20.

        :return: Sequence[CollectionRecord]: A list of collection records.
        """
        records = await self.session.execute(
            select(CollectionRecord).offset(page * size).limit(size)
        )

        return records.scalars().all()
