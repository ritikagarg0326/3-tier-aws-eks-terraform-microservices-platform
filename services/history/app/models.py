from datetime import datetime

from hotstar_common.db import Base, utcnow
from sqlalchemy import Boolean, DateTime, Float, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class WatchHistory(Base):
    __tablename__ = "watch_history"
    __table_args__ = (UniqueConstraint("user_id", "content_id", name="uq_history_user_content"), Index("ix_history_user_last", "user_id", "last_watched_at"))

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    content_id: Mapped[int] = mapped_column(nullable=False)
    position_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_watched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    last_watched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
