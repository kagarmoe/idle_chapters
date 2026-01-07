from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routers import journal, players, sessions, world


def create_app() -> FastAPI:
    app = FastAPI(title="Idle Chapters API", version="v1")
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

    return app


app = create_app()
