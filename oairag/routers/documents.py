import os
import hashlib
from typing import Union
from sqlalchemy.orm import Session
import aiofiles
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Response,
    status,
    UploadFile,
)

from oairag.config import settings
from oairag.models import DocumentResponse, ErrorResponse, DocumentDTO
from oairag.prepdocs import process_document
from oairag import database

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    path="/upload",
    summary="Upload a document to process",
    description="Upload a document to extract the text, chunk it and embed the chunks and store "
    "in a vector store",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={500: {"model": ErrorResponse, "description": "Server Error"}},
)
async def doc_upload(
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(database.get_db_session),
) -> Union[DocumentResponse, ErrorResponse]:
    """
    Uploads a text document to be processed.

    Args:
        :param response: (Response): The FastAPI Response object to modify in case of errors.
        :param background_tasks: (BackgroundTasks): Asynchronous processing tasks to run on
        uploaded docs.
        :param  file: (UploadFile): The UploadFile object representing the uploaded file.
        :param session: Database session

    Returns:
        Union[ErrorResponse, DocumentResponse]: Returns an ErrorResponse object if an error
        occurs, otherwise returns a DocumentResponse.
    """
    file_path = os.path.join(settings.doc_upload_dir, file.filename)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while contents := await file.read(1024 * 1024):
                await f.write(contents)
        # todo: check conflict
        document = _add_document_entry(file.filename, session)
    except Exception as e:
        response.status_code = 500
        return ErrorResponse(
            message=f"Error occurred while uploading {file.filename}", exception=repr(e)
        )
    finally:
        await file.close()
    background_tasks.add_task(process_document, file_path)
    return document


def _add_document_entry(filename: str, session: Session) -> DocumentResponse:
    document = database.add_document(session, DocumentDTO(
        file_name=filename,
        name_hash=hashlib.sha256(filename.encode("utf-8")).hexdigest(),
    ))
    return DocumentResponse.model_validate(document, from_attributes=True)
