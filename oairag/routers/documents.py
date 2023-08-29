import logging
import math
import os
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Request,
    Response,
    status,
    UploadFile,
)
from fastapi.exceptions import HTTPException

from oairag.config import settings
from oairag.models import (
    ErrorResponse,
    DocumentDTO,
    DocumentListDTO,
    Links,
    Meta,
)
from oairag.prepdocs import process_document
from oairag import database

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

db_session = Depends(database.get_db_session)


@router.get(
    path="",
    summary="Get list of documents",
    responses={
        200: {"model": DocumentListDTO, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def get_documents(
    request: Request,
    response: Response,
    page: int = 1,
    size: int = 20,
    session: AsyncSession = db_session,
):
    try:
        return await __get_document_list(session, request, page, size)
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message=f"Error occurred while fetching documents",
            exception=repr(e),
        )


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
    session: AsyncSession = db_session,
):
    """
    Uploads a text document to be processed. Uploaded document will be stored in a document store
    and processed to extract text and store in a vector store as embeddings.

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
        document = await database.get_document_by_filename(session, file.filename)
        if document is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"DocumentDTO already exist with the id: {document.id}",
            )

        async with aiofiles.open(file_path, "wb") as f:
            while contents := await file.read(1024 * 1024):
                await f.write(contents)

        document = await __add_document_entry(session, file.filename)
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


@router.get(
    path="/{document_id}",
    summary="Get document details by document id",
    responses={
        200: {"model": DocumentDTO, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        404: {"model": ErrorResponse, "description": "Not Found"},
    },
)
async def get_document(
    response: Response, document_id: str, session: AsyncSession = db_session
):
    try:
        document = await database.get_document_by_id(session, document_id)
        if document is None:
            raise HTTPException(
                status_code=404, detail=f"DocumentDTO: {document_id} not found"
            )
        else:
            return document
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message=f"Error occurred while retrieving the document with id: {document_id}",
            exception=repr(e),
        )


async def __add_document_entry(session: AsyncSession, filename: str) -> DocumentDTO:
    result = await database.add_document(
        session,
        DocumentDTO(file_name=filename),
    )
    return DocumentDTO.model_validate(result)


async def __get_document_list(
    session: AsyncSession, request: Request, page: int = 1, size: int = 20
) -> DocumentListDTO:
    total_records = await database.get_document_count(session)
    total_pages = math.ceil(total_records / size)
    documents = await database.get_documents(session, page - 1, size)

    if page > total_pages:
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect page value. Page value {page} cannot be greater than {total_pages}",
        )

    prev_page = None if page <= 1 else f"{request.base_url}?page={page-1}&size={size}"
    next_page = (
        None if page >= total_pages else f"{request.base_url}?page={page+1}&size={size}"
    )

    links = Links(
        current_page=f"{request.base_url}documents?page={page}&size={size}",
        first_page=f"{request.base_url}?page=1&size={size}",
        prev_page=prev_page,
        next_page=next_page,
        last_page=f"{request.base_url}?page={total_pages}&size={size}",
    )
    meta = Meta(total_records=total_records, total_pages=total_pages)

    return DocumentListDTO(documents=documents, links=links, meta=meta)
