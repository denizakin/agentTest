"""Database connection helper using SQLAlchemy and Alembic.

Provides a lightweight wrapper to create engine and sessions, test
connectivity, and optionally read the Alembic revision if present.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from config import get_database_url


class DbConn:
    """Simple database connection manager.

    Usage:
        db = DbConn()
        ok = db.test_connection()
        with db.session_scope() as s:
            s.execute(text("SELECT 1"))
    """

    def __init__(self, db_url: Optional[str] = None, echo: bool = False) -> None:
        url = db_url or get_database_url()
        if not url:
            raise ValueError("Database URL not configured. Check resources/.env or DATABASE_URL.")

        # pool_pre_ping=True to avoid broken connections
        self._engine: Engine = create_engine(url, echo=echo, pool_pre_ping=True)
        self._Session = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

    @property
    def engine(self) -> Engine:
        return self._engine

    def get_session(self) -> Session:
        return self._Session()

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """Try connecting and executing a trivial statement."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False

    def get_alembic_revision(self) -> Optional[str]:
        """Return current Alembic revision if alembic_version table exists.

        Returns None when the table is missing or unreadable.
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                row = result.first()
                return row[0] if row else None
        except SQLAlchemyError:
            return None

