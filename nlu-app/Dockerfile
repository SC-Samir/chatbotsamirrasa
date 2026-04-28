FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_HTTP_TIMEOUT=300 \
    UV_HTTP_RETRIES=5

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY app ./app
COPY scripts ./scripts
COPY data.nlu.yml ./data.nlu.yml
COPY models ./models

RUN uv run --no-project python scripts/train.py --input data.nlu.yml --output models/model.joblib

CMD ["uv", "run", "--no-project", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
