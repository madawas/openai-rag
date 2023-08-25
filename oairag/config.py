from pydantic import DirectoryPath, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Union, Optional


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

    pg_username: str = Field(default="postgres")
    pg_password: str = Field(default="postgres")
    pg_database: str = Field(default="oai_demo_vdb")
    pg_dsn: PostgresDsn = Field(default=f"postgres://{pg_username}:{pg_password}@db:5432/"
                                        f"{pg_database}")


settings = Settings()
