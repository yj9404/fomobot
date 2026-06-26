FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev --no-cache

ENV PATH="/app/.venv/bin:$PATH"

COPY alembic/ alembic/
COPY alembic.ini .

CMD alembic upgrade head && uvicorn realestate.main:app --host 0.0.0.0 --port ${PORT:-8000}
