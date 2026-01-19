"""
API Configuration
Settings and configuration management for the StarStitch API.
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API Settings with environment variable support."""

    # API configuration
    api_title: str = "StarStitch API"
    api_version: str = "0.6.0"
    debug: bool = False

    # CORS configuration
    cors_origins: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Paths
    renders_dir: Path = Path("renders")
    templates_dir: Path = Path("templates")

    # Job configuration
    max_concurrent_jobs: int = 2
    job_timeout_seconds: int = 3600  # 1 hour

    class Config:
        env_prefix = "STARSTITCH_"
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = Settings()
