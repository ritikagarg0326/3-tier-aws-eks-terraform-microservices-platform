from datetime import datetime

from hotstar_common.db import Base, utcnow
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(30), nullable=False, default="English")
    avatar_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#1f80e0")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
