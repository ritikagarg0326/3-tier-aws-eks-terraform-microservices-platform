# hotstar architecture

## Three tiers

```
 Presentation tier            Application tier                                   Data tier
┌───────────────────┐   ┌──────────────────────────────────────────────┐   ┌───────────────────────┐
│ Angular SPA       │   │  API Gateway (FastAPI, :8000)                │   │ MySQL 8.4             │
│ served by nginx   │──▶│   - edge JWT check, rate-limit, CORS         │   │  auth_db      (auth)  │
│ (:8080)           │   │   - streaming reverse proxy (uploads, Range) │   │  user_db      (user)  │
│ /api/* → gateway  │   │        │                                     │   │  content_db   (content│
└───────────────────┘   │        ├─▶ auth-service      :8001 ───────────┼──▶│  video_db     (video) │
                        │        ├─▶ user-service      :8002 ───────────┼──▶│  watchlist_db         │
                        │        ├─▶ content-service   :8003 ───────────┼──▶│  history_db           │
                        │        ├─▶ video-service     :8004 ─────┐     │   └───────────────────────┘
                        │        ├─▶ watchlist-service :8005      │     │   ┌───────────────────────┐
                        │        └─▶ history-service   :8006      └─────┼──▶│ MinIO (S3 API)        │
                        └──────────────────────────────────────────────┘   │ bucket hotstar-media  │
                                                                           └───────────────────────┘
```

The browser only ever talks to nginx on one origin. nginx serves the static Angular build and forwards `/api/*` to the **API gateway**; the gateway is the only component that reaches the microservices. Services are never exposed to the browser (the optional `docker-compose.override.yml` publishes them on `127.0.0.1` for debugging only).

Docker networks: `edge` (frontend, gateway), `backend` (gateway, services), `data` (services, MySQL, MinIO).

## Services

| Service | Port | Owns (database) | Responsibility |
|---|---|---|---|
| api-gateway | 8000 | – | Routing `/api/<svc>/…`, edge authentication, login rate limiting, streamed request/response bodies (uploads, `Range`), aggregated readiness, Swagger UI with all services |
| auth-service | 8001 | `auth_db`: users, refresh_tokens | Registration, login, JWT access + rotating refresh tokens, roles, admin user management |
| user-service | 8002 | `user_db`: user_profiles | Viewer profile (display name, bio, language, avatar colour); created lazily on first access |
| content-service | 8003 | `content_db`: contents | Catalogue metadata, search/filter/sort/paginate, facets, admin CRUD and statistics |
| video-service | 8004 | `video_db`: media_assets + object storage | Upload of video/poster/thumbnail, content sniffing, HTTP Range streaming, short-lived stream tokens |
| watchlist-service | 8005 | `watchlist_db`: watchlist_items | Per-user watchlist (unique user+content) |
| history-service | 8006 | `history_db`: watch_history | Per-user progress / resume position, "continue watching" |

**Database ownership.** Each service has its own schema, its own MySQL account (`auth_svc`, `content_svc`, …) with privileges only on that schema, and its own Alembic migration history (`services/<svc>/alembic`). There are no cross-service foreign keys or joins; services reference each other only by id (`content_id`, `user_id`). One MySQL server hosts the six schemas to keep the local stack light; moving a schema to its own server (or RDS instance) only changes `DATABASE_URL`.

**Shared library.** `libs/common/hotstar_common` provides what must be identical everywhere (JSON logging + request ids, error envelope, JWT validation, health router, DB helpers). It is installed into every image; services share no other code.

## Security model

* Passwords: bcrypt (cost 12), 8–72 bytes, must contain a letter and a digit; login does a constant-time comparison even for unknown emails.
* Tokens: HS256 JWT. Access token 30 min (claims: `sub`, `email`, `username`, `role`, `type=access`). Refresh token 7 days, stored server-side by `jti`, **rotated on every use**; re-use of a rotated token revokes the whole family. Password change, account disabling and logout revoke tokens.
* Defence in depth: the gateway rejects unauthenticated calls at the edge, **and every service validates the JWT itself** with the shared secret and enforces roles (`require_admin`). Reaching a service directly does not bypass authorization.
* Video playback: `<video>` cannot send an `Authorization` header, so the client asks `POST /videos/stream-token/{id}` (authenticated) for a 4-hour token scoped to one title (`type=stream`, `cid=<id>`) and passes it as `?stream_token=`. Access tokens are not accepted in the URL. Posters/thumbnails are public (needed by `<img>`).
* Uploads: type is determined from magic bytes (MP4/WebM, JPEG/PNG/WebP), never from the client's `Content-Type`/extension; size limits are enforced; object keys are generated server-side (UUID), so file names cannot traverse paths.
* Secrets come only from environment variables (`.env`, never committed). `docker compose` refuses to start if required secrets are missing. Containers run as non-root with `no-new-privileges` and all capabilities dropped.
* nginx adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and a strict Content-Security-Policy.
* Trade-off: the SPA keeps tokens in `localStorage` (simple, survives reloads, but readable by injected JS). The CSP and Angular's template escaping mitigate XSS; an httpOnly-cookie session is the hardened alternative if the app is served from one site.

## Storage abstraction

`services/video/app/storage.py` defines `Storage` (`put`, `size`, `read_range`, `delete`, `ping`, `ensure_ready`) with two implementations:

* `S3Storage` – boto3. With `S3_ENDPOINT_URL=http://minio:9000` it talks to MinIO (path-style addressing). With an empty endpoint it talks to **AWS S3** and uses the default credential chain (so an IAM role / IRSA works without keys). No code change is needed to move from MinIO to S3.
* `LocalStorage` – filesystem, used by unit tests and no-Docker development (`STORAGE_BACKEND=local`).

Range playback: the video service parses `Range` (RFC 7233: `a-b`, `a-`, `-n`), answers `206` + `Content-Range`/`Accept-Ranges`, or `416`, and streams only the requested bytes from the object store (S3 `GetObject` with `Range`). The gateway and nginx pass `Range` through unbuffered, so seeking works in the browser.

## Request flows

**Login** – SPA → `POST /api/auth/login` → gateway (rate-limited, public route) → auth-service → bcrypt verify → access+refresh token pair → SPA stores it; the HTTP interceptor adds `Authorization` to later calls and on a 401 performs one shared refresh and retries.

**Upload** – Admin form → `POST /api/content` (content-service) → `POST /api/videos/media/{id}/{poster|thumbnail|video}` as multipart, streamed through nginx and the gateway → video-service sniffs the bytes, writes to MinIO, upserts `media_assets`, deletes the replaced object.

**Playback + resume** – watch page → `GET /api/history/{id}` (resume point) + `POST /api/videos/stream-token/{id}` → `<video src=…?stream_token=…>`; the browser issues `Range` requests; progress is saved every 10 s, on pause/end and on page hide via `PUT /api/history/{id}`; ≥95 % marks the title completed.

**Delete content** – content-service deletes the row and then calls `DELETE /videos/media/{id}` on video-service with the admin's own token (best-effort, logged). Watchlist/history rows of deleted titles are ignored by the UI because titles are resolved through content-service.

## Operational characteristics (EKS-friendly, nothing cloud-specific yet)

* Stateless services configured only by environment variables; `/health` (liveness) and `/ready` (readiness) on every service; JSON logs on stdout with a request id propagated by the gateway (`X-Request-ID`).
* Images are multi-stage, run as UID 10001, expose one port, and have a `HEALTHCHECK`.
* Alembic migrations run at container start (`entrypoint.sh`). With several replicas of one service, move that step to a one-shot Job/init container.
* The login rate limiter is in-memory per gateway replica; use an ingress/WAF limit or Redis when scaling out.
* Not included by design (next phase): Terraform, EKS manifests/Helm, CI/CD, Prometheus/Grafana, CloudWatch/ELK.
