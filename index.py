# Vercel's zero-config FastAPI entrypoint looks for `app` in a root index.py.
from idle_chapters.api.server import server as app

__all__ = ["app"]
