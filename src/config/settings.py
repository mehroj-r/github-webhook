from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General Settings
    APP_NAME: str = "Github Webhook Bot"
    DEBUG: bool = False
    LOG_DIR: str = "logs"
    LOG_FORMAT: Literal["text", "json"] = "text"

    # Telegram Bot Settings
    BOT_TOKEN: str = ""
    USE_WEBHOOK: bool = False
    WEBHOOK_URL: str = ""
    WEBHOOK_SECRET: str = ""
    WEBHOOK_PATH: str = "/webhook"  # /telegram/webhook
    MASTER_CHAT_ID: int | None = None  # For miscellaneous stuff

    # GitHub Settings
    GH_WEBHOOK_SECRET: str = ""
    GH_WEBHOOK_URL: str = ""
    GH_WEBHOOK_PATH: str = "/webhook"  # /github/webhook
    WEBHOOK_PROCESS_IN_BACKGROUND: bool = True  # respond 200 after validation, handle after the response

    # Observability
    METRICS_TOKEN: str = ""  # when set, /misc/metrics requires "Authorization: Bearer <token>"

    # FastAPI Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database Settings
    DATABASE_URL: str = ""
    DATABASE_ECHO: bool = False

    @property
    def telegram_webhook_url(self) -> str:
        """Full public URL Telegram should deliver updates to."""
        return f"{self.WEBHOOK_URL.rstrip('/')}/telegram{self.WEBHOOK_PATH}"


@lru_cache
def _get_settings() -> Settings:
    """
    Create and cache a single instance of Settings.

    :return: Settings instance
    """
    return Settings()
