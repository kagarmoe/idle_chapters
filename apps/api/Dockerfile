FROM python:3.12-slim

WORKDIR /app

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/app ./app
COPY assets ./assets
COPY schemas ./schemas
COPY lexicons ./lexicons

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
