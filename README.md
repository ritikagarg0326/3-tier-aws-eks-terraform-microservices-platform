# hotstar – OTT streaming platform

A Disney+ Hotstar-inspired video platform: **Angular** SPA, **FastAPI** API gateway + six independently deployable microservices, **MySQL** (one database per service, Alembic migrations) and **MinIO** (S3-compatible video/image storage with HTTP Range playback), all started locally with **Docker Compose**.

```
Browser ─▶ nginx (Angular, :8080) ─▶ API Gateway (:8000) ─▶ auth · user · content · video · watchlist · history
                                                              │                    │
                                                           MySQL (6 DBs)       MinIO (S3)
```

## Features

**Viewers** – registration & JWT login (rotating refresh tokens) · browse movies / TV shows / web series · search + filter by genre, language, category · sort · details page · integrated video player with seeking (HTTP Range), speed and ±10 s controls · **resume from last position** · watchlist add/remove · watch history & "continue watching" · profile (display name, bio, language, avatar colour) and password change · responsive dark OTT UI.

**Admins** – secure admin login · dashboard with content and user statistics · create/edit/delete titles (title, description, genre, language, release year, duration, category, rating, featured) · upload/replace/remove **poster, thumbnail and video** with progress bars · manage users (change role, disable/enable, delete).

## Quick start (Windows)

Prerequisites: **Docker Desktop** (WSL 2 backend), ~8 GB free RAM, ~5 GB disk, free ports 8080 and 8000 (plus 8001-8006, 3307, 9001 from the override file).

```powershell
Expand-Archive Hotstar-OTT-Platform.zip -DestinationPath .
cd hotstar

# 1. create .env with freshly generated random secrets
.\scripts\init-env.ps1

# 2. build and start everything (first run: ~5-10 min of image builds)
docker compose up --build -d

# 3. wait until every container is "healthy"
docker compose ps
```

macOS/Linux: `./scripts/init-env.sh` instead of the PowerShell script; the compose commands are identical.

| What | URL |
|---|---|
| **The app** | http://localhost:8080 |
| API gateway + Swagger UI (all services) | http://localhost:8000/docs |
| Gateway readiness (all services) | http://localhost:8000/ready |
| Per-service Swagger (debug override) | http://localhost:8001/docs … :8006/docs |
| MinIO console | http://localhost:9001 (user `hotstar-minio`, password = `MINIO_ROOT_PASSWORD` in `.env`) |
| MySQL (debug override) | `127.0.0.1:3307`, e.g. user `auth_svc` / `AUTH_DB_PASSWORD`, db `auth_db` |

### Sample accounts (created by the seed, from `.env`)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@hotstar-demo.com` | `Admin@12345` |
| Viewer | `demo@hotstar-demo.com` | `Demo@12345` |

These come from `ADMIN_*` / `DEMO_USER_*` in `.env.example` and are for local practice only – change them, or set `SEED_DATA=false`, before sharing the stack. The seed also inserts 12 sample titles with generated posters and a short sample video (a test pattern, so you can try playback and resume immediately).

### Try it

1. Sign in as the viewer → open any title → **Watch now**, seek around, pause, leave the page, come back → **Resume**. Add titles to the **Watchlist**; see **History** under the avatar menu.
2. Sign in as the admin → avatar menu → **Admin dashboard** → *Content* → **Add content**, choose a poster/thumbnail/video (MP4 or WebM), save. Watch the upload progress; the title appears on the home page.
3. Admin → *Users* to change a role or disable an account.

### Stop / reset

```powershell
docker compose down          # stop, keep data (volumes mysql_data, minio_data)
docker compose down -v       # stop and DELETE all data (needed after changing DB/MinIO passwords in .env)
docker compose logs -f gateway content-service    # JSON logs, request id in every line
```

## Tests

Backend – 70 automated tests (unit + API integration) across the seven services, plus migration tests (`alembic upgrade head`) and seed tests. They use SQLite and a local storage backend, so no Docker is needed (Python 3.11+):

```powershell
.\scripts\run-tests.ps1          # or ./scripts/run-tests.sh
```

End-to-end smoke test (36 checks through the gateway: login, registration, RBAC, upload, Range playback, watchlist, history, profile, admin, token rotation, cleanup) – run it against the running stack:

```powershell
$env:ADMIN_PASSWORD = "Admin@12345"
python scripts/e2e_smoke.py http://localhost:8000
```

## Repository layout

```
hotstar/
├── docker-compose.yml            full stack (frontend, gateway, 6 services, MySQL, MinIO, volumes, networks, healthchecks)
├── docker-compose.override.yml   local-only: publishes service/MySQL/MinIO-console ports on 127.0.0.1
├── .env.example                  every setting, with placeholders (copy via scripts/init-env.*)
├── frontend/                     Angular 18 + Angular Material app, nginx.conf.template, Dockerfile
├── services/
│   ├── gateway/  auth/  user/  content/  video/  watchlist/  history/
│   │   ├── app/ (main.py, config.py, models.py, schemas.py, routes.py, seed.py …)
│   │   ├── alembic/ (migrations)   tests/   Dockerfile   entrypoint.sh   requirements.txt   .env.example
├── libs/common/                  shared logging, error handling, JWT security, health, DB helpers
├── docker/mysql/                 MySQL image + init script (one schema and account per service)
├── scripts/                      init-env, run-tests, e2e_smoke.py, gen_api_docs.py
└── docs/                         ARCHITECTURE.md, API.md
```

## Configuration

Everything is environment-driven (see `.env.example` and each service's `.env.example`). Key settings: `JWT_SECRET` (≥ 32 chars, shared by all services), `ACCESS_TOKEN_TTL_MINUTES`, `REFRESH_TOKEN_TTL_DAYS`, `*_DB_PASSWORD`, `MINIO_ROOT_USER/PASSWORD`, `S3_BUCKET`, `MAX_VIDEO_MB`, `SEED_DATA`. Storage: `STORAGE_BACKEND=s3` with `S3_ENDPOINT_URL=http://minio:9000` for MinIO; leave `S3_ENDPOINT_URL` empty to target AWS S3 (credentials from the IAM role) – no code changes.

## Documentation

* [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) – tiers, service ownership, security model, storage abstraction, request flows.
* [`docs/API.md`](docs/API.md) – endpoint tables for every service (generated from the live OpenAPI schemas); live Swagger at `/docs`.

## Troubleshooting

* **A container is unhealthy / the first start is slow** – MySQL initialisation takes up to a minute on the first run; services wait for it. `docker compose logs mysql auth-service`.
* **"set JWT_SECRET in .env"** – you skipped `scripts/init-env`.
* **Access denied for user 'auth_svc'** – you changed passwords after the first start; MySQL only creates accounts on an empty volume → `docker compose down -v`, then `up --build` again.
* **Port already in use** – stop whatever uses 8080/8000, or edit the `ports:` mappings; delete `docker-compose.override.yml` to stop publishing 8001-8006/3307/9001.
* **Video does not play** – browsers play MP4 (H.264/AAC) and WebM; HEVC/MKV files will upload but not play. Re-encode: `ffmpeg -i in.mov -c:v libx264 -c:a aac -movflags +faststart out.mp4`.
* **Upload fails with 413** – limits are `MAX_VIDEO_MB` (default 2048) and `MAX_IMAGE_MB` (10).
* **`exec ... entrypoint.sh: no such file` on Windows** – CRLF line endings; the Dockerfiles strip them, but make sure Git does not rewrite the Dockerfiles (`.gitattributes` is included).



