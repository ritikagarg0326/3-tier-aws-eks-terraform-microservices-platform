"""Token issuance and rotation logic."""
from datetime import timedelta

from hotstar_common.db import utcnow
from hotstar_common.errors import UnauthorizedError
from hotstar_common.security import create_token, decode_token
from sqlalchemy import update
from sqlalchemy.orm import Session

from .config import get_settings
from .models import RefreshToken, User
from .schemas import TokenOut, UserOut


def issue_tokens(db: Session, user: User) -> TokenOut:
    s = get_settings()
    access_ttl = s.access_token_ttl_minutes * 60
    claims = {"sub": str(user.id), "email": user.email, "username": user.username, "role": user.role}
    access = create_token(claims, "access", access_ttl)
    refresh_ttl = s.refresh_token_ttl_days * 86400
    refresh = create_token({"sub": str(user.id)}, "refresh", refresh_ttl)
    jti = decode_token(refresh, "refresh")["jti"]
    db.add(RefreshToken(jti=jti, user_id=user.id, expires_at=utcnow() + timedelta(seconds=refresh_ttl)))
    db.commit()
    return TokenOut(access_token=access, refresh_token=refresh, expires_in=access_ttl, user=UserOut.model_validate(user))


def revoke_all(db: Session, user_id: int) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)).values(revoked=True))
    db.commit()


def rotate(db: Session, refresh_token: str) -> TokenOut:
    payload = decode_token(refresh_token, "refresh")
    row = db.get(RefreshToken, payload["jti"])
    if row is None or row.expires_at < utcnow():
        raise UnauthorizedError("Refresh token is invalid", code="invalid_token")
    if row.revoked:  # reuse of a rotated token => assume theft, kill the whole family
        revoke_all(db, row.user_id)
        raise UnauthorizedError("Refresh token has been revoked", code="token_revoked")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is disabled", code="account_disabled")
    row.revoked = True
    db.commit()
    return issue_tokens(db, user)
