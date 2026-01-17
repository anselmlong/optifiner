"""Configuration for the worker service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Worker settings loaded from environment variables."""

    # LLM Configuration
    anthropic_api_key: str = ""
    google_api_key: str = ""
    default_model: str = "gemini-3-flash"

    # Workspace Configuration
    workspace_path: str = "/app"  # Docker volume mount point for target codebase

    # Execution Limits
    max_file_lines: int = 2000
    max_line_length: int = 2000
    command_timeout: int = 30  # seconds
    max_output_size: int = 100_000  # characters

    # Redis Configuration
    redis_url: str = "redis://redis:6379/0"

    class Config:
        env_prefix = "OPTIFINER_"
        env_file = ".env"


settings = Settings()
