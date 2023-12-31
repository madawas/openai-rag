from typing import Union, Optional, ClassVar

from pydantic import DirectoryPath, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings class to define configuration parameters.

    Attributes:
        model_config (SettingsConfigDict): Configuration dictionary for model app_settings.
        doc_upload_dir (DirectoryPath): Directory path for document uploads.

    """

    def __init__(self):
        super().__init__(_env_file=".env", _env_file_encoding="utf-8")

    _instance: ClassVar = None

    doc_upload_dir: DirectoryPath = Field(default="/home/uploads")
    chunk_size: int = Field(default=1000)

    chunk_overlap: int = Field(default=300)
    openai_api_key: str
    openai_api_type: Optional[Union[str, None]] = None
    openai_api_version: Optional[Union[str, None]] = None
    openai_default_embeddings_model: str = Field(default="text-embedding-ada-002")

    openai_default_llm_model: str = Field(default="gpt-3.5-turbo-0613")
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_host: str = Field(default="db")

    postgres_db: str = Field(default="oai_demo_vdb")

    default_collection: str = Field(default="oairag_default_collection")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        return cls._instance

    @classmethod
    def get_settings(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
