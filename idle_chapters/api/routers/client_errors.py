from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from idle_chapters.api.error_log import log_error

router = APIRouter(prefix="/v1", tags=["client-errors"])


class ClientErrorReport(BaseModel):
    """What the browser may say about an error. Unauthenticated, so every field is capped and nothing else is accepted."""

    model_config = ConfigDict(extra="forbid")

    level: Literal["warning", "error"]
    kind: str = Field(max_length=100)
    message: str = Field(max_length=500)
    path: str = Field(max_length=200)
    stack: str = Field("", max_length=4000)


@router.post(
    "/client-errors",
    status_code=204,
    summary="Report a browser error",
    description="The web client reports its errors, handled or not, so they reach the logs. Nothing the player typed is sent.",
)
def report_client_error(report: ClientErrorReport, request: Request) -> Response:
    log_error(report.level, "browser", kind=report.kind, message=report.message, path=report.path,
              stack=report.stack, user_agent=request.headers.get("user-agent", "")[:300])
    return Response(status_code=204)
