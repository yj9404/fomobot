# ── Build stage ───────────────────────────────────────────────────────────────
# python:3.12-slim 은 Debian bookworm 기반.
# psycopg2-binary 가 libpq.so 를 번들하므로 별도 libpq-dev 불필요.
# pykrx 가 pkg_resources 를 사용하므로 setuptools 를 pyproject.toml 에 고정(<70).
FROM python:3.12-slim AS builder

WORKDIR /build

# uv 를 빠른 pip 대체재로 사용해 레이어 캐시를 최대화
RUN pip install --no-cache-dir uv

COPY pyproject.toml .
# src 레이아웃 패키지 메타데이터 참조용
COPY src/ src/

# 의존성만 먼저 설치 (소스 변경 시 이 레이어는 재사용됨)
RUN uv pip install --system --no-cache ".[dev]" 2>/dev/null || \
    uv pip install --system --no-cache .


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# builder 에서 설치된 site-packages 복사
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 소스 코드 및 마이그레이션 파일 복사
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/ scripts/

# 마이그레이션 실행 후 웹 서버 시작
# 배치 실행은 railway.toml 의 cron 서비스에서 별도로 정의한다:
#   python -m fomobot.jobs.collect kospi
#   python -m fomobot.jobs.collect nasdaq
CMD alembic upgrade head && uvicorn fomobot.main:app --host 0.0.0.0 --port ${PORT:-8000}
