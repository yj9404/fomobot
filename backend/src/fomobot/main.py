import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fomobot.api.rankings import router as rankings_router
from fomobot.api.backtest import router as backtest_router
from fomobot.config import settings
from fomobot.sentry_init import init_sentry

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.enable_scheduler:
        # dev 환경에서만 활성화 — prod 은 Railway Cron 이 jobs.collect 를 직접 호출
        from fomobot.batch.scheduler import start_scheduler, shutdown_scheduler
        logger.info("APScheduler 활성화 (ENABLE_SCHEDULER=true)")
        start_scheduler()
        yield
        shutdown_scheduler()
    else:
        yield


app = FastAPI(
    title="FomoBot API",
    description=(
        "KOSPI·NASDAQ 기간별 상승률 랭킹 서비스. "
        "**투자 조언이 아닙니다. FomoBot은 지나간 걸 보여줄 뿐이에요.**"
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

_allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(rankings_router)
app.include_router(backtest_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    앱 상태 + 마지막 수집 성공 시각을 반환한다.
    마지막 랭킹 스냅샷이 HEALTH_STALE_HOURS 이상 오래됐으면 503 unhealthy.
    UptimeRobot 이 이 엔드포인트를 모니터링해 데이터 정체를 감지한다.
    """
    from fomobot.db.session import AsyncSessionLocal
    from fomobot.db.crud import get_latest_snapshot_date

    last_updated: str | None = None
    stale = False

    try:
        async with AsyncSessionLocal() as session:
            # KOSPI 와 NASDAQ 중 더 최근 날짜를 마지막 수집 시각으로 사용
            kospi_date = await get_latest_snapshot_date(session, "kospi", "1d")
            nasdaq_date = await get_latest_snapshot_date(session, "nasdaq", "1d")

        dates = [d for d in [kospi_date, nasdaq_date] if d is not None]
        if dates:
            latest = max(dates)
            last_updated = latest.isoformat()
            now_utc = datetime.now(timezone.utc).date()
            delta_hours = (now_utc - latest).days * 24
            stale = delta_hours >= settings.health_stale_hours
        else:
            stale = True

    except Exception:
        logger.exception("헬스체크 DB 조회 실패")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": "db_error", "last_updated": None},
        )

    if stale:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "reason": "stale_data",
                "last_updated": last_updated,
                "stale_threshold_hours": settings.health_stale_hours,
            },
        )

    return {
        "status": "ok",
        "last_updated": last_updated,
        "stale_threshold_hours": settings.health_stale_hours,
    }
