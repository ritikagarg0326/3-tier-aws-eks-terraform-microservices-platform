import json
import logging
import os

os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-0123456789"

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from hotstar_common.app import create_service_app
from hotstar_common.errors import ConflictError
from hotstar_common.logging import JsonFormatter
from hotstar_common.security import CurrentUser, create_token, decode_token, get_current_user, require_admin


def make_app():
    app = create_service_app(name="t", title="t", description="t", readiness_checks={"dep": lambda: (_ for _ in ()).throw(RuntimeError("down"))})

    @app.get("/me")
    def me(u: CurrentUser = Depends(get_current_user)):
        return {"id": u.id, "role": u.role}

    @app.get("/admin")
    def admin(u: CurrentUser = Depends(require_admin)):
        return {"ok": True}

    @app.get("/conflict")
    def conflict():
        raise ConflictError("dup", code="dup")

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internals")

    return app


def token(role="user", ttl=60, typ="access"):
    return create_token({"sub": "7", "email": "a@b.c", "username": "u", "role": role}, typ, ttl)


def test_token_types_and_expiry():
    assert decode_token(token())["sub"] == "7"
    with pytest.raises(Exception):
        decode_token(token(typ="refresh"))
    with pytest.raises(Exception):
        decode_token(token(ttl=-10))


def test_auth_dependencies_and_error_envelope():
    c = TestClient(make_app(), raise_server_exceptions=False)
    assert c.get("/me").status_code == 401
    assert c.get("/me", headers={"Authorization": f"Bearer {token()}"}).json() == {"id": 7, "role": "user"}
    assert c.get("/admin", headers={"Authorization": f"Bearer {token()}"}).status_code == 403
    assert c.get("/admin", headers={"Authorization": f"Bearer {token('admin')}"}).status_code == 200
    r = c.get("/conflict")
    assert r.status_code == 409 and r.json()["error"]["code"] == "dup" and r.headers["x-request-id"]
    r = c.get("/boom")
    assert r.status_code == 500 and "secret" not in r.text and r.json()["error"]["code"] == "internal_error"
    assert c.get("/nope").json()["error"]["code"] == "http_404"


def test_health_and_readiness():
    c = TestClient(make_app())
    assert c.get("/health").json()["status"] == "ok"
    r = c.get("/ready")
    assert r.status_code == 503 and r.json()["checks"]["dep"].startswith("unavailable")


def test_json_log_format():
    rec = logging.LogRecord("x", logging.INFO, "f", 1, "hello %s", ("w",), None)
    rec.custom = 5
    out = json.loads(JsonFormatter("svc").format(rec))
    assert out["message"] == "hello w" and out["service"] == "svc" and out["custom"] == 5
