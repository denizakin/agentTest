from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol
from uuid import uuid4


@dataclass
class Job:
    """Minimal job payload wrapper."""

    payload: Dict[str, Any]
    id: str = field(default_factory=lambda: f"job-{uuid4().hex[:8]}")


class JobQueue(Protocol):
    """Queue interface to enqueue/dequeue jobs."""

    def enqueue(self, job: Job) -> str:
        ...

    def dequeue(self) -> Optional[Job]:
        ...

