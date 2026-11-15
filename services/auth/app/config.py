from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    log_level: str = "INFO"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7
    bcrypt_rounds: int = 12
    seed_data: bool = False
    admin_email: str = ""
    admin_username: str = "admin"
    admin_password: str = ""
    demo_user_email: str = ""
    demo_user_username: str = "demo"
    demo_user_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
