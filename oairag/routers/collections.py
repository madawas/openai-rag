import logging
import math

from fastapi import status, APIRouter, Depends, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_session, CollectionDAO
from ..models import CollectionModel, ErrorResponse, CollectionListModel, Links, Meta

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/collection", tags=["collection"])

db_session = Depends(get_db_session)


@router.post(
    path="",
    summary="Create a collection",
    description="Create a collection (collection of documents) to place documents",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": CollectionModel, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        409: {"model": ErrorResponse, "description": "Conflict"},
    },
)
async def create_collection(
    response: Response,
    collection: CollectionModel,
    session: AsyncSession = db_session,
):
    try:
        collection_dao = CollectionDAO(session)
        created_collection = await collection_dao.create_collection(collection)
        return CollectionModel.model_validate(created_collection)
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message=f"Error occurred while creating the collection {collection.name}",
            exception=repr(e),
        )


@router.get(
    path="/list",
    summary="Get list of documents",
    responses={
        200: {"model": CollectionListModel, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def get_collection_list(
    request: Request,
    response: Response,
    page: int = 1,
    size: int = 20,
    session: AsyncSession = db_session,
):
    try:
        collection_dao = CollectionDAO(session)
        return await __get_collection_list(collection_dao, request, page, size)
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message="Error occurred while fetching collections",
            exception=repr(e),
        )


@router.get(
    path="/{collection_id}",
    summary="Get document details by document id",
    responses={
        200: {"model": CollectionModel, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        404: {"model": ErrorResponse, "description": "Not Found"},
    },
)
async def get_collection(
    response: Response,
    collection_id: str,
    with_documents: bool = False,
    session: AsyncSession = db_session,
):
    try:
        collection_dao = CollectionDAO(session)
        ext_collection, documents = await collection_dao.get_collection_by_id(
            collection_id, with_documents
        )
        if ext_collection is None:
            raise HTTPException(
                status_code=404, detail=f"Collection: {collection_id} not found"
            )
        collection = CollectionModel.model_validate(ext_collection)
        if with_documents:
            collection.documents = documents
        return collection
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message=f"Error occurred while retrieving the collection with id: {collection_id}",
            exception=repr(e),
        )


async def __get_collection_list(
    collection_dao: CollectionDAO, request: Request, page: int = 1, size: int = 20
) -> CollectionListModel:
    total_records = await collection_dao.get_collection_count()

    if total_records <= 0:
        return CollectionListModel(documents=[], links=None, meta=None)

    total_pages = math.ceil(total_records / size)
    collections = await collection_dao.get_collection_list(page - 1, size)

    if page > total_pages:
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect page value. Page value {page} cannot be greater than "
            f"{total_pages}",
        )

    prev_page = (
        None if page <= 1 else f"{request.base_url}collection?page={page-1}&size={size}"
    )
    next_page = (
        None
        if page >= total_pages
        else f"{request.base_url}collection?page={page+1}&size={size}"
    )

    links = Links(
        current_page=f"{request.base_url}collection?page={page}&size={size}",
        first_page=f"{request.base_url}collection?page=1&size={size}",
        prev_page=prev_page,
        next_page=next_page,
        last_page=f"{request.base_url}collection?page={total_pages}&size={size}",
    )
    meta = Meta(total_records=total_records, total_pages=total_pages)

    return CollectionListModel(collections=collections, links=links, meta=meta)
