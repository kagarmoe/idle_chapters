from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from idle_chapters.api.deps import get_content_repo
from idle_chapters.api.error_log import log_error, route_of
from idle_chapters.api.routers import client_errors, journal, players, sessions, world
from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery


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
    app.include_router(client_errors.router)

    def problem(request: Request, exc: GameError) -> JSONResponse:
        projection = request.headers.get("Accept-Projection", "developer")
        if projection == "player":
            body = exc.project_player()
        else:
            body = exc.project_developer()
        return JSONResponse(status_code=exc.http_status, content=body)

    @app.exception_handler(GameError)
    async def handle_game_error(request: Request, exc: GameError) -> JSONResponse:
        # The title, not the detail: details can carry ids.
        log_error("error" if exc.http_status >= 500 else "warning", "api", kind=exc.kind.value,
                  status=exc.http_status, method=request.method, path=route_of(request), message=exc.title)
        return problem(request, exc)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        log_error("error", "api", kind=type(exc).__name__, status=500, method=request.method,
                  path=route_of(request), message=str(exc)[:500],
                  stack="".join(traceback.format_exception(exc))[-4000:])
        return problem(request, GameError(ErrorKind.ENGINE_FAILURE, Effect.UNKNOWN, Recovery.RETRYABLE))

    @app.on_event("startup")
    def export_openapi():
        spec = app.openapi()
        try:
            Path("docs/openapi.json").write_text(json.dumps(spec, indent=2))
        except OSError:
            pass  # serverless hosts have a read-only filesystem; CI checks the committed spec

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @app.get("/health")
    def health() -> dict:
        get_content_repo()
        # Vercel sets this per deployment; ic-ship's smoke waits for the merged commit.
        return {"status": "ok", "commit": os.getenv("VERCEL_GIT_COMMIT_SHA")}

    return app


server = create_app()
