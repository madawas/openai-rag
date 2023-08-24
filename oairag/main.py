import logging
from fastapi import FastAPI
from .routers import documents

logging.basicConfig(level=logging.DEBUG)

app = FastAPI(
    debug=True,
    title="OpenAI Retrieval Augmented Generation API",
    version="0.0.1"
)

app.include_router(documents.router)
