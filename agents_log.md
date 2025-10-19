# Status & Next Steps

## Where We Are
- Python env: `.venv` created and set as default in `.vscode/settings.json`.
- Dependencies installed: `python-okx`, `python-dotenv`, `SQLAlchemy`, `Alembic`, `psycopg2-binary`.
- Config: `src/config.py` loads `resources/.env` and builds `DATABASE_URL`.
- OKX client: `src/api/okx_market_data_client.py` fetches candlesticks; `src/main.py` loads `.env` and prints data.
- DB layer:
  - ORM base: `src/db/base.py`.
  - Model: `src/db/poco/candlestick.py`.
  - Conn helper: `src/db/db_conn.py` (engine/session, connection test, alembic revision).
  - Repo: `src/db/candles_repo.py` with PostgreSQL UPSERT and OKX row parser.
  - CLI: `src/main_db.py` (connection test) and `src/main_ingest.py` (fetch from OKX, upsert to DB).
- Migrations (Alembic):
  - `alembic.ini`, `alembic/env.py`, `alembic/versions/20251019_000001_init_schema.py` applied.
- TimescaleDB: deferred for now (Postgres 18 not supported yet by Timescale at time of setup).

## Validation Done
- `src/main.py` successfully fetched live OKX candlesticks.
- `src/main_db.py` confirmed DB connectivity and shows current Alembic revision.
- `src/main_ingest.py` inserted rows via UPSERT (tested with BTC-USDT, 1m, limit 10).

## Suggestions (Short-Term)
- Ingest robustness:
  - Add retry/backoff, HTTP timeouts, and simple rate-limiting for OKX calls.
  - Implement pagination/backfill to load historical ranges.
  - Idempotent upserts are in place; add batching if limits increase.
- Data model:
  - Consider storing quote volume and any extra fields returned by OKX as nullable columns.
  - Add CHECK constraints (e.g., `open/high/low/close >= 0`, `volume >= 0`).
- Observability:
  - Structured logging (e.g., JSON logs) and basic metrics (counts, latency).
  - Add a lightweight healthcheck endpoint or CLI command for liveness.
- Testing:
  - Unit tests for `OkxMarketDataClient` (mock SDK), `CandlesRepo` (against a test DB).
  - Add a small integration test that runs a migration and upserts sample rows.
- Dev UX:
  - Provide a `resources/.env.example` (no secrets) for onboarding.
  - Optional scripts for setup/run (PowerShell/Make) if team prefers one-liners.

## Suggestions (Mid-Term)
- TimescaleDB (when Postgres 18 support is available):
  - Convert `candlesticks` to hypertable on `ts` with `instrument_id` partitioning.
  - Add time-desc index, compression, and retention policies.
- Backfilling & Scheduling:
  - A backfill CLI that walks time windows until seed history is complete.
  - A scheduler (e.g., APScheduler/Celery) for periodic ingest.
- Strategy & Backtesting foundations:
  - Define a raw market data access layer (time-window queries, resampling).
  - Create a backtest runner interface and a simple moving-average example.
- API & Frontend prep:
  - Start a minimal Node.js API (read-only endpoints) to expose portfolio and data for a React UI.
- CI/CD:
  - Add linting (ruff/flake8), type checks (mypy), and a migration check step.
  - Optional Dockerfiles for app and a local dev DB.

## Handy Commands
- Fetch and print live data: `python src/main.py --inst BTC-USDT --bar 1m --limit 5`
- Test DB connection: `python src/main_db.py --echo`
- Ingest into DB: `python src/main_ingest.py --inst BTC-USDT --bar 1m --limit 50`
- Alembic upgrade: `.\.venv\Scripts\alembic.exe -c alembic.ini upgrade head`
- Create migration: `.\.venv\Scripts\alembic.exe -c alembic.ini revision --autogenerate -m "change"`

## Open Questions
- Target history depth for initial backfill per instrument/bar (e.g., 6 months, 1 year)?
- Priority instruments and granularities?
- Preferred scheduling mechanism (external scheduler vs. in-app)?
- Any specific SLAs for data freshness and error budgets?

## 2025-10-19
- Summary
  - Alembic initialized and initial schema applied; `candlesticks` table live.
  - Implemented `DbConn`, `CandlesRepo` with UPSERT, and ingestion CLI.
  - Verified OKX fetch, DB connection, migration state, and successful upserts.
- Decisions
  - TimescaleDB deferred until official PostgreSQL 18 support lands.
  - Store minimal fields (ts, o/h/l/c, volume) for now; consider extra columns later.
- Next Steps
  - Add retry/backoff and timeouts to OKX client and ingestion.
  - Implement historical backfill with pagination and windowing.
  - Add constraints and basic validation on numeric fields.
  - Set up simple logging/metrics; optional scheduler for periodic ingest.
- Handy Commands
  - Fetch and print: `python src/main.py --inst BTC-USDT --bar 1m --limit 5`
  - Test DB: `python src/main_db.py --echo`
  - Ingest: `python src/main_ingest.py --inst BTC-USDT --bar 1m --limit 50`
  - Migrate: `.\.venv\Scripts\alembic.exe -c alembic.ini upgrade head`
