"""JWT helpers and FastAPI auth dependencies shared by every service.

All services validate the same HS256 access token (issued by auth-service) using the
shared JWT_SECRET, so each service stays secure even when reached without the gateway.
"""
import os
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPBearer

from .errors import ForbiddenError, UnauthorizedError

ROLE_USER = "user"
ROLE_ADMIN = "admin"


@lru_cache
def jwt_config() -> tuple[str, str]:
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be set and at least 32 characters long")
    return secret, os.environ.get("JWT_ALGORITHM", "HS256")


def create_token(claims: dict, token_type: str, ttl_seconds: int, jti: str | None = None) -> str:
    secret, alg = jwt_config()
    now = int(time.time())
    payload = {**claims, "type": token_type, "iat": now, "exp": now + ttl_seconds, "jti": jti or uuid.uuid4().hex}
    return jwt.encode(payload, secret, algorithm=alg)


def decode_token(token: str, expected_type: str = "access") -> dict:
    secret, alg = jwt_config()
    try:
        payload = jwt.decode(token, secret, algorithms=[alg], options={"require": ["exp", "sub", "type"]})
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired", code="token_expired")
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid authentication token", code="invalid_token")
    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type", code="invalid_token")
    return payload


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str
    username: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


def _user_from_payload(payload: dict) -> CurrentUser:
    return CurrentUser(id=int(payload["sub"]), email=payload.get("email", ""), username=payload.get("username", ""), role=payload.get("role", ROLE_USER))


bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token from POST /api/auth/login")


def user_from_request(request: Request) -> CurrentUser:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Missing bearer token", code="missing_token")
    return _user_from_payload(decode_token(token))


def get_current_user(request: Request, _=Depends(bearer_scheme)) -> CurrentUser:
    return user_from_request(request)


def require_roles(*roles: str):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action")
        return user

    return dependency


require_admin = require_roles(ROLE_ADMIN)
