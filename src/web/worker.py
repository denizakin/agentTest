from __future__ import annotations

import threading
import time
from typing import Optional

from db.backtests_repo import BacktestsRepo
from db.db_conn import DbConn
from taskqueue.types import JobQueue
from web.deps import get_job_queue


def _handle_backtest(queue: JobQueue, db: DbConn, stop_event: threading.Event) -> None:
    repo = BacktestsRepo()
    while not stop_event.is_set():
        job = queue.dequeue()
        if not job:
            time.sleep(1.0)
            continue

        payload = job.payload or {}
        run_id = payload.get("run_id")
        with db.session_scope() as session:
            try:
                if run_id:
                    repo.update_status(session, run_id, status="running", progress=10)
                # TODO: hook in real backtest execution here
                time.sleep(0.5)
                if run_id:
                    repo.update_status(session, run_id, status="succeeded", progress=100)
            except Exception as exc:  # pragma: no cover - runtime safety
                session.rollback()
                if run_id:
                    repo.update_status(session, run_id, status="failed", progress=100, error=str(exc))


_worker_thread: Optional[threading.Thread] = None
_stop_event: Optional[threading.Event] = None


def start_background_worker(db: DbConn) -> None:
    """
    Start a simple background worker to consume in-memory queue and update run status.

    This is a dev-only placeholder. For production, replace with a real queue/worker.
    """
    global _worker_thread, _stop_event
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event = threading.Event()
    queue = get_job_queue()
    _worker_thread = threading.Thread(target=_handle_backtest, args=(queue, db, _stop_event), daemon=True)
    _worker_thread.start()


def stop_background_worker() -> None:
    global _worker_thread, _stop_event
    if _stop_event:
        _stop_event.set()
    if _worker_thread:
        _worker_thread.join(timeout=2.0)
