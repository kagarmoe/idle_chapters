"""One JSON line per error on stderr: Vercel's runtime logs carry it to the drain (monitoring design §1)."""

from __future__ import annotations

import json
import os
import sys

from fastapi import Request


def route_of(request: Request) -> str:
    """The matched route template, so ids and query strings never reach the logs."""
    return getattr(request.scope.get("route"), "path", "unmatched")


def log_error(level: str, source: str, **fields: object) -> None:
    line = {"event": "error", "level": level, "source": source,
            "commit": os.getenv("VERCEL_GIT_COMMIT_SHA"), **fields}
    print(json.dumps(line, default=str), file=sys.stderr, flush=True)
