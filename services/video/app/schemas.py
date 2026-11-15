from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Kind = Literal["video", "poster", "thumbnail"]


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    content_id: int
    kind: str
    content_type: str
    size_bytes: int
    original_filename: str | None = None
    updated_at: datetime


class StreamToken(BaseModel):
    token: str
    expires_in: int
