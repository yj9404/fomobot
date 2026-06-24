FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir uv

# 의존성만 먼저 설치해 레이어 캐시 활용 (소스 변경 시 재설치 불필요)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache --no-install-project

# 소스 및 마이그레이션 복사 후 프로젝트 본체 설치
COPY src/ src/
RUN uv sync --frozen --no-dev --no-cache

ENV PATH="/app/.venv/bin:$PATH"

COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/ scripts/

# venv가 /app/.venv에 직접 생성되므로 경로 이동 없음 → shebang 깨짐 없음
CMD alembic upgrade head && uvicorn fomobot.main:app --host 0.0.0.0 --port ${PORT:-8000}
