import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fomobot.api.rankings import router as rankings_router
from fomobot.api.backtest import router as backtest_router
from fomobot.batch.scheduler import start_scheduler, shutdown_scheduler

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(rankings_router)
app.include_router(backtest_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
