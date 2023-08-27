import logging
from langchain.vectorstores import PGVector
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from oairag.config import settings
from oairag.dao import DocumentDAO
from oairag.models import DocumentDTO

LOG = logging.getLogger(__name__)

_engine = create_engine(
    f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}"
    f"/{settings.postgres_db}"
)

_pg_session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_db_session():
    db_session = _pg_session()
    try:
        yield db_session
    finally:
        db_session.close()


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


def add_document(session: Session, document: DocumentDTO) -> DocumentDTO:
    doc_entry = DocumentDAO(
        file_name=document.file_name,
        process_status=document.process_status,
    )

    session.add(doc_entry)
    session.commit()
    session.refresh(doc_entry)

    return DocumentDTO.model_validate(doc_entry, from_attributes=True)


def get_document_by_filename(session: Session, filename: str) -> DocumentDTO | None:
    document = (
        session.query(DocumentDAO).filter(DocumentDAO.file_name == filename).first()
    )
    if document is not None:
        return DocumentDTO.model_validate(document)
    else:
        return None
