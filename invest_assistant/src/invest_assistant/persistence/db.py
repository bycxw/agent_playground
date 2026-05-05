"""SQLAlchemy engine + session helpers."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from .models import Base


_engine = create_engine(settings.DATABASE_URL, future=True)
_SessionMaker = sessionmaker(bind=_engine, expire_on_commit=False)


def init_db() -> None:
    """Create tables if they don't exist."""
    Base.metadata.create_all(_engine)


@contextmanager
def session() -> Iterator[Session]:
    """Transactional scope. Commits on success, rolls back on error."""
    s = _SessionMaker()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
