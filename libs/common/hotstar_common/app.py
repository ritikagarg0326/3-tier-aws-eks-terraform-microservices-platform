"""Application factory so every service gets identical logging, errors, health and docs."""
import inspect
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse

from .errors import register_exception_handlers
from .logging import RequestContextMiddleware, setup_logging


def create_service_app(
    *,
    name: str,
    title: str,
    description: str,
    version: str = "1.0.0",
    routers: list[APIRouter] | None = None,
    readiness_checks: dict[str, Callable[[], None]] | None = None,
    on_startup: Callable[[], None] | None = None,
    on_shutdown: Callable[[], None] | None = None,
    swagger_ui_parameters: dict | None = None,
    default_readiness: bool = True,
    log_level: str = "INFO",
) -> FastAPI:
    setup_logging(name, log_level)
    log = logging.getLogger(name)
    checks = readiness_checks or {}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        log.info("service starting", extra={"version": version})
        if on_startup:
            res = on_startup()
            if inspect.isawaitable(res):
                await res
        yield
        if on_shutdown:
            res = on_shutdown()
            if inspect.isawaitable(res):
                await res
        log.info("service stopped")

    app = FastAPI(title=title, description=description, version=version, lifespan=lifespan, swagger_ui_parameters=swagger_ui_parameters)
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    health = APIRouter(tags=["health"])

    @health.get("/health", summary="Liveness probe")
    def liveness():
        return {"status": "ok", "service": name, "version": version}

    if default_readiness:

        @health.get("/ready", summary="Readiness probe (checks dependencies)")
        def readiness():
            results, ok = {}, True
            for dep, fn in checks.items():
                try:
                    fn()
                    results[dep] = "ok"
                except Exception as exc:  # noqa: BLE001
                    ok = False
                    results[dep] = f"unavailable: {exc.__class__.__name__}"
                    log.warning("readiness check failed", extra={"dependency": dep})
            return JSONResponse({"status": "ready" if ok else "not_ready", "service": name, "checks": results}, status_code=200 if ok else 503)

    app.include_router(health)
    for r in routers or []:
        app.include_router(r)
    return app
