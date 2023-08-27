import logging
import os
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
from fastapi.exceptions import HTTPException

from oairag.config import settings
from oairag.models import ErrorResponse, DocumentDTO
from oairag.prepdocs import process_document
from oairag import database

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    path="/upload",
    summary="Upload a document to process",
    description="Upload a document to extract the text, chunk it and embed the chunks and store "
    "in a vector store",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": DocumentDTO, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        409: {"model": ErrorResponse, "description": "Conflict"},
    },
)
async def doc_upload(
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(database.get_db_session),
):
    """
    Uploads a text document to be processed.

    :param response: (Response): The FastAPI Response object to modify in case of errors.
    :param background_tasks: (BackgroundTasks): Asynchronous processing tasks to run on
    uploaded docs.
    :param  file: (UploadFile): The UploadFile object representing the uploaded file.
    :param session: Database session

    :returns Union[DocumentDTO, ErrorResponse]: Returns an ErrorResponse object if an error
    occurs, otherwise returns a DocumentDTO.
    """
    file_path = os.path.join(settings.doc_upload_dir, file.filename)

    try:
        document = database.get_document_by_filename(session, file.filename)
        if document is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document already exist with the id: {document.id}",
            )

        async with aiofiles.open(file_path, "wb") as f:
            while contents := await file.read(1024 * 1024):
                await f.write(contents)

        document = _add_document_entry(file.filename, session)
        background_tasks.add_task(process_document, file_path)
        return document
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message=f"Error occurred while uploading {file.filename}", exception=repr(e)
        )
    finally:
        await file.close()


def _add_document_entry(filename: str, session: Session) -> DocumentDTO:
    return database.add_document(
        session,
        DocumentDTO(file_name=filename),
    )
