"""SQLAlchemy helpers: engine factory, declarative base, session dependency, connectivity probe."""
from collections.abc import Callable, Iterator
from datetime import datetime, timezone

from sqlalchemy import DateTime, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_db_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url.endswith("sqlite://"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, pool_size=10, max_overflow=10)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def db_dependency(factory: sessionmaker[Session]) -> Callable[[], Iterator[Session]]:
    def get_db() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    return get_db


def check_db(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


DateTimeCol = DateTime
