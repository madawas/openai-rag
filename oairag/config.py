from pydantic import DirectoryPath, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Union


class Settings(BaseSettings):
    """
    Settings class to define configuration parameters.

    Attributes:
        model_config (SettingsConfigDict): Configuration dictionary for model settings.
        doc_upload_dir (DirectoryPath): Directory path for document uploads.

    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    doc_upload_dir: DirectoryPath = Field(default='/Users/madawa/projects/openai-rag/test')
    chunk_length: int = Field(default=1000)
    chunk_overlap: int = Field(default=300)
    sentence_search_limit: int = Field(default=100)
    form_recogniser_service: Union[str, None] = None


settings = Settings()
