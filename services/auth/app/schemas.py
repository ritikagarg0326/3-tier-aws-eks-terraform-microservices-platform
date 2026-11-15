import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")


def _check_password(v: str) -> str:
    if len(v.encode()) > 72:
        raise ValueError("Password must be at most 72 bytes")
    if len(v) < 8 or not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("Password must be at least 8 characters and contain a letter and a digit")
    return v


class RegisterIn(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 3-30 characters: letters, digits, '.', '_' or '-'")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _check_password(v)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class RefreshIn(BaseModel):
    refresh_token: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _check_password(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class AdminUserUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    is_active: bool | None = None


class AuthStats(BaseModel):
    total_users: int
    admins: int
    active_users: int
    new_last_7_days: int
