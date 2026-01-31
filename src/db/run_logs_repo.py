from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.poco.run_log import RunLog


class RunLogsRepo:
    """Append-only log storage per run."""

    def append(self, session: Session, run_id: int, level: str, message: str, ts: Optional[datetime] = None) -> None:
        # Try to extract timestamp from message if not provided
        if ts is None:
            # Pattern to match ISO timestamp at start of message: "2025-03-31T19:00:00 - ..."
            ts_match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)", message)
            if ts_match:
                try:
                    # Parse timestamp from message (naive, assume Istanbul timezone)
                    from zoneinfo import ZoneInfo
                    istanbul_tz = ZoneInfo("Europe/Istanbul")
                    ts_naive = datetime.fromisoformat(ts_match.group(1))
                    ts = ts_naive.replace(tzinfo=istanbul_tz)
                    # DEBUG: print(f"[DEBUG] Parsed timestamp from message: {ts}")
                except Exception as e:
                    # If parsing fails, use current UTC time
                    # DEBUG: print(f"[DEBUG] Failed to parse timestamp: {e}")
                    ts = datetime.now(tz=timezone.utc)
            else:
                # No timestamp in message, use current UTC time
                # DEBUG: print(f"[DEBUG] No timestamp in message, using current time")
                ts = datetime.now(tz=timezone.utc)

        log = RunLog(run_id=run_id, level=level, message=message, ts=ts)
        session.add(log)

    def list_logs(self, session: Session, run_id: int, limit: int = 200, offset: int = 0) -> List[RunLog]:
        stmt = (
            select(RunLog)
            .where(RunLog.run_id == run_id)
            .order_by(RunLog.ts.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())
