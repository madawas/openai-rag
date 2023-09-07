import logging
import math
import os
from typing import Optional

import aiofiles
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Request,
    Response,
    status,
    UploadFile,
)
from fastapi.exceptions import HTTPException
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from oairag.config import settings
from oairag.database import DocumentDAO, get_db_session
from oairag.models import (
    ErrorResponse,
    DocumentResponse,
    DocumentListResponse,
    Links,
    Meta,
    SummaryRequest,
    SummaryResponse,
    DocumentWithMetadata,
)
from oairag.prepdocs import process_document, summarise

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
__document_callbacks_router = APIRouter()

db_session = Depends(get_db_session)


@__document_callbacks_router.post(
    path="{$callback_url}",
    response_model=DocumentResponse,
)
def document_processed_notification():
    pass


@__document_callbacks_router.post(
    path="{$callback_url}",
    response_model=SummaryResponse,
)
def document_summary_notification():
    pass


@router.post(
    path="/upload",
    summary="Upload a document to process",
    description="Upload a document to extract the text, chunk it and embed the chunks and store "
    "in a vector store",
    status_code=status.HTTP_201_CREATED,
    callbacks=__document_callbacks_router.routes,
    responses={
        201: {"model": DocumentResponse, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        409: {"model": ErrorResponse, "description": "Conflict"},
    },
)
async def doc_upload(
    response: Response,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: Optional[str] = Form(...),
    callback_url: Optional[HttpUrl] = None,
    session: AsyncSession = db_session,
):
    """
    Uploads a text document to be processed. Uploaded document will be stored in a document store
    and processed to extract text and store in a vector store as embeddings.

    :param response: (Response): The FastAPI Response object to modify in case of errors.
    :param background_tasks: (BackgroundTasks): Asynchronous processing tasks to run on
    uploaded docs.
    :param file: (UploadFile): The UploadFile object representing the uploaded file.
    :param collection: Optional[str]: Collection which the document is added to
    :param callback_url: Optional[HttpUrl]: Callback URL to notify the status of the document
    :param session: Database session

    :returns Union[DocumentResponse, ErrorResponse]: Returns an ErrorResponse object if an error
    occurs, otherwise returns a DocumentResponse.
    """
    file_path = os.path.join(settings.doc_upload_dir, file.filename)

    try:
        document_dao = DocumentDAO(session)
        document = await document_dao.get_document_by_filename(file.filename)
        if document is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"DocumentResponse already exist with the id: {document.id}",
            )

        async with aiofiles.open(file_path, "wb") as f:
            while contents := await file.read(1024 * 1024):
                await f.write(contents)

        document = await __add_document_entry(document_dao, file.filename, collection)
        background_tasks.add_task(
            process_document,
            document_dao,
            file_path,
            document.id,
            collection,
            callback_url,
        )
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
    path="",
    summary="Get list of documents",
    responses={
        200: {"model": DocumentListResponse, "description": "Success"},
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
        document_dao = DocumentDAO(session)
        return await __get_document_list(document_dao, request, page, size)
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message="Error occurred while fetching documents",
            exception=repr(e),
        )


@router.get(
    path="/{document_id}",
    summary="Get document details by document id",
    responses={
        200: {"model": DocumentResponse, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        404: {"model": ErrorResponse, "description": "Not Found"},
    },
)
async def get_document(
    response: Response, document_id: str, session: AsyncSession = db_session
):
    try:
        document_dao = DocumentDAO(session)
        document = await document_dao.get_document_by_id(document_id)
        if document is None:
            raise HTTPException(
                status_code=404, detail=f"DocumentResponse: {document_id} not found"
            )
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


@router.delete(
    path="/{document_id}",
    summary="Get document details by document id",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        404: {"model": ErrorResponse, "description": "Not Found"},
    },
)
async def delete_document(
    response: Response, document_id: str, session: AsyncSession = db_session
):
    try:
        document_dao = DocumentDAO(session)
        await document_dao.delete_document(document_id)
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message=f"Error occurred while retrieving the document with id: {document_id}",
            exception=repr(e),
        )


@router.post(
    path="/{document_id}/summary",
    summary="Generate document summary",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        200: {"model": SummaryResponse, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        404: {"model": ErrorResponse, "description": "Not Found"},
    },
)
async def get_document_summary(
    response: Response,
    background_tasks: BackgroundTasks,
    document_id: str,
    summary_request: SummaryRequest,
    session: AsyncSession = db_session,
):
    try:
        document_dao = DocumentDAO(session)
        ext_record = await document_dao.get_document_by_id(document_id)
        if ext_record is None:
            raise HTTPException(
                status_code=404, detail=f"DocumentResponse: {document_id} not found"
            )
        document = DocumentWithMetadata.model_validate(ext_record)

        if not (document.summary is None and summary_request.regenerate):
            return SummaryResponse(
                document_id=document.id,
                file_name=document.file_name,
                summary=document.summary,
            )
        else:
            if summary_request.synchronous:
                # todo: add additional parameters to generate the summary
                document = await summarise(document)
                background_tasks.add_task(document_dao.update_document, document)
                return SummaryResponse(
                    document_id=document.id,
                    file_name=document.file_name,
                    summary=document.summary,
                )
            else:
                background_tasks.add_task(summarise, document, True, document_dao)
                return Response(status_code=status.HTTP_202_ACCEPTED)
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message=f"Error occurred while retrieving the summary of the document with id:"
            f" {document_id}",
            exception=repr(e),
        )


async def __add_document_entry(
    document_dao: DocumentDAO,
    filename: str,
    collection: str = settings.default_collection,
) -> DocumentResponse:
    result = await document_dao.add_document(
        DocumentResponse(file_name=filename, collection_name=collection),
    )
    return DocumentResponse.model_validate(result)


async def __get_document_list(
    document_dao: DocumentDAO, request: Request, page: int = 1, size: int = 20
) -> DocumentListResponse:
    total_records = await document_dao.get_document_count()
    if total_records > 0:
        total_pages = math.ceil(total_records / size)
        documents = await document_dao.get_documents(page - 1, size)

        if page > total_pages:
            raise HTTPException(
                status_code=400,
                detail=f"Incorrect page value. Page value {page} cannot be greater than "
                f"{total_pages}",
            )

        prev_page = (
            None if page <= 1 else f"{request.base_url}?page={page-1}&size={size}"
        )
        next_page = (
            None
            if page >= total_pages
            else f"{request.base_url}?page={page+1}&size={size}"
        )

        links = Links(
            current_page=f"{request.base_url}documents?page={page}&size={size}",
            first_page=f"{request.base_url}?page=1&size={size}",
            prev_page=prev_page,
            next_page=next_page,
            last_page=f"{request.base_url}?page={total_pages}&size={size}",
        )
        meta = Meta(total_records=total_records, total_pages=total_pages)

        return DocumentListResponse(documents=documents, links=links, meta=meta)
    else:
        return DocumentListResponse(documents=[], links=None, meta=None)
