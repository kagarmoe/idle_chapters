FROM python:3.12-slim

WORKDIR /idle_chapters_app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY idle_chapters ./idle_chapters
COPY assets ./assets
COPY schemas ./schemas
COPY lexicons ./lexicons

EXPOSE 8000

CMD ["uvicorn", "idle_chapters.api.server:server", "--host", "0.0.0.0", "--port", "8000"]
