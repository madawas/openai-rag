from sqlalchemy import Column, String, UUID
from sqlalchemy.ext.declarative import declarative_base

DeclarativeBase = declarative_base()


class DocumentSchema(DeclarativeBase):
    __tablename__ = "documents"
    id = Column(UUID, primary_key=True, index=True, server_default="uuid_generate_v4()")
    file_name = Column(String)
    name_hash = Column(String)
    content_hash = Column(String)
    process_status = Column(String)
    process_description = Column(String)
    user_id = Column(String)
    collection_id = Column(String)
