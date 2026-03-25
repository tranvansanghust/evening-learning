"""
Configuration management for FastAPI application.

Loads environment variables from .env file and provides typed access
to configuration values through Pydantic settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Database, API, and external service credentials are managed here.
    All configuration is loaded from .env file and environment variables.
    """

    # Database Configuration
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "evening_learning"

    # Telegram Bot Configuration
    telegram_bot_token: str = "8618965675:AAHr3z_bsDl8iJ7Glq8VadtneJo2LlGVnbA"
    telegram_webhook_url: str = ""

    # LLM Configuration (OpenAI-compatible)
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_fast_model: str = "gpt-4o-mini"
    llm_smart_model: str = "gpt-4o"

    # FastAPI Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    class Config:
        """Pydantic config for settings loading."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_database_url(self) -> str:
        """
        Generate SQLAlchemy database URL from configuration.

        Returns:
            str: MySQL database URL in format:
                 mysql+pymysql://user:password@host:port/dbname
        """
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?ssl_disabled=true"
        )


# Global settings instance - instantiate once and reuse
settings = Settings()
