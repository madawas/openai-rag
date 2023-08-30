from pydantic import UUID4
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[UUID4] = mapped_column(
        primary_key=True, index=True, server_default="uuid_generate_v4()"
    )
    file_name: Mapped[str] = mapped_column(unique=True)
    process_status: Mapped[str]
    process_description: Mapped[str]
    collection_name: Mapped[str]
