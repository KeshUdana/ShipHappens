from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Application settings loaded from .env"""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    gemini_api_key: str = ""
    supabase_storage_url: str = ""
    app_name: str = "ShipHappens"
    debug: bool = False

settings = Settings()
