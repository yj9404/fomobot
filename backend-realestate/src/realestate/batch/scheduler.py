"""APScheduler — dev 환경 전용. prod 에서는 Railway Cron이 jobs.* 를 직접 호출한다."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="Asia/Seoul")

    # 매월 15일 오전 3시 증분 수집 + 랭킹 재계산
    _scheduler.add_job(
        _run_incremental,
        "cron",
        day=15,
        hour=3,
        minute=0,
        id="re_incremental",
    )
    _scheduler.start()
    logger.info("부동산 스케줄러 시작 (dev mode)")


def shutdown_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("부동산 스케줄러 종료")


def _run_incremental() -> None:
    try:
        from realestate.jobs.incremental import run_incremental
        run_incremental()
    except Exception:
        logger.exception("부동산 증분 수집 스케줄 실패")
