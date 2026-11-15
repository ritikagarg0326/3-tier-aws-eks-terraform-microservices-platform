from datetime import datetime

from hotstar_common.db import Base, utcnow
from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        UniqueConstraint("content_id", "kind", name="uq_media_content_kind"),
        CheckConstraint("kind IN ('video','poster','thumbnail')", name="ck_media_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    object_key: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
