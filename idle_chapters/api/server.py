from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routers import journal, players, sessions, world


def create_app() -> FastAPI:
    app = FastAPI(title="Idle Chapters API", version="v1")

    allowed_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(world.router)
    app.include_router(players.router)
    app.include_router(sessions.router)
    app.include_router(journal.router)

    @app.on_event("startup")
    def export_openapi():
        spec = app.openapi()
        Path("docs/openapi.json").write_text(json.dumps(spec, indent=2))

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


server = create_app()
