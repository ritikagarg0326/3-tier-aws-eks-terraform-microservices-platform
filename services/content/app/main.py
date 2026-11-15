from hotstar_common.app import create_service_app
from hotstar_common.db import check_db

from .config import get_settings
from .db import engine
from .routes import router

settings = get_settings()

app = create_service_app(
    name="content-service",
    title="hotstar Content Service",
    description="Catalogue of movies, TV shows, web series and other content: metadata, search, filters and admin management.",
    routers=[router],
    readiness_checks={"database": lambda: check_db(engine)},
    log_level=settings.log_level,
)
