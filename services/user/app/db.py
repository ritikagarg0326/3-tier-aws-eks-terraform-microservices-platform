from hotstar_common.db import create_db_engine, db_dependency, session_factory

from .config import get_settings

engine = create_db_engine(get_settings().database_url)
SessionLocal = session_factory(engine)
get_db = db_dependency(SessionLocal)
