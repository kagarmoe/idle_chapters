from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routers import journal, players, sessions, world


def create_app() -> FastAPI:
    app = FastAPI(title="Idle Chapters API", version="v1")
    app.include_router(world.router)
    app.include_router(players.router)
    app.include_router(sessions.router)
    app.include_router(journal.router)

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
