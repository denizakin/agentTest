from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Optional

from taskqueue.types import Job, JobQueue


class InMemoryQueue(JobQueue):
    """
    A simple thread-safe in-memory queue placeholder.

    Swap with Redis/RQ or Celery when ready.
    """

    def __init__(self) -> None:
        self._queue: Deque[Job] = deque()
        self._lock = threading.Lock()

    def enqueue(self, job: Job) -> str:
        with self._lock:
            self._queue.append(job)
            return job.id

    def dequeue(self) -> Optional[Job]:
        with self._lock:
            return self._queue.popleft() if self._queue else None

