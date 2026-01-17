"""Configuration settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database
    DATABASE_URL: str = "postgresql://optifiner:optifiner_dev@postgres:5432/optifiner"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # GitHub
    GITHUB_TOKEN: str | None = None

    # Worker
    WORKER_WORKSPACE_PATH: str = "/workspaces"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True


settings = Settings()
