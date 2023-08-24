from pydantic import BaseModel

class SuccessResponse(BaseModel):
    """
    Success response model.

    Attributes:
        status (str): Status of the response ('success').
        message (str): Message indicating the response status.

    """
    status: str = 'success'
    message: str


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
