from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    log_level: str = "INFO"
    auth_service_url: str = "http://auth-service:8001"
    user_service_url: str = "http://user-service:8002"
    content_service_url: str = "http://content-service:8003"
    video_service_url: str = "http://video-service:8004"
    watchlist_service_url: str = "http://watchlist-service:8005"
    history_service_url: str = "http://history-service:8006"
    cors_origins: str = "http://localhost:8080,http://localhost:4200"
    max_upload_mb: int = 2100
    upstream_timeout_seconds: float = 30
    upstream_read_timeout_seconds: float = 600
    rate_limit_auth_per_minute: int = 20

    @property
    def upstreams(self) -> dict[str, str]:
        return {
            "auth": self.auth_service_url,
            "users": self.user_service_url,
            "content": self.content_service_url,
            "videos": self.video_service_url,
            "watchlist": self.watchlist_service_url,
            "history": self.history_service_url,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
