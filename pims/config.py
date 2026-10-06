from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application configuration managed by pydantic-settings.
    Reads from environment variables or a .env file.
    """
    # Use mock by default for safety and to avoid unexpected API costs
    USE_MOCK_LLM: bool = True

    # API Keys (only needed if USE_MOCK_LLM is False)
    OPENAI_API_KEY: Optional[str] = None

    # Model preferences
    DEFAULT_OPENAI_MODEL: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Global settings instance
settings = Settings()
