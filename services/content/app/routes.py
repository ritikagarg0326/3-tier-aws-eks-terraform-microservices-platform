from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request, Response
from hotstar_common.db import utcnow
from hotstar_common.errors import AppError, NotFoundError
from hotstar_common.pagination import make_page
from hotstar_common.security import CurrentUser, get_current_user, require_admin
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import media_client
from .db import get_db
from .models import Content
from .schemas import ContentIn, ContentOut, ContentPatch, ContentStats, Facets

router = APIRouter(prefix="/content", tags=["content"])
SORTS = {
    "newest": (Content.created_at.desc(), Content.id.desc()),
    "oldest": (Content.created_at.asc(), Content.id.asc()),
    "year": (Content.release_year.desc(), Content.id.desc()),
    "title": (Content.title.asc(),),
}


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", summary="Browse / search / filter content", dependencies=[Depends(get_current_user)])
def list_content(
    q: str | None = Query(None, max_length=100, description="Matches title or description"),
    genre: str | None = None,
    language: str | None = None,
    category: str | None = Query(None, pattern="^(movie|tv_show|web_series|other)$"),
    year: int | None = Query(None, ge=1888, le=2100),
    featured: bool | None = None,
    ids: str | None = Query(None, description="Comma separated content ids (max 100)"),
    sort: str = Query("newest", pattern="^(newest|oldest|year|title)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Content)
    if q:
        like = f"%{_escape_like(q.strip())}%"
        stmt = stmt.where(or_(Content.title.like(like, escape="\\"), Content.description.like(like, escape="\\")))
    if genre:
        stmt = stmt.where(Content.genre == genre)
    if language:
        stmt = stmt.where(Content.language == language)
    if category:
        stmt = stmt.where(Content.category == category)
    if year:
        stmt = stmt.where(Content.release_year == year)
    if featured is not None:
        stmt = stmt.where(Content.is_featured.is_(featured))
    if ids:
        try:
            id_list = [int(x) for x in ids.split(",") if x.strip()][:100]
        except ValueError:
            raise AppError("ids must be a comma separated list of integers", code="invalid_ids")
        stmt = stmt.where(Content.id.in_(id_list))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(*SORTS[sort]).offset((page - 1) * page_size).limit(page_size)).all()
    return make_page([ContentOut.model_validate(r) for r in rows], total, page, page_size)


@router.get("/facets", response_model=Facets, summary="Distinct filter values", dependencies=[Depends(get_current_user)])
def facets(db: Session = Depends(get_db)):
    distinct = lambda col: [r for r in db.scalars(select(col).distinct().order_by(col))]  # noqa: E731
    return Facets(genres=distinct(Content.genre), languages=distinct(Content.language), categories=distinct(Content.category), years=sorted(distinct(Content.release_year), reverse=True))


@router.get("/admin/stats", response_model=ContentStats, summary="Content management statistics", dependencies=[Depends(require_admin)])
def stats(db: Session = Depends(get_db)):
    def grouped(col):
        return {k: v for k, v in db.execute(select(col, func.count()).group_by(col).order_by(func.count().desc()))}

    week = utcnow() - timedelta(days=7)
    return ContentStats(
        total=db.scalar(select(func.count()).select_from(Content)) or 0,
        featured=db.scalar(select(func.count()).select_from(Content).where(Content.is_featured.is_(True))) or 0,
        added_last_7_days=db.scalar(select(func.count()).select_from(Content).where(Content.created_at >= week)) or 0,
        by_category=grouped(Content.category),
        by_genre=grouped(Content.genre),
        by_language=grouped(Content.language),
    )


@router.get("/{content_id}", response_model=ContentOut, summary="Content details", dependencies=[Depends(get_current_user)])
def get_content(content_id: int, db: Session = Depends(get_db)):
    row = db.get(Content, content_id)
    if not row:
        raise NotFoundError("Content not found")
    return row


@router.post("", response_model=ContentOut, status_code=201, summary="Create content (admin)")
def create_content(body: ContentIn, admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    row = Content(**body.model_dump(), created_by=admin.id)
    db.add(row)
    db.commit()
    return row


@router.put("/{content_id}", response_model=ContentOut, summary="Replace content metadata (admin)", dependencies=[Depends(require_admin)])
def replace_content(content_id: int, body: ContentIn, db: Session = Depends(get_db)):
    row = db.get(Content, content_id)
    if not row:
        raise NotFoundError("Content not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    return row


@router.patch("/{content_id}", response_model=ContentOut, summary="Partially update content metadata (admin)", dependencies=[Depends(require_admin)])
def patch_content(content_id: int, body: ContentPatch, db: Session = Depends(get_db)):
    row = db.get(Content, content_id)
    if not row:
        raise NotFoundError("Content not found")
    for k, v in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(row, k, v)
    db.commit()
    return row


@router.delete("/{content_id}", status_code=204, summary="Delete content and its stored media (admin)", dependencies=[Depends(require_admin)])
def delete_content(content_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(Content, content_id)
    if not row:
        raise NotFoundError("Content not found")
    db.delete(row)
    db.commit()
    media_client.delete_media(content_id, request.headers.get("authorization"))
    return Response(status_code=204)
