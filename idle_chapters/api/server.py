from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from idle_chapters.api.routers import journal, players, sessions, world
from idle_chapters.services.errors import GameError


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

    @app.exception_handler(GameError)
    async def handle_game_error(request: Request, exc: GameError) -> JSONResponse:
        projection = request.headers.get("Accept-Projection", "developer")
        if projection == "player":
            body = exc.project_player()
        else:
            body = exc.project_developer()
        return JSONResponse(status_code=exc.http_status, content=body)

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
