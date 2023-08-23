from pydantic import BaseModel
from pydantic import DirectoryPath, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings class to define configuration parameters.

    Attributes:
        model_config (SettingsConfigDict): Configuration dictionary for model settings.
        doc_upload_dir (DirectoryPath): Directory path for document uploads.

    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    doc_upload_dir: DirectoryPath = Field(default='/Users/madawa/projects/openai-rag/test')


settings = Settings()


class SuccessResponse(BaseModel):
    """
    Success response model.

    Attributes:
        status (str): Status of the response ('success').
        message (str): Message indicating the response status.

    """
    status: str = 'success'
    message: str


class ErrorResponse(BaseModel):
    """
    Error response model.

    Attributes:
        status (str): Status of the response ('error').
        message (str): Message indicating the response status.
        exception (str): String representing the exception details.

    """
    status: str = 'error'
    message: str
    exception: str
