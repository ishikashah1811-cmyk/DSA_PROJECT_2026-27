"""ContentIQ API.

    uvicorn api.main:app --reload        # from the repository root; docs at /docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .routes import benchmark, duplicates, hashtags, health, posts
from .state import AppState


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.ctx = AppState(settings)
        app.state.ctx.startup()
        yield

    app = FastAPI(
        title="ContentIQ API",
        version="0.1.0",
        description="Near-duplicate caption detection (MinHash + LSH) and hashtag intelligence (Trie + heap).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    for module in (health, posts, duplicates, hashtags, benchmark):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
