# hotstar API reference

All calls go through the **API gateway** (`http://localhost:8000` or `/api` on the web origin). Paths below are shown as the browser calls them (`/api/...`).
Interactive Swagger UI: **http://localhost:8000/docs** (pick a service in the top-right selector, click *Authorize*, paste an access token). Each service also serves its own `/docs` on ports 8001-8006 in local mode.

Errors always use one envelope: `{"error": {"code": "...", "message": "...", "details": [...], "request_id": "..."}}`.
Auth: `Authorization: Bearer <access_token>`. **Public**: register/login/refresh/logout, poster & thumbnail images. Video playback accepts `?stream_token=` (from `POST /api/videos/stream-token/{id}`) because `<video>` elements cannot send headers.
Roles: `user` (viewer) and `admin`. *Admin* endpoints return 403 for viewers.

## Auth Service

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/api/auth/register` | public | Register a new viewer account |
| POST | `/api/auth/login` | public | Login with email and password |
| POST | `/api/auth/refresh` | public | Rotate refresh token and get a new access token |
| POST | `/api/auth/logout` | public | Revoke a refresh token |
| GET | `/api/auth/me` | authenticated | Current account |
| POST | `/api/auth/change-password` | authenticated | Change password (revokes all sessions) |
| GET | `/api/auth/admin/users` | admin | List users |
| PATCH | `/api/auth/admin/users/{user_id}` | admin | Change a user's role or active flag |
| DELETE | `/api/auth/admin/users/{user_id}` | admin | Delete a user |
| GET | `/api/auth/admin/stats` | admin | User statistics |

## User Service

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/api/users/me` | authenticated | Get my profile (created on first access) |
| PUT | `/api/users/me` | authenticated | Update my profile |
| DELETE | `/api/users/me` | authenticated | Delete my profile data |

## Content Service

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/api/content` | authenticated | Browse / search / filter content |
| POST | `/api/content` | admin | Create content (admin) |
| GET | `/api/content/facets` | authenticated | Distinct filter values |
| GET | `/api/content/admin/stats` | admin | Content management statistics |
| GET | `/api/content/{content_id}` | authenticated | Content details |
| PUT | `/api/content/{content_id}` | admin | Replace content metadata (admin) |
| PATCH | `/api/content/{content_id}` | admin | Partially update content metadata (admin) |
| DELETE | `/api/content/{content_id}` | admin | Delete content and its stored media (admin) |

## Video Service

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/api/videos/media/{content_id}/{kind}` | admin | Upload / replace a video, poster or thumbnail (admin) |
| GET | `/api/videos/media/{content_id}/{kind}` | images public, video needs stream token | Download/stream media with HTTP Range support (posters are public) |
| HEAD | `/api/videos/media/{content_id}/{kind}` | images public, video needs stream token | Download/stream media with HTTP Range support (posters are public) |
| DELETE | `/api/videos/media/{content_id}/{kind}` | admin | Delete one media asset (admin) |
| GET | `/api/videos/media/{content_id}` | authenticated | Which media exists for a title |
| DELETE | `/api/videos/media/{content_id}` | admin | Delete all media of a title (admin) |
| POST | `/api/videos/stream-token/{content_id}` | authenticated | Short-lived token for <video src> playback (browsers cannot send auth headers) |

## Watchlist Service

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/api/watchlist` | authenticated | My watchlist, newest first |
| POST | `/api/watchlist` | authenticated | Add to watchlist (idempotent) |
| GET | `/api/watchlist/ids` | authenticated | All content ids on my watchlist |
| GET | `/api/watchlist/{content_id}` | authenticated | Is this content on my watchlist? |
| DELETE | `/api/watchlist/{content_id}` | authenticated | Remove from watchlist (idempotent) |

## Watch History Service

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/api/history` | authenticated | My watch history, most recent first |
| DELETE | `/api/history` | authenticated | Clear my whole history |
| GET | `/api/history/{content_id}` | authenticated | Resume position for one title |
| PUT | `/api/history/{content_id}` | authenticated | Save playback progress (upsert) |
| DELETE | `/api/history/{content_id}` | authenticated | Remove one title from history |

## Health endpoints

Every service exposes `GET /health` (liveness) and `GET /ready` (readiness: database and, for the video service, object storage). The gateway's `GET /ready` reports the reachability of all six services.

