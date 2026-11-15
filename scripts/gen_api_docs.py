#!/usr/bin/env python3
"""Regenerates docs/API.md from each service's live OpenAPI schema (no Docker needed)."""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = [("auth", "/api/auth", "Auth Service"), ("users", "/api/users", "User Service"), ("content", "/api/content", "Content Service"),
            ("videos", "/api/videos", "Video Service"), ("watchlist", "/api/watchlist", "Watchlist Service"), ("history", "/api/history", "Watch History Service")]
DIRS = {"auth": "auth", "users": "user", "content": "content", "videos": "video", "watchlist": "watchlist", "history": "history"}
ENV = {**os.environ, "DATABASE_URL": "sqlite://", "JWT_SECRET": "x" * 40, "STORAGE_BACKEND": "local"}
PUBLIC = {("POST", "/auth/register"), ("POST", "/auth/login"), ("POST", "/auth/refresh"), ("POST", "/auth/logout")}
MIXED = {("GET", "/videos/media/{content_id}/{kind}"), ("HEAD", "/videos/media/{content_id}/{kind}")}
CODE = "import json,sys;from app.main import app;print(json.dumps(app.openapi()))"

out = ["# hotstar API reference", "",
       "All calls go through the **API gateway** (`http://localhost:8000` or `/api` on the web origin). Paths below are shown as the browser calls them (`/api/...`).",
       "Interactive Swagger UI: **http://localhost:8000/docs** (pick a service in the top-right selector, click *Authorize*, paste an access token). Each service also serves its own `/docs` on ports 8001-8006 in local mode.", "",
       "Errors always use one envelope: `{\"error\": {\"code\": \"...\", \"message\": \"...\", \"details\": [...], \"request_id\": \"...\"}}`.",
       "Auth: `Authorization: Bearer <access_token>`. **Public**: register/login/refresh/logout, poster & thumbnail images. Video playback accepts `?stream_token=` (from `POST /api/videos/stream-token/{id}`) because `<video>` elements cannot send headers.",
       "Roles: `user` (viewer) and `admin`. *Admin* endpoints return 403 for viewers.", ""]
for key, prefix, title in SERVICES:
    res = subprocess.run([sys.executable, "-c", CODE], cwd=ROOT / "services" / DIRS[key], env=ENV, capture_output=True, text=True)
    if res.returncode:
        sys.exit(res.stderr)
    spec = json.loads(res.stdout.strip().splitlines()[-1])
    out += [f"## {title}", "", "| Method | Path | Access | Description |", "|---|---|---|---|"]
    for path, ops in spec["paths"].items():
        if path in ("/health", "/ready"):
            continue
        for method, op in ops.items():
            admin = "/admin" in path or "(admin)" in op.get("summary", "")
            access = "images public, video needs stream token" if (method.upper(), path) in MIXED else "public" if (method.upper(), path) in PUBLIC else ("admin" if admin else "authenticated")
            out.append(f"| {method.upper()} | `/api{path}` | {access} | {op.get('summary', '')} |")
    out.append("")
out += ["## Health endpoints", "", "Every service exposes `GET /health` (liveness) and `GET /ready` (readiness: database and, for the video service, object storage). The gateway's `GET /ready` reports the reachability of all six services.", ""]
(ROOT / "docs" / "API.md").write_text("\n".join(out) + "\n")
print("wrote docs/API.md")
