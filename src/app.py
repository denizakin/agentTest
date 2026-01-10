from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import load_env_file
from db.db_conn import DbConn
from web.routes import backtests, coins, strategies, ui, jobs
from web.worker import start_background_worker


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    load_env_file()

    app = FastAPI(
        title="Auto-Trading Platform API",
        version="0.1.0",
        description="Stubs for strategies, coins, and backtests.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize DB and start background worker for in-memory queue (dev placeholder).
    db_conn = DbConn()
    start_background_worker(db_conn)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(strategies.router)
    app.include_router(coins.router)
    app.include_router(backtests.router)
    app.include_router(jobs.router)
    app.include_router(ui.router)

    return app


app = create_app()
