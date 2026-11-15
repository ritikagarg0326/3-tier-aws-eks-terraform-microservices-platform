from hotstar_common.security import create_token

from .conftest import CALLS, bearer


def test_routing_and_header_forwarding(client):
    r = client.get("/api/content/12?x=1&y=a%20b", headers=bearer())
    body = r.json()
    assert r.status_code == 200 and body["host"] == "content-service" and body["path"] == "/content/12" and body["query"] == "x=1&y=a%20b"
    assert body["xrid"] and body["auth"].startswith("Bearer ")
    assert client.get("/api/watchlist", headers=bearer()).json()["host"] == "watchlist-service"
    assert client.get("/api/users/me", headers=bearer()).json()["host"] == "user-service"
    assert client.get("/api/history", headers=bearer()).json()["host"] == "history-service"


def test_unknown_route(client):
    assert client.get("/api/nope/x", headers=bearer()).status_code == 404
    assert client.get("/api", headers=bearer()).status_code == 404


def test_auth_enforced_at_edge(client):
    r = client.get("/api/content")
    assert r.status_code == 401 and r.json()["error"]["code"] == "missing_token"
    assert client.get("/api/content", headers={"Authorization": "Bearer junk"}).status_code == 401
    assert not CALLS  # rejected before reaching any upstream
    refresh_token = create_token({"sub": "1"}, "refresh", 600)
    assert client.get("/api/content", headers={"Authorization": f"Bearer {refresh_token}"}).status_code == 401  # wrong token type


def test_public_routes(client):
    assert client.post("/api/auth/login", json={"email": "a@b.c", "password": "x"}).status_code == 200
    assert client.get("/api/videos/media/3/poster").status_code == 200
    assert client.get("/api/videos/media/3/thumbnail").status_code == 200
    assert client.get("/api/videos/media/3/video").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_video_stream_token_and_range_passthrough(client):
    tok = create_token({"sub": "1", "cid": 3}, "stream", 600)
    r = client.get(f"/api/videos/media/3/video?stream_token={tok}", headers={"Range": "bytes=0-5"})
    assert r.status_code == 206 and r.headers["content-range"] == "bytes 0-5/6" and r.content == b"abcdef"
    assert client.get("/api/videos/media/3/video?stream_token=bad").status_code == 401


def test_body_streaming_and_methods(client):
    r = client.post("/api/content", headers=bearer("admin"), content=b'{"title":"T"}')
    assert r.json()["body"] == '{"title":"T"}' and r.json()["method"] == "POST"
    assert client.delete("/api/content/4", headers=bearer("admin")).json()["method"] == "DELETE"


def test_upstream_failure_is_502(client):
    r = client.get("/api/content/boom", headers=bearer())
    assert r.status_code == 502 and r.json()["error"]["code"] == "bad_gateway"


def test_rate_limit_on_credentials(client):
    codes = [client.post("/api/auth/login", json={}).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3:] == [429, 429]


def test_payload_limit(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    assert client.post("/api/videos/media/1/video", headers={**bearer("admin"), "Content-Length": "10"}, content=b"0123456789").status_code == 413


def test_openapi_rewrite_and_readiness(client):
    spec = client.get("/api/openapi/videos.json", headers=bearer()).json()
    assert list(spec["paths"]) == ["/api/videos/media/{id}"]
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/ready")
    assert ready.status_code == 503 and ready.json()["checks"]["history"] == "http_503" and ready.json()["checks"]["auth"] == "ok"
    assert client.get("/docs").status_code == 200
