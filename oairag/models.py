from enum import Enum
from pydantic import BaseModel, ConfigDict, UUID4, HttpUrl


class ErrorResponse(BaseModel):
    """
    Error response model.

    Attributes:
        status (str): Status of the response ('error').
        message (str): Message indicating the response status.
        exception (str): String representing the exception details.

    """

    status: str = "error"
    message: str
    exception: str | None = None


class ProcStatus(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    ERROR = "error"


class DocumentResponse(BaseModel):
    id: UUID4 = None
    file_name: str
    process_status: ProcStatus = ProcStatus.PENDING
    process_description: str | None = None
    collection_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentWithMetadata(BaseModel):
    id: UUID4 = None
    file_name: str
    process_status: ProcStatus = ProcStatus.PENDING
    process_description: str | None = None
    collection_name: str | None = None
    summary: str | None = None
    vectors: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class SummaryResponse(BaseModel):
    document_id: UUID4
    file_name: str
    summary: str


class Links(BaseModel):
    current_page: HttpUrl
    first_page: HttpUrl
    prev_page: HttpUrl | None
    next_page: HttpUrl | None
    last_page: HttpUrl


class Meta(BaseModel):
    total_records: int
    total_pages: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    links: Links
    meta: Meta
