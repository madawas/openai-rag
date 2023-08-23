import os
import aiofiles
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from ..config import settings

router = APIRouter(
    prefix='/documents',
    tags=['documents']
)


@router.post(
    path='/upload'
)
async def doc_upload(file: UploadFile = File(...)) -> JSONResponse:
    print(settings.model_dump())
    file_path = os.path.join(settings.doc_upload_dir, file.filename)
    print(file_path)

    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while contents := await file.read(1024 * 1024):
                await f.write(contents)
    except Exception as error:
        return JSONResponse(
            content={
                'status': 'error',
                'message': f'Error occurred while uploading {file.filename}',
                'exception': str(error)
            },
            status_code=500
        )
    finally:
        await file.close()
    return JSONResponse(
        content={
            'status': 'success',
            'message': f'File {file.filename} uploaded successfully'
        },
        status_code=201
    )
