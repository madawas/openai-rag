from enum import Enum
from typing import Union
from pydantic import BaseModel, ConfigDict, UUID4


class UploadSuccessResponse(BaseModel):
    """
    Response when the document upload is successful. Response includes the document id of the
    uploaded document.

    Attributes:
        document_id (UUID4): Id of the uploaded document
    """
    document_id: UUID4


class ErrorResponse(BaseModel):
    """
    Error response model.

    Attributes:
        status (str): Status of the response ('error').
        message (str): Message indicating the response status.
        exception (str): String representing the exception details.

    """
    status: str = 'error'
    message: str
    exception: str


class ProcStatus(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    ERROR = "error"


class DocumentBase(BaseModel):
    id: Union[str, None] = None
    file_name: str
    name_hash: str
    content_hash: Union[str, None] = None
    process_status: ProcStatus = ProcStatus.PENDING
    process_description: Union[str, None] = None
    user_id: Union[str, None] = None
    collection_id: Union[str, None] = None

    model_config = ConfigDict(from_attributes=True)
