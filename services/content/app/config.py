from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    log_level: str = "INFO"
    video_service_url: str = "http://video-service:8004"
    seed_data: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
