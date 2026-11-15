"""Idempotent seed: inserts the sample catalogue only when the table is empty."""
import logging

from hotstar_common.logging import setup_logging
from sqlalchemy import func, select

from .db import SessionLocal
from .models import Content
from .seed_data import SAMPLE_CONTENT


def seed() -> None:
    log = logging.getLogger("seed")
    with SessionLocal() as db:
        if (db.scalar(select(func.count()).select_from(Content)) or 0) > 0:
            log.info("catalogue already populated; skipping seed")
            return
        for title, desc, genre, lang, year, mins, cat, rating, featured in SAMPLE_CONTENT:
            db.add(Content(title=title, description=desc, genre=genre, language=lang, release_year=year, duration_minutes=mins, category=cat, maturity_rating=rating, is_featured=featured))
        db.commit()
        log.info("seeded %d titles", len(SAMPLE_CONTENT))


if __name__ == "__main__":
    setup_logging("content-seed")
    seed()
