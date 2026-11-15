import asyncio
import logging
import re

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from hotstar_common.errors import AppError, UnauthorizedError
from hotstar_common.logging import request_id_ctx
from hotstar_common.security import bearer_scheme, decode_token, user_from_request
from starlette.background import BackgroundTask

from .config import get_settings
from .ratelimit import RateLimiter

log = logging.getLogger("gateway")
router = APIRouter(tags=["gateway"])

_client: httpx.AsyncClient | None = None
HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade", "host"}
PUBLIC_POST = {"/auth/register", "/auth/login", "/auth/refresh", "/auth/logout"}
PUBLIC_IMAGE = re.compile(r"^/videos/media/\d+/(poster|thumbnail)$")
STREAM_PATH = re.compile(r"^/videos/media/(\d+)/video$")
RATE_LIMITED = {"/auth/register", "/auth/login", "/auth/refresh"}
limiter = RateLimiter(get_settings().rate_limit_auth_per_minute)


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        s = get_settings()
        _client = httpx.AsyncClient(timeout=httpx.Timeout(s.upstream_timeout_seconds, read=s.upstream_read_timeout_seconds), limits=httpx.Limits(max_connections=200, max_keepalive_connections=50), follow_redirects=False)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def authenticate(request: Request, path: str) -> None:
    """Fail fast at the edge; every downstream service re-validates the token itself."""
    method = request.method
    if method == "POST" and path in PUBLIC_POST:
        return
    if method in ("GET", "HEAD") and PUBLIC_IMAGE.match(path):
        return
    if method in ("GET", "HEAD") and (m := STREAM_PATH.match(path)) and not request.headers.get("authorization"):
        token = request.query_params.get("stream_token")
        if not token:
            raise UnauthorizedError("Authentication required to stream video", code="missing_token")
        decode_token(token, "stream")
        return
    user_from_request(request)


@router.get("/api/openapi/{service}.json", include_in_schema=False, dependencies=[Depends(bearer_scheme)])
async def service_openapi(service: str, client: httpx.AsyncClient = Depends(get_client)):
    """Upstream OpenAPI document with paths rewritten to the public /api prefix (used by Swagger UI at /docs)."""
    base = get_settings().upstreams.get(service)
    if base is None:
        raise AppError("Unknown service", status_code=404, code="not_found")
    try:
        r = await client.get(f"{base}/openapi.json", timeout=10)
        r.raise_for_status()
    except httpx.HTTPError:
        raise AppError("Service documentation unavailable", status_code=502, code="bad_gateway")
    spec = r.json()
    spec["paths"] = {f"/api{p}": v for p, v in spec.get("paths", {}).items() if p not in ("/health", "/ready")}
    spec["info"]["title"] = f"hotstar {service} API (via gateway)"
    return JSONResponse(spec)


@router.api_route("/api/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
async def proxy(request: Request, path: str, client: httpx.AsyncClient = Depends(get_client)):
    s = get_settings()
    path = "/" + path.strip("/")
    segment = path.split("/")[1] if path != "/" else ""
    base = s.upstreams.get(segment)
    if base is None:
        raise AppError("Unknown API route", status_code=404, code="not_found")
    authenticate(request, path)
    if request.method == "POST" and path in RATE_LIMITED and not limiter.allow(f"{request.client.host if request.client else 'unknown'}:{path}"):
        raise AppError("Too many attempts, please try again in a minute", status_code=429, code="rate_limited")
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > s.max_upload_mb * 1024 * 1024:
        raise AppError("Request body too large", status_code=413, code="payload_too_large")

    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    headers["x-request-id"] = request_id_ctx.get()
    client_ip = request.client.host if request.client else ""
    headers["x-forwarded-for"] = f"{request.headers.get('x-forwarded-for', client_ip)}".strip()
    has_body = request.method in ("POST", "PUT", "PATCH", "DELETE") and (length not in (None, "0") or "transfer-encoding" in request.headers)
    url = f"{base}{path}" + (f"?{request.url.query}" if request.url.query else "")
    upstream_request = client.build_request(request.method, url, headers=headers, content=request.stream() if has_body else None)
    try:
        upstream = await client.send(upstream_request, stream=True)
    except httpx.TimeoutException:
        raise AppError("Upstream service timed out", status_code=504, code="gateway_timeout")
    except httpx.HTTPError as exc:
        log.warning("upstream unavailable", extra={"service": segment, "error": exc.__class__.__name__})
        raise AppError("Upstream service unavailable", status_code=502, code="bad_gateway")
    out_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP}
    return StreamingResponse(upstream.aiter_raw(), status_code=upstream.status_code, headers=out_headers, background=BackgroundTask(upstream.aclose))


async def _check(client: httpx.AsyncClient, name: str, base: str) -> tuple[str, str]:
    try:
        r = await client.get(f"{base}/health", timeout=2)
        return name, "ok" if r.status_code == 200 else f"http_{r.status_code}"
    except httpx.HTTPError:
        return name, "unreachable"


async def upstream_status(client: httpx.AsyncClient) -> dict[str, str]:
    return dict(await asyncio.gather(*[_check(client, n, u) for n, u in get_settings().upstreams.items()]))
