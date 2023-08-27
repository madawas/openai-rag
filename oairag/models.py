from enum import Enum
from pydantic import BaseModel, ConfigDict, UUID4


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


class DocumentDTO(BaseModel):
    id: UUID4 = None
    file_name: str
    process_status: ProcStatus = ProcStatus.PENDING
    process_description: str | None = None
    collection_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
