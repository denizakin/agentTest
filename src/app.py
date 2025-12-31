from __future__ import annotations

from fastapi import FastAPI

from config import load_env_file
from web.routes import backtests, coins, strategies, ui


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    load_env_file()

    app = FastAPI(
        title="Auto-Trading Platform API",
        version="0.1.0",
        description="Stubs for strategies, coins, and backtests.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(strategies.router)
    app.include_router(coins.router)
    app.include_router(backtests.router)
    app.include_router(ui.router)

    return app


app = create_app()
