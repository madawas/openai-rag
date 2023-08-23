from pydantic import DirectoryPath, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False)
    doc_upload_dir: DirectoryPath = Field(default='/Users/madawa/projects/openai-rag/test')

settings = Settings()

print(settings.model_dump())
