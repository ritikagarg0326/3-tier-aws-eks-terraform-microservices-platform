from hotstar_common.app import create_service_app
from hotstar_common.db import check_db

from .config import get_settings
from .db import engine
from .routes import admin, router

settings = get_settings()

app = create_service_app(
    name="auth-service",
    title="hotstar Auth Service",
    description="Registration, login, JWT access/refresh tokens, roles and admin user management.",
    routers=[router, admin],
    readiness_checks={"database": lambda: check_db(engine)},
    log_level=settings.log_level,
)
