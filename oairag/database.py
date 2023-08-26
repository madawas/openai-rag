from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from oairag.config import settings
from oairag.models import DocumentDTO
from oairag.dao import DocumentDAO

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


def add_document(session: Session, document: DocumentDTO) -> DocumentDTO:
    doc_entry = DocumentDAO(
        file_name=document.file_name,
        name_hash=document.name_hash,
        process_status=document.process_status,
        user_id=document.user_id,
    )

    session.add(doc_entry)
    session.commit()
    session.refresh(doc_entry)

    return DocumentDTO.model_validate(doc_entry, from_attributes=True)
