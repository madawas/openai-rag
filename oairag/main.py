from fastapi import FastAPI
from .routers import documents
import uvicorn


app = FastAPI(
    debug=True,
    title="OpenAI Retrieval Augmented Generation API",
    version="0.0.1"
)

app.include_router(documents.router)

if __name__ == "__main__":
    print(__package__)
    uvicorn.run(app, host="0.0.0.0", port=8000)