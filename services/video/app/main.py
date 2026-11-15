import logging
import time

from hotstar_common.app import create_service_app
from hotstar_common.db import check_db

from .config import get_settings
from .db import engine
from .routes import router
from .storage import get_storage

settings = get_settings()
log = logging.getLogger("video-service")


def _startup() -> None:
    storage = get_storage()
    for attempt in range(1, 11):
        try:
            storage.ensure_ready()
            return
        except Exception as exc:  # noqa: BLE001
            log.warning("object storage not ready (attempt %d): %s", attempt, exc)
            time.sleep(3)
    log.error("object storage unavailable; /ready will report not_ready")


app = create_service_app(
    name="video-service",
    title="hotstar Video Service",
    description="Video, poster and thumbnail upload to S3-compatible storage (MinIO / AWS S3) and HTTP Range streaming.",
    routers=[router],
    readiness_checks={"database": lambda: check_db(engine), "object_storage": lambda: get_storage().ping()},
    on_startup=_startup,
    log_level=settings.log_level,
)
