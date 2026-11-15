from datetime import datetime

from hotstar_common.db import Base, utcnow
from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

CATEGORIES = ("movie", "tv_show", "web_series", "other")


class Content(Base):
    __tablename__ = "contents"
    __table_args__ = (
        CheckConstraint("category IN ('movie','tv_show','web_series','other')", name="ck_contents_category"),
        CheckConstraint("duration_minutes > 0", name="ck_contents_duration"),
        Index("ix_contents_category_genre", "category", "genre"),
        Index("ix_contents_featured_created", "is_featured", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    genre: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    release_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    maturity_rating: Mapped[str] = mapped_column(String(10), nullable=False, default="U/A 13+")
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
