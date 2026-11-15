from .conftest import MP4, PNG


def up(client, h, cid=1, kind="video", data=MP4, name="a.mp4"):
    return client.post(f"/videos/media/{cid}/{kind}", headers=h, files={"file": (name, data, "application/octet-stream")})


def test_upload_requires_admin(client, user_h):
    assert up(client, user_h).status_code == 403
    assert client.post("/videos/media/1/video", files={"file": ("a.mp4", MP4)}).status_code == 401


def test_upload_validation(client, admin_h):
    assert up(client, admin_h, data=b"not a video at all", name="x.mp4").status_code == 415
    assert up(client, admin_h, kind="poster", data=MP4).status_code == 415  # video bytes as poster
    assert up(client, admin_h, kind="video", data=PNG).status_code == 415
    assert up(client, admin_h, kind="banner").status_code == 422
    assert up(client, admin_h, data=b"").status_code in (413, 415)


def test_size_limit(client, admin_h, monkeypatch):
    from app import routes

    s = routes.get_settings()
    monkeypatch.setattr(s, "max_image_mb", 0)
    assert up(client, admin_h, kind="poster", data=PNG, name="p.png").status_code == 413


def test_range_streaming(client, admin_h, user_h):
    assert up(client, admin_h).status_code == 201
    tok = client.post("/videos/stream-token/1", headers=user_h).json()["token"]
    url = f"/videos/media/1/video?stream_token={tok}"
    full = client.get(url)
    assert full.status_code == 200 and full.content == MP4 and full.headers["accept-ranges"] == "bytes"
    assert full.headers["content-type"] == "video/mp4"
    part = client.get(url, headers={"Range": "bytes=10-19"})
    assert part.status_code == 206 and part.content == MP4[10:20]
    assert part.headers["content-range"] == f"bytes 10-19/{len(MP4)}" and part.headers["content-length"] == "10"
    assert client.get(url, headers={"Range": "bytes=100-"}).content == MP4[100:]
    assert client.get(url, headers={"Range": "bytes=-5"}).content == MP4[-5:]
    assert client.get(url, headers={"Range": f"bytes=0-{len(MP4) * 5}"}).content == MP4
    r416 = client.get(url, headers={"Range": f"bytes={len(MP4)}-"})
    assert r416.status_code == 416
    head = client.head(url)
    assert head.status_code == 200 and head.headers["content-length"] == str(len(MP4)) and head.content == b""


def test_video_auth_rules(client, admin_h, user_h):
    up(client, admin_h)
    assert client.get("/videos/media/1/video").status_code == 401
    assert client.get("/videos/media/1/video?stream_token=bogus").status_code == 401
    assert client.get("/videos/media/1/video", headers=user_h).status_code == 200  # bearer header also fine
    up(client, admin_h, cid=2)
    tok = client.post("/videos/stream-token/1", headers=user_h).json()["token"]
    assert client.get(f"/videos/media/2/video?stream_token={tok}").status_code == 403  # token scoped to title 1
    assert client.post("/videos/stream-token/99", headers=user_h).status_code == 404
    access = user_h["Authorization"].split()[1]
    assert client.get(f"/videos/media/1/video?stream_token={access}").status_code == 401  # access token is not a stream token


def test_posters_public_cached_and_replaced(client, admin_h, _env):
    up(client, admin_h, kind="poster", data=PNG, name="p.png")
    r = client.get("/videos/media/1/poster")
    assert r.status_code == 200 and r.content == PNG and r.headers["content-type"] == "image/png"
    assert client.get("/videos/media/1/poster", headers={"If-None-Match": r.headers["etag"]}).status_code == 304
    first = list((_env.root / "content/1/poster").iterdir())
    up(client, admin_h, kind="poster", data=PNG + b"2", name="p2.png")
    assert len(list((_env.root / "content/1/poster").iterdir())) == 1 and first[0].exists() is False  # old object removed
    assert client.get("/videos/media/1/thumbnail").status_code == 404


def test_listing_and_deletion(client, admin_h, user_h, _env):
    up(client, admin_h)
    up(client, admin_h, kind="poster", data=PNG, name="p.png")
    listing = client.get("/videos/media/1", headers=user_h).json()
    assert set(listing) == {"video", "poster"} and listing["video"]["size_bytes"] == len(MP4)
    assert client.delete("/videos/media/1/poster", headers=user_h).status_code == 403
    assert client.delete("/videos/media/1/poster", headers=admin_h).status_code == 204
    assert client.delete("/videos/media/1/poster", headers=admin_h).status_code == 404
    assert client.delete("/videos/media/1", headers=admin_h).status_code == 204
    assert client.get("/videos/media/1", headers=user_h).json() == {}
    assert not any((_env.root / "content/1").rglob("*.mp4"))
    assert client.get("/ready").json()["checks"] == {"database": "ok", "object_storage": "ok"}
