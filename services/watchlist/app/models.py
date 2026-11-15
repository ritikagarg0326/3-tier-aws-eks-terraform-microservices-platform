from datetime import datetime

from hotstar_common.db import Base, utcnow
from sqlalchemy import DateTime, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "content_id", name="uq_watchlist_user_content"), Index("ix_watchlist_user_added", "user_id", "added_at"))

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    content_id: Mapped[int] = mapped_column(nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
