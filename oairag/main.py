import logging
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from .routers import documents

logging.basicConfig(level=logging.DEBUG)

app = FastAPI(
    debug=True, title="OpenAI Retrieval Augmented Generation API", version="0.0.1"
)

app.include_router(documents.router)


@app.get("/")
def main():
    return RedirectResponse(url="/docs/")
