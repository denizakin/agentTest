from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import load_env_file
from web.routes import backtests, coins, strategies, ui, jobs


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

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(strategies.router)
    app.include_router(coins.router)
    app.include_router(backtests.router)
    app.include_router(jobs.router)
    app.include_router(ui.router)
    # Serve generated plot images (if any)
    import os
    from pathlib import Path
    plots_dir = Path(__file__).parent.parent / "resources" / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/plots", StaticFiles(directory=str(plots_dir)), name="plots")

    return app


app = create_app()
