"""Application configuration via pydantic-settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://acg:acg@localhost:5432/acg"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Storage
    file_storage_backend: str = "local"
    file_storage_path: str = "./data/files"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "acg-files"
    s3_bucket: str = "acg-files"
    s3_region: str = "eu-south-1"

    # LLM
    llm_provider: str = "ollama"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-oss-120b"
    llm_timeout: int = 45
    ollama_model: str = "llama3.1"
    ollama_base_url: str = "http://localhost:11434/v1"

    # Environment
    environment: str = "development"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
