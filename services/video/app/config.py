from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    log_level: str = "INFO"
    storage_backend: Literal["s3", "local"] = "s3"
    # S3-compatible storage. Leave S3_ENDPOINT_URL empty for real AWS S3 (credentials then come from
    # the default AWS chain, e.g. an IAM role / IRSA on EKS) and set S3_ENDPOINT_URL for MinIO.
    s3_endpoint_url: str = ""
    s3_region: str = "us-east-1"
    s3_bucket: str = "hotstar-media"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    local_storage_path: str = "/data/media"
    max_video_mb: int = 2048
    max_image_mb: int = 10
    stream_token_ttl_seconds: int = 4 * 3600
    seed_data: bool = False
    seed_assets_dir: str = "seed_assets"


@lru_cache
def get_settings() -> Settings:
    return Settings()
