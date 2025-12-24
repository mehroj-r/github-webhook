from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DEBUG: bool = False


@lru_cache
def get_settings() -> Settings:
    """
    Create and cache a single instance of Settings.
    This ensures the singleton pattern - only one instance is created.
    """
    return Settings()
