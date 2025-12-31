"""Shared FastAPI dependencies (DB sessions, job queue, etc.)."""
from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from config import load_env_file
from db.db_conn import DbConn
from taskqueue.memory import InMemoryQueue
from taskqueue.types import JobQueue

# Load environment variables so DbConn can read DB settings.
load_env_file()

_db_conn: Optional[DbConn] = None
_job_queue: JobQueue = InMemoryQueue()


def get_db() -> Generator[Session, None, None]:
    """Provide a SQLAlchemy session per-request (lazy init)."""
    global _db_conn

    if _db_conn is None:
        try:
            _db_conn = DbConn()
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    session = _db_conn.get_session()
    try:
        yield session
    finally:
        session.close()


def get_job_queue(_: Session = Depends(get_db)) -> JobQueue:  # pragma: no cover - simple dependency
    """
    Provide a job queue handle. Currently in-memory; swap for Redis/RQ or Celery later.

    The DB dependency ensures the queue can later record jobs/status in the DB.
    """
    return _job_queue
