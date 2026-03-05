"""Configuration settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database - PostgreSQL
    DATABASE_URL: str = "postgresql://optifiner:optifiner_dev@localhost:5432/optifiner"

    # GitHub App
    GITHUB_APP_ID: str | None = None
    GITHUB_APP_PRIVATE_KEY: str | None = None  # PEM content or path to PEM file
    GITHUB_APP_CLIENT_ID: str | None = None  # GitHub App Client ID

    # Worker
    WORKER_WORKSPACE_PATH: str = "/tmp/optifiner_workspaces"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

    class Config:
        """Pydantic config."""

        # Resolve .env file path relative to apps/api directory
        # This file is at: apps/api/src/optifiner_api/config.py
        # We want: apps/api/.env
        # So go up 2 levels: src -> optifiner_api -> api
        _config_file = Path(__file__)
        _api_dir = _config_file.parent.parent.parent  # apps/api
        env_file = str(_api_dir / ".env")
        case_sensitive = True
        extra = "ignore"  # Allow extra fields in .env file (like GOOGLE_API_KEY) without validation errors


settings = Settings()
