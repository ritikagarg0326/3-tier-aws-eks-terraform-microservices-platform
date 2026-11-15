"""Idempotent seed: creates the sample admin and demo user from environment variables."""
import logging

from hotstar_common.logging import setup_logging
from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .models import User
from .passwords import hash_password


def seed() -> None:
    s = get_settings()
    log = logging.getLogger("seed")
    with SessionLocal() as db:
        for email, username, password, role in (
            (s.admin_email, s.admin_username, s.admin_password, "admin"),
            (s.demo_user_email, s.demo_user_username, s.demo_user_password, "user"),
        ):
            if not (email and password):
                continue
            if db.scalar(select(User).where(User.email == email.lower())):
                continue
            db.add(User(email=email.lower(), username=username, password_hash=hash_password(password), role=role))
            db.commit()
            log.info("seeded %s account", role)


if __name__ == "__main__":
    setup_logging("auth-seed")
    seed()
