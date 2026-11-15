from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from hotstar_common.pagination import make_page
from hotstar_common.security import CurrentUser, get_current_user
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from .models import WatchlistItem

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class ItemIn(BaseModel):
    content_id: int = Field(gt=0)


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    content_id: int
    added_at: datetime


@router.get("", summary="My watchlist, newest first")
def list_items(page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=100), cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    base = select(WatchlistItem).where(WatchlistItem.user_id == cu.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(WatchlistItem.added_at.desc(), WatchlistItem.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return make_page([ItemOut.model_validate(r) for r in rows], total, page, page_size)


@router.get("/ids", response_model=list[int], summary="All content ids on my watchlist")
def ids(cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(WatchlistItem.content_id).where(WatchlistItem.user_id == cu.id)))


@router.get("/{content_id}", summary="Is this content on my watchlist?")
def status(content_id: int, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    found = db.scalar(select(WatchlistItem.id).where(WatchlistItem.user_id == cu.id, WatchlistItem.content_id == content_id))
    return {"content_id": content_id, "in_watchlist": found is not None}


@router.post("", response_model=ItemOut, summary="Add to watchlist (idempotent)")
def add(body: ItemIn, response: Response, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.scalar(select(WatchlistItem).where(WatchlistItem.user_id == cu.id, WatchlistItem.content_id == body.content_id))
    if existing:
        return existing
    item = WatchlistItem(user_id=cu.id, content_id=body.content_id)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:  # concurrent insert
        db.rollback()
        return db.scalar(select(WatchlistItem).where(WatchlistItem.user_id == cu.id, WatchlistItem.content_id == body.content_id))
    response.status_code = 201
    return item


@router.delete("/{content_id}", status_code=204, summary="Remove from watchlist (idempotent)")
def remove(content_id: int, cu: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(WatchlistItem).filter(WatchlistItem.user_id == cu.id, WatchlistItem.content_id == content_id).delete()
    db.commit()
    return Response(status_code=204)
