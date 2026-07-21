import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from realestate.api.rankings import router as rankings_router
from realestate.api.region import router as region_router
from realestate.api.search import router as search_router
from realestate.api.news import router as news_router
from realestate.config import settings
from realestate.sentry_init import init_sentry

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.enable_scheduler:
        from realestate.batch.scheduler import start_scheduler, shutdown_scheduler
        logger.info("APScheduler 활성화 (ENABLE_SCHEDULER=true)")
        start_scheduler()
        yield
        shutdown_scheduler()
    else:
        yield


app = FastAPI(
    title="FomoBot Real Estate API",
    description=(
        "수도권 아파트 평단가 상승률 랭킹 서비스. "
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
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

app.include_router(rankings_router)
app.include_router(region_router)
app.include_router(search_router)
app.include_router(news_router)


@app.api_route("/health", methods=["GET", "HEAD"], tags=["Health"])
async def health_check():
    """
    앱 상태 + 마지막 랭킹 스냅샷 날짜를 반환한다.
    마지막 스냅샷이 HEALTH_STALE_DAYS 이상 오래됐으면 503 unhealthy.
    """
    from realestate.db.session import AsyncSessionLocal
    from realestate.db.crud import get_latest_snapshot_ym

    last_snapshot_ym: str | None = None
    stale = False

    try:
        async with AsyncSessionLocal() as session:
            last_snapshot_ym = await get_latest_snapshot_ym(session, "gu", "1y")

        if last_snapshot_ym:
            snap_year = int(last_snapshot_ym[:4])
            snap_month = int(last_snapshot_ym[4:])
            today = date.today()
            months_behind = (today.year - snap_year) * 12 + (today.month - snap_month)
            stale = months_behind > settings.health_stale_months

    except Exception:
        logger.exception("헬스체크 DB 조회 실패")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "reason": "db_error", "last_snapshot_ym": None},
        )

    if stale:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "reason": "stale_data",
                "last_snapshot_ym": last_snapshot_ym,
                "stale_threshold_months": settings.health_stale_months,
            },
        )

    body: dict = {
        "status": "ok",
        "last_snapshot_ym": last_snapshot_ym,
        "stale_threshold_months": settings.health_stale_months,
    }
    if last_snapshot_ym is None:
        body["note"] = "no data yet"
    return body
