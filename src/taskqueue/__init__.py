"""Lightweight queue abstractions and stubs for future workers."""

from taskqueue.memory import InMemoryQueue
from taskqueue.types import Job, JobQueue

__all__ = ["InMemoryQueue", "Job", "JobQueue"]

