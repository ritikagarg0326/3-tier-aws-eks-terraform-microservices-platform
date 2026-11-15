#!/usr/bin/env python3
"""End-to-end smoke test that drives the whole platform through the API gateway.

Usage:  python scripts/e2e_smoke.py [GATEWAY_URL]        (default http://localhost:8000)
Credentials come from the environment (same names as .env): ADMIN_EMAIL, ADMIN_PASSWORD.
Only needs the Python standard library.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GATEWAY_URL", "http://localhost:8000")).rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@hotstar-demo.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SAMPLE = Path(__file__).resolve().parent.parent / "services/video/seed_assets"
results: list[tuple[str, bool, str]] = []


def call(method, path, token=None, body=None, headers=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    h = dict(headers or {})
    if data is not None:
        h["Content-Type"] = ctype
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = r.read()
            return r.status, (json.loads(payload) if payload and "json" in r.headers.get("content-type", "") else payload), r.headers
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload), e.headers
        except ValueError:
            return e.code, payload, e.headers


def multipart(filename, content, ctype):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"   -> {detail}"))


def main():
    print(f"hotstar end-to-end smoke test against {BASE}\n")
    for _ in range(30):
        s, body, _h = call("GET", "/ready")
        if s == 200:
            break
        time.sleep(2)
    check("gateway reports all services ready", s == 200, str(body))

    s, tokens, _ = call("POST", "/api/auth/login", body={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    check("admin login", s == 200 and tokens["user"]["role"] == "admin", str(tokens))
    admin = tokens["access_token"]
    uname = "smoke" + uuid.uuid4().hex[:8]
    s, reg, _ = call("POST", "/api/auth/register", body={"email": f"{uname}@example.com", "username": uname, "password": "Smoke1234!"})
    check("user registration", s == 201 and reg["user"]["role"] == "user", str(reg))
    user = reg["access_token"]

    check("unauthenticated request rejected", call("GET", "/api/content")[0] == 401)
    check("viewer cannot create content", call("POST", "/api/content", user, {"title": "x"})[0] in (403, 422))

    s, facets, _ = call("GET", "/api/content/facets", user)
    check("facets endpoint", s == 200 and len(facets["genres"]) > 0, str(facets))
    s, page, _ = call("GET", "/api/content?page_size=5", user)
    check("seeded catalogue is browsable", s == 200 and page["total"] >= 1, str(page)[:200])
    s, found, _ = call("GET", "/api/content?q=midnight", user)
    check("search works", s == 200 and any("Midnight" in i["title"] for i in found["items"]), str(found)[:200])

    # ---- admin content lifecycle with real uploads
    meta = {"title": "Smoke Test Feature", "description": "Created by the e2e smoke test", "genre": "Drama", "language": "English", "release_year": 2024, "duration_minutes": 90, "category": "movie"}
    s, created, _ = call("POST", "/api/content", admin, meta)
    check("admin creates content", s == 201, str(created))
    cid = created["id"]
    poster = (SAMPLE / "poster_1.jpg").read_bytes()
    body, ct = multipart("poster.jpg", poster, "image/jpeg")
    check("admin uploads poster", call("POST", f"/api/videos/media/{cid}/poster", admin, raw=body, ctype=ct)[0] == 201)
    video = (SAMPLE / "sample.mp4").read_bytes()
    body, ct = multipart("movie.mp4", video, "video/mp4")
    s, asset, _ = call("POST", f"/api/videos/media/{cid}/video", admin, raw=body, ctype=ct)
    check("admin uploads video", s == 201 and asset["size_bytes"] == len(video), str(asset))
    s, _b, _ = call("POST", f"/api/videos/media/{cid}/video", user, raw=body, ctype=ct)
    check("viewer cannot upload", s == 403)
    bad_body, bad_ct = multipart("evil.mp4", b"MZ this is not a video", "video/mp4")
    s, bad, _ = call("POST", f"/api/videos/media/{cid}/video", admin, raw=bad_body, ctype=bad_ct)
    check("non-video upload rejected (magic-byte check)", s == 415, str(s))
    s, patched, _ = call("PATCH", f"/api/content/{cid}", admin, {"title": "Smoke Test Feature (edited)"})
    check("admin edits content", s == 200 and "edited" in patched["title"])

    # ---- viewer playback
    s, img, hdr = call("GET", f"/api/videos/media/{cid}/poster")
    check("poster is publicly viewable", s == 200 and img == poster)
    s, tok, _ = call("POST", f"/api/videos/stream-token/{cid}", user)
    check("stream token issued", s == 200 and tok["token"], str(tok))
    url = f"/api/videos/media/{cid}/video?stream_token={tok['token']}"
    s, chunk, hdr = call("GET", url, headers={"Range": "bytes=0-99"})
    check("HTTP Range request returns 206 + Content-Range", s == 206 and len(chunk) == 100 and hdr["Content-Range"].startswith("bytes 0-99/"), f"{s} {hdr.get('Content-Range')}")
    s, whole, _ = call("GET", url)
    check("full video download matches upload", s == 200 and whole == video)
    check("video without token rejected", call("GET", f"/api/videos/media/{cid}/video")[0] == 401)

    # ---- watchlist / history / profile
    check("add to watchlist", call("POST", "/api/watchlist", user, {"content_id": cid})[0] in (200, 201))
    s, ids, _ = call("GET", "/api/watchlist/ids", user)
    check("watchlist contains title", s == 200 and cid in ids)
    check("remove from watchlist", call("DELETE", f"/api/watchlist/{cid}", user)[0] == 204)
    s, h, _ = call("PUT", f"/api/history/{cid}", user, {"position_seconds": 42.5, "duration_seconds": 720})
    check("save watch progress", s == 200 and h["position_seconds"] == 42.5, str(h))
    s, h, _ = call("GET", f"/api/history/{cid}", user)
    check("resume position retrievable", s == 200 and h["position_seconds"] == 42.5)
    s, hist, _ = call("GET", "/api/history", user)
    check("watch history lists title", s == 200 and hist["total"] == 1)
    s, prof, _ = call("PUT", "/api/users/me", user, {"display_name": "Smoke Viewer", "preferred_language": "Hindi", "avatar_color": "#ff5500"})
    check("profile update", s == 200 and prof["display_name"] == "Smoke Viewer", str(prof))

    # ---- admin management
    s, stats, _ = call("GET", "/api/content/admin/stats", admin)
    check("content statistics", s == 200 and stats["total"] >= 1)
    s, ustats, _ = call("GET", "/api/auth/admin/stats", admin)
    check("user statistics", s == 200 and ustats["total_users"] >= 2)
    check("viewer blocked from admin APIs", call("GET", "/api/auth/admin/users", user)[0] == 403)
    s, users, _ = call("GET", f"/api/auth/admin/users?q={uname}", admin)
    check("admin lists users", s == 200 and users["total"] == 1)
    uid = users["items"][0]["id"]
    s, up, _ = call("PATCH", f"/api/auth/admin/users/{uid}", admin, {"role": "admin"})
    check("admin changes a role", s == 200 and up["role"] == "admin")
    check("admin removes the test user", call("DELETE", f"/api/auth/admin/users/{uid}", admin)[0] == 204)

    # ---- refresh + cleanup
    s, rotated, _ = call("POST", "/api/auth/refresh", body={"refresh_token": tokens["refresh_token"]})
    check("refresh token rotation", s == 200 and rotated["refresh_token"] != tokens["refresh_token"])
    check("old refresh token rejected", call("POST", "/api/auth/refresh", body={"refresh_token": tokens["refresh_token"]})[0] == 401)
    check("admin deletes content", call("DELETE", f"/api/content/{cid}", admin)[0] == 204)
    time.sleep(0.5)
    s, assets, _ = call("GET", f"/api/videos/media/{cid}", admin)
    check("media removed with content", s == 200 and assets == {}, str(assets))

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
