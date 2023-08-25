from typing import Union, Optional
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
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=300)

    openai_api_key: str
    openai_api_type: Optional[Union[str, None]] = None
    openai_api_version: Optional[Union[str, None]] = None

    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_host: str = Field(default="db")
    postgres_db: str = Field(default="oai_demo_vdb")


settings = Settings()
