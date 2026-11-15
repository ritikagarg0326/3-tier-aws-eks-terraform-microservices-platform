import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    email: str = ""
    username: str = ""
    role: str = "user"
    display_name: str
    bio: str | None = None
    preferred_language: str
    avatar_color: str
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    bio: str | None = Field(default=None, max_length=500)
    preferred_language: str = Field(default="English", min_length=2, max_length=30)
    avatar_color: str = "#1f80e0"

    @field_validator("display_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Display name must not be blank")
        return v

    @field_validator("avatar_color")
    @classmethod
    def _color(cls, v: str) -> str:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            raise ValueError("avatar_color must be a #RRGGBB hex colour")
        return v
