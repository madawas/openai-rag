import logging

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db_session, CollectionDAO
from .models import ChatRequest, ChatResponse, ErrorResponse
from .routers import documents, collections

logging.basicConfig(level=logging.DEBUG)

app = FastAPI(
    debug=True, title="OpenAI Retrieval Augmented Generation API", version="0.0.1"
)

app.include_router(documents.router)
app.include_router(collections.router)


@app.post(
    path="/chat",
    summary="Ask a question from a collection or a document",
    tags=["rag"],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": ChatResponse, "description": "Success"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        409: {"model": ErrorResponse, "description": "Conflict"},
    },
)
async def chat_completion(
    response: Response, chat_request: ChatRequest, session: AsyncSession = Depends(get_db_session)
):
    try:
        if not chat_request.collection_name:
            raise HTTPException(status_code=400, detail=f"Collection name is empty")

        collection_dao = CollectionDAO(session)
        collection, _ = collection_dao.get_collection_by_name(chat_request.collection_name, False)
        return __get_qa_result(chat_request)
    except HTTPException as e:
        response.status_code = e.status_code
        return ErrorResponse(message=e.detail)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return ErrorResponse(
            message="Error occurred while fetching collections",
            exception=repr(e),
        )


async def __get_qa_result(chat_request: ChatRequest) -> ChatResponse:
    pass
