import os

os.environ.update(JWT_SECRET="test-secret-test-secret-test-secret-0123456789", RATE_LIMIT_AUTH_PER_MINUTE="3")

import json as _json  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from hotstar_common.security import create_token  # noqa: E402

from app.main import app  # noqa: E402
from app.proxy import get_client, limiter  # noqa: E402

CALLS: list[httpx.Request] = []


def mk(status=200, *, json=None, content=b"", headers=None):
    data = _json.dumps(json).encode() if json is not None else content
    h = dict(headers or {})
    if json is not None:
        h["content-type"] = "application/json"
    return httpx.Response(status, headers=h, stream=httpx.ByteStream(data))


def upstream(request: httpx.Request) -> httpx.Response:
    CALLS.append(request)
    host = request.url.host
    if host == "video-service" and request.url.path == "/openapi.json":
        return mk(200, json={"info": {"title": "x"}, "paths": {"/videos/media/{id}": {}, "/health": {}}})
    if request.url.path == "/health":
        return mk(503 if host == "history-service" else 200, json={"status": "ok"})
    if host == "content-service" and request.url.path == "/content/boom":
        raise httpx.ConnectError("down")
    if request.url.path.endswith("/video"):
        rng = request.headers.get("range")
        return mk(206 if rng else 200, content=b"abcdef", headers={"Content-Range": "bytes 0-5/6", "Accept-Ranges": "bytes"} if rng else {"Accept-Ranges": "bytes"})
    return mk(200, json={"host": host, "path": request.url.path, "query": request.url.query.decode(), "method": request.method, "body": request.content.decode() if request.content else "", "xrid": request.headers.get("x-request-id"), "auth": request.headers.get("authorization")})


@pytest.fixture(autouse=True)
def _setup():
    CALLS.clear()
    limiter._hits.clear()
    mock = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app.dependency_overrides[get_client] = lambda: mock
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def bearer(role="user"):
    return {"Authorization": "Bearer " + create_token({"sub": "1", "email": "a@b.c", "username": "u", "role": role}, "access", 600)}
