"""Centralised exception handling producing one consistent error envelope."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import request_id_ctx

log = logging.getLogger("errors")


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str = "", *, status_code: int | None = None, code: str | None = None, details=None):
        super().__init__(message)
        self.message = message or self.__class__.__name__
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.details = details


class NotFoundError(AppError):
    status_code, code = 404, "not_found"


class ConflictError(AppError):
    status_code, code = 409, "conflict"


class UnauthorizedError(AppError):
    status_code, code = 401, "unauthorized"


class ForbiddenError(AppError):
    status_code, code = 403, "forbidden"


class BadGatewayError(AppError):
    status_code, code = 502, "bad_gateway"


def _body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details, "request_id": request_id_ctx.get()}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status_code, headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        return JSONResponse(_body(f"http_{exc.status_code}", str(exc.detail)), status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path")), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(_body("validation_error", "Request validation failed", details), status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("unhandled exception")
        return JSONResponse(_body("internal_error", "Internal server error"), status_code=500)
