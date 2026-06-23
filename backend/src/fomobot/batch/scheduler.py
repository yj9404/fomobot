"""
APScheduler 배치 스케줄러.

스케줄:
  - KOSPI 수집:   매일 18:00 KST
  - NASDAQ 수집:  매일 07:30 KST
  - 랭킹 계산:    각 수집 완료 직후 트리거 (event listener 방식)

FastAPI lifespan에서 start/shutdown된다.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

KOSPI_COLLECT_JOB_ID = "kospi_collect"
NASDAQ_COLLECT_JOB_ID = "nasdaq_collect"
KOSPI_RANK_JOB_ID = "kospi_rank"
NASDAQ_RANK_JOB_ID = "nasdaq_rank"


def _run_kospi_collect():
    from fomobot.batch.collect_kospi import run_kospi_collection
    run_kospi_collection()


def _run_nasdaq_collect():
    from fomobot.batch.collect_nasdaq import run_nasdaq_collection
    run_nasdaq_collection()


def _run_kospi_rankings():
    from fomobot.batch.compute_rankings import compute_rankings_for_market
    from datetime import date
    compute_rankings_for_market("kospi", date.today())


def _run_nasdaq_rankings():
    from fomobot.batch.compute_rankings import compute_rankings_for_market
    from datetime import date
    compute_rankings_for_market("nasdaq", date.today())


def _on_job_executed(event: JobExecutionEvent):
    """수집 완료 후 랭킹 계산 잡을 즉시 트리거한다."""
    if _scheduler is None:
        return
    if event.job_id == KOSPI_COLLECT_JOB_ID:
        logger.info("KOSPI 수집 완료 → 랭킹 계산 트리거")
        _scheduler.add_job(
            _run_kospi_rankings,
            id=KOSPI_RANK_JOB_ID + "_triggered",
            replace_existing=True,
        )
    elif event.job_id == NASDAQ_COLLECT_JOB_ID:
        logger.info("NASDAQ 수집 완료 → 랭킹 계산 트리거")
        _scheduler.add_job(
            _run_nasdaq_rankings,
            id=NASDAQ_RANK_JOB_ID + "_triggered",
            replace_existing=True,
        )


def _on_job_error(event: JobExecutionEvent):
    logger.error("배치 잡 실패: %s — %s", event.job_id, event.exception)


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            timezone="Asia/Seoul",
            job_defaults={"coalesce": True, "max_instances": 1},
        )
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()

    # KOSPI 수집: 매일 18:00 KST
    scheduler.add_job(
        _run_kospi_collect,
        trigger="cron",
        hour=18,
        minute=0,
        id=KOSPI_COLLECT_JOB_ID,
        replace_existing=True,
    )

    # NASDAQ 수집: 매일 07:30 KST
    scheduler.add_job(
        _run_nasdaq_collect,
        trigger="cron",
        hour=7,
        minute=30,
        id=NASDAQ_COLLECT_JOB_ID,
        replace_existing=True,
    )

    # 랭킹 계산 (정기 백업): 각 수집 후 30분 뒤 고정 스케줄
    scheduler.add_job(
        _run_kospi_rankings,
        trigger="cron",
        hour=18,
        minute=30,
        id=KOSPI_RANK_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _run_nasdaq_rankings,
        trigger="cron",
        hour=8,
        minute=0,
        id=NASDAQ_RANK_JOB_ID,
        replace_existing=True,
    )

    scheduler.add_listener(_on_job_executed, EVENT_JOB_EXECUTED)
    scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)

    scheduler.start()
    logger.info("배치 스케줄러 시작 (KOSPI 18:00 / NASDAQ 07:30 KST)")


def shutdown_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("배치 스케줄러 종료")
