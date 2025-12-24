import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # General Settings
    APP_NAME: str = "Github Webhook Bot"
    DEBUG: bool = False

    # Telegram Bot Settings
    BOT_TOKEN: str = ""
    USE_WEBHOOK: bool = False
    WEBHOOK_URL: str = ""
    WEBHOOK_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    """
    Create and cache a single instance of Settings.

    :return: Settings instance
    """
    return Settings()
