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
from oairag.models import UploadSuccessResponse, ErrorResponse, DocumentBase
from oairag.prepdocs import process_document
from oairag import database

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    path="/upload",
    summary="Upload a document to process",
    description="Upload a document to extract the text, chunk it and embed the chunks and store "
    "in a vector store",
    status_code=status.HTTP_201_CREATED,
    responses={500: {"model": ErrorResponse, "description": "Server Error"}},
)
async def doc_upload(
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(database.get_db_session),
) -> Union[UploadSuccessResponse, ErrorResponse]:
    """
    Uploads a text document to be processed.

    Args:
        :param response: (Response): The FastAPI Response object to modify in case of errors.
        :param background_tasks: (BackgroundTasks): Asynchronous processing tasks to run on
        uploaded docs.
        :param  file: (UploadFile): The UploadFile object representing the uploaded file.
        :param session: Database session

    Returns:
        Union[ErrorResponse, UploadSuccessResponse]: Returns an ErrorResponse object if an error
        occurs,
            otherwise returns a SuccessResponse object indicating successful file upload.

    This function uploads a document file by reading the contents of the provided UploadFile
    object and saving it to the directory specified in the settings. The file is read in chunks
    of 1MB and asynchronously written to the file path. Any exceptions that occur during the upload
    process are caught and handled by modifying the response object's status code and returning an
    ErrorResponse. If the upload is successful, a SuccessResponse is returned.
    """
    file_path = os.path.join(settings.doc_upload_dir, file.filename)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while contents := await file.read(1024 * 1024):
                await f.write(contents)
    except Exception as e:
        response.status_code = 500
        return ErrorResponse(
            message=f"Error occurred while uploading {file.filename}", exception=repr(e)
        )
    finally:
        await file.close()
    # todo: check conflict
    document = DocumentBase(
        file_name=file.filename,
        name_hash=hashlib.sha256(file.filename.encode("utf-8")).hexdigest(),
    )
    document_id = database.add_document(session, document)
    background_tasks.add_task(process_document, file_path)
    return UploadSuccessResponse(document_id=document_id)
