"""CLI: Test database connectivity using SQLAlchemy and Alembic.

Reads configuration from resources/.env via config.load_env_file().
Performs a simple SELECT 1 using SQLAlchemy, and if available,
prints the current Alembic revision from alembic_version table.
"""
from __future__ import annotations

import argparse

from config import load_env_file, get_database_url
from db.db_conn import DbConn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test DB connection")
    parser.add_argument("--echo", action="store_true", help="Enable SQLAlchemy engine echo")
    return parser.parse_args()


def main() -> int:
    load_env_file()

    url = get_database_url()
    if not url:
        print("DATABASE_URL not set or incomplete DB_* variables. Check resources/.env.")
        return 2

    args = parse_args()
    try:
        db = DbConn(db_url=url, echo=args.echo)
    except Exception as exc:
        print(f"Failed to configure engine: {exc}")
        return 2

    ok = db.test_connection()
    print(f"Connection test: {'OK' if ok else 'FAILED'}")
    if not ok:
        return 1

    rev = db.get_alembic_revision()
    if rev:
        print(f"Alembic revision: {rev}")
    else:
        print("Alembic revision: not found (no alembic_version table)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

