"""Placeholder worker loop for backtest jobs."""
from __future__ import annotations

import time
from typing import Callable

from taskqueue.types import JobQueue


def run_worker(queue: JobQueue, handler: Callable[[dict], None], poll_seconds: float = 1.0) -> None:
    """
    Minimal worker loop.

    Args:
        queue: Queue implementation (will be Redis/RQ or Celery in future).
        handler: Function that handles a single job payload.
        poll_seconds: Delay between polls.
    """
    while True:  # pragma: no cover - placeholder loop
        job = queue.dequeue()
        if job:
            handler(job.payload)
        time.sleep(poll_seconds)

