from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from typing import List, Optional

from config import load_env_file
from db.db_conn import DbConn
from sqlalchemy import text


POLL_SECONDS = float(os.getenv("MANAGER_POLL_SECONDS", "5.0"))
MIN_PROCS = int(os.getenv("MANAGER_MIN_PROCS", "1"))
MAX_PROCS = int(os.getenv("MANAGER_MAX_PROCS", "4"))
WORKER_CONCURRENCY = int(os.getenv("MANAGER_WORKER_CONCURRENCY", "1"))
WORKER_POLL_SECONDS = os.getenv("MANAGER_WORKER_POLL", "1.0")
PROC_CAPACITY = int(os.getenv("MANAGER_PROC_CAPACITY", str(WORKER_CONCURRENCY)))


def get_counts(db: DbConn) -> tuple[int, int]:
    with db.session_scope() as session:
        q = session.execute(
            text(
                "select "
                "sum(case when status='queued' then 1 else 0 end) as queued, "
                "sum(case when status='running' then 1 else 0 end) as running "
                "from run_headers where run_type='backtest'"
            )
        )
        row = q.first()
        queued = int(row[0] or 0)
        running = int(row[1] or 0)
    return queued, running


def spawn_worker() -> subprocess.Popen:
    env = os.environ.copy()
    env["WORKER_CONCURRENCY"] = str(WORKER_CONCURRENCY)
    env["WORKER_POLL_SECONDS"] = str(WORKER_POLL_SECONDS)
    cmd = [sys.executable, "worker_main.py"]
    return subprocess.Popen(cmd, env=env)


def prune_workers(workers: List[subprocess.Popen]) -> List[subprocess.Popen]:
    alive = []
    for p in workers:
        if p.poll() is None:
            alive.append(p)
    return alive


def main() -> None:
    load_env_file()
    db = DbConn()
    workers: List[subprocess.Popen] = []

    try:
        while True:
            queued, running = get_counts(db)
            workers = prune_workers(workers)
            current = len(workers)

            desired = max(MIN_PROCS, math.ceil(queued / max(1, PROC_CAPACITY)))
            desired = min(desired, MAX_PROCS)

            if desired > current:
                to_add = desired - current
                for _ in range(to_add):
                    workers.append(spawn_worker())
                print(f"[manager] queued={queued} running={running} procs={len(workers)} (scaled up)")
            elif desired < current:
                to_kill = current - desired
                for _ in range(to_kill):
                    p = workers.pop()
                    p.terminate()
                print(f"[manager] queued={queued} running={running} procs={len(workers)} (scaled down)")
            else:
                print(f"[manager] queued={queued} running={running} procs={len(workers)}")

            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("Manager stopping, terminating workers...")
        for p in workers:
            p.terminate()
        for p in workers:
            try:
                p.wait(timeout=2.0)
            except Exception:
                pass


if __name__ == "__main__":
    main()
