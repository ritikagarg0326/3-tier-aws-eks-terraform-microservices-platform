"""Container entrypoint helper: block until the database accepts connections."""
import logging
import os
import sys
import time

from sqlalchemy import create_engine, text

from .logging import setup_logging


def wait_for_db(url: str, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    engine = create_engine(url, pool_pre_ping=True)
    log = logging.getLogger("startup")
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            log.info("database is reachable")
            return
        except Exception as exc:  # noqa: BLE001
            if time.time() > deadline:
                log.error("database not reachable: %s", exc)
                sys.exit(1)
            log.info("waiting for database...")
            time.sleep(2)


if __name__ == "__main__":
    setup_logging(os.environ.get("SERVICE_NAME", "startup"))
    wait_for_db(os.environ["DATABASE_URL"])
