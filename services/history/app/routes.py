from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from hotstar_common.db import utcnow
from hotstar_common.errors import NotFoundError
from hotstar_common.pagination import make_page
from hotstar_common.security import CurrentUser, get_current_user
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import WatchHistory

router = APIRouter(prefix="/history", tags=["watch-history"])
COMPLETE_RATIO = 0.95


class ProgressIn(BaseModel):
    position_seconds: float = Field(ge=0, le=1_000_000)
    duration_seconds: float = Field(ge=0, le=1_000_000)


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    content_id: int
    position_seconds: float
    duration_seconds: float
    completed: bool
    last_watched_at: datetime


@router.get("", summary="My watch history, most recent first")
def list_history(
    in_progress: bool = Query(False, description="Only unfinished items (\"Continue watching\")"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    cu: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    base = select(WatchHistory).where(WatchHistory.user_id == cu.id)
    if in_progress:
        base = base.where(WatchHistory.completed.is_(False), WatchHistory.position_seconds > 5)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(WatchHistory.last_watched_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return make_page([HistoryOut.model_validate(r) for r in rows], total, page, page_size)


@router.get("/{content_id}", response_model=HistoryOut, summary="Resume position for one title")
def get_one(content_id: int, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(WatchHistory).where(WatchHistory.user_id == cu.id, WatchHistory.content_id == content_id))
    if not row:
        raise NotFoundError("No watch history for this title")
    return row


@router.put("/{content_id}", response_model=HistoryOut, summary="Save playback progress (upsert)")
def save_progress(content_id: int, body: ProgressIn, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(WatchHistory).where(WatchHistory.user_id == cu.id, WatchHistory.content_id == content_id))
    if row is None:
        row = WatchHistory(user_id=cu.id, content_id=content_id)
        db.add(row)
    pos = min(body.position_seconds, body.duration_seconds) if body.duration_seconds else body.position_seconds
    row.position_seconds, row.duration_seconds = pos, body.duration_seconds
    row.completed = bool(body.duration_seconds) and pos >= body.duration_seconds * COMPLETE_RATIO
    row.last_watched_at = utcnow()
    db.commit()
    return row


@router.delete("/{content_id}", status_code=204, summary="Remove one title from history")
def delete_one(content_id: int, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(WatchHistory).filter(WatchHistory.user_id == cu.id, WatchHistory.content_id == content_id).delete()
    db.commit()
    return Response(status_code=204)


@router.delete("", status_code=204, summary="Clear my whole history")
def clear(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(WatchHistory).filter(WatchHistory.user_id == cu.id).delete()
    db.commit()
    return Response(status_code=204)
