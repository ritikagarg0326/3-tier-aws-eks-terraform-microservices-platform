import logging
import uuid
from email.utils import format_datetime

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from hotstar_common.errors import AppError, ForbiddenError, NotFoundError, UnauthorizedError
from hotstar_common.security import CurrentUser, create_token, decode_token, get_current_user, require_admin, user_from_request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import MediaAsset
from .ranges import parse_range
from .schemas import AssetOut, Kind, StreamToken
from .sniff import IMAGE_TYPES, VIDEO_TYPES, sniff
from .storage import ObjectNotFound, Storage, get_storage

log = logging.getLogger("video")
router = APIRouter(prefix="/videos", tags=["media"])


def _asset(db: Session, content_id: int, kind: str) -> MediaAsset | None:
    return db.scalar(select(MediaAsset).where(MediaAsset.content_id == content_id, MediaAsset.kind == kind))


@router.post("/media/{content_id}/{kind}", response_model=AssetOut, status_code=201, summary="Upload / replace a video, poster or thumbnail (admin)")
def upload(
    content_id: int,
    kind: Kind,
    file: UploadFile = File(...),
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    s = get_settings()
    detected = sniff(file.file)
    allowed = VIDEO_TYPES if kind == "video" else IMAGE_TYPES
    if detected is None or detected[0] not in allowed:
        raise AppError(f"Unsupported file for {kind}. Allowed: {', '.join(sorted(allowed))}", status_code=415, code="unsupported_media_type")
    content_type, ext = detected
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    limit = (s.max_video_mb if kind == "video" else s.max_image_mb) * 1024 * 1024
    if size == 0 or size > limit:
        raise AppError(f"File must be between 1 byte and {limit // (1024 * 1024)} MB", status_code=413, code="file_too_large")

    key = f"content/{content_id}/{kind}/{uuid.uuid4().hex}{ext}"
    storage.put(key, file.file, content_type)
    existing = _asset(db, content_id, kind)
    old_key = existing.object_key if existing else None
    if existing:
        existing.object_key, existing.content_type, existing.size_bytes = key, content_type, size
        existing.original_filename, existing.uploaded_by = (file.filename or "")[:255] or None, admin.id
        asset = existing
    else:
        asset = MediaAsset(content_id=content_id, kind=kind, object_key=key, content_type=content_type, size_bytes=size, original_filename=(file.filename or "")[:255] or None, uploaded_by=admin.id)
        db.add(asset)
    db.commit()
    db.refresh(asset)
    if old_key:
        storage.delete(old_key)
    log.info("media uploaded", extra={"content_id": content_id, "kind": kind, "size": size})
    return asset


@router.get("/media/{content_id}", response_model=dict[str, AssetOut], summary="Which media exists for a title", dependencies=[Depends(get_current_user)])
def list_assets(content_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(MediaAsset).where(MediaAsset.content_id == content_id)).all()
    return {r.kind: AssetOut.model_validate(r) for r in rows}


@router.post("/stream-token/{content_id}", response_model=StreamToken, summary="Short-lived token for <video src> playback (browsers cannot send auth headers)")
def stream_token(content_id: int, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _asset(db, content_id, "video"):
        raise NotFoundError("No video has been uploaded for this title")
    ttl = get_settings().stream_token_ttl_seconds
    return StreamToken(token=create_token({"sub": str(cu.id), "cid": content_id}, "stream", ttl), expires_in=ttl)


def _authorize_stream(request: Request, content_id: int, stream_token: str | None) -> None:
    if request.headers.get("authorization"):
        user_from_request(request)
        return
    if not stream_token:
        raise UnauthorizedError("Authentication required to stream video", code="missing_token")
    if decode_token(stream_token, "stream").get("cid") != content_id:
        raise ForbiddenError("Stream token is not valid for this title")


@router.api_route("/media/{content_id}/{kind}", methods=["GET", "HEAD"], summary="Download/stream media with HTTP Range support (posters are public)")
def serve(
    request: Request,
    content_id: int,
    kind: Kind,
    stream_token: str | None = Query(None),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    if kind == "video":
        _authorize_stream(request, content_id, stream_token)
    asset = _asset(db, content_id, kind)
    if not asset:
        raise NotFoundError(f"No {kind} for this title")

    etag = f'"{asset.id}-{int(asset.updated_at.timestamp())}"'
    common = {"Accept-Ranges": "bytes", "ETag": etag, "Last-Modified": format_datetime(asset.updated_at, usegmt=True) if asset.updated_at.tzinfo else asset.updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT")}
    common["Cache-Control"] = "public, max-age=3600" if kind != "video" else "private, max-age=3600"
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=common)

    try:
        size = storage.size(asset.object_key)
    except ObjectNotFound:
        raise NotFoundError("Stored object is missing")
    rng = parse_range(request.headers.get("range"), size) if kind == "video" or request.headers.get("range") else None
    start, end = rng if rng else (0, size - 1)
    headers = {**common, "Content-Length": str(end - start + 1)}
    status = 200
    if rng:
        status = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    if request.method == "HEAD":
        return Response(status_code=status, headers={**headers, "Content-Type": asset.content_type})
    return StreamingResponse(storage.read_range(asset.object_key, start, end), status_code=status, media_type=asset.content_type, headers=headers)


@router.delete("/media/{content_id}/{kind}", status_code=204, summary="Delete one media asset (admin)", dependencies=[Depends(require_admin)])
def delete_one(content_id: int, kind: Kind, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    asset = _asset(db, content_id, kind)
    if not asset:
        raise NotFoundError("Media not found")
    key = asset.object_key
    db.delete(asset)
    db.commit()
    storage.delete(key)
    return Response(status_code=204)


@router.delete("/media/{content_id}", status_code=204, summary="Delete all media of a title (admin)", dependencies=[Depends(require_admin)])
def delete_all(content_id: int, db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    rows = db.scalars(select(MediaAsset).where(MediaAsset.content_id == content_id)).all()
    keys = [r.object_key for r in rows]
    for r in rows:
        db.delete(r)
    db.commit()
    for k in keys:
        storage.delete(k)
    return Response(status_code=204)
