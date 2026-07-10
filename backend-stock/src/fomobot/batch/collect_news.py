"""
KOSPI 종목 관련 뉴스 수집 배치.

랭킹 배치 완료 후 별도로 실행된다(실시간 검색 금지 — API는 저장된 캐시만 조회).
종목 단위로 하루 1회만 검색해 stock_news에 TTL 캐시로 저장한다.

LLM 미사용 — 관련성 판정은 "제목에 종목명 직접 언급 + 발행일이 랭킹 구간 내"
규칙만 사용한다(fomobot.services.naver_news.filter_relevant_articles).
"""

import logging

from fomobot.config import settings
from fomobot.db.crud import (
    delete_expired_stock_news_sync,
    get_kospi_news_targets_sync,
    get_latest_ranking_snapshot_date_sync,
    replace_stock_news_sync,
)
from fomobot.db.session import SyncSessionLocal
from fomobot.services.naver_news import filter_relevant_articles, search_news

logger = logging.getLogger(__name__)


def collect_kospi_news() -> int:
    """
    오늘자 KOSPI 랭킹(1d/7d/30d top20 상승·하락) 종목의 뉴스를 갱신한다.

    랭킹 스냅샷이 없으면(배치 미실행 상태) 검색을 돌리지 않고 0을 반환한다.
    개별 종목 검색 실패는 격리한다(한 종목 실패가 나머지를 막지 않음).

    Returns
    -------
    int : 뉴스가 1건 이상 갱신된 종목 수
    """
    with SyncSessionLocal() as session:
        deleted = delete_expired_stock_news_sync(session, settings.stock_news_ttl_days)
        if deleted:
            logger.info("만료된 stock_news %d건 삭제", deleted)

        snapshot_date = get_latest_ranking_snapshot_date_sync(session, "kospi", "1d")
        if snapshot_date is None:
            logger.warning("KOSPI 랭킹 스냅샷 없음(랭킹 배치 미실행) — 뉴스 배치 스킵")
            return 0

        targets = get_kospi_news_targets_sync(session, snapshot_date)
        if not targets:
            logger.warning(
                "%s 기준 KOSPI 랭킹 대상 없음 — 랭킹 배치가 아직 안 돌았을 수 있음, 뉴스 배치 스킵",
                snapshot_date,
            )
            return 0

        updated = 0
        for target in targets:
            ticker, name = target["ticker"], target["name"]
            try:
                raw = search_news(f"{name} 주가")
                articles = filter_relevant_articles(
                    raw,
                    target_name=name,
                    window_start=target["window_start"],
                    window_end=target["window_end"],
                )
                replace_stock_news_sync(session, ticker, articles)
                if articles:
                    updated += 1
            except Exception:
                logger.exception("%s(%s) 뉴스 수집 실패 — 다음 종목으로 진행", name, ticker)
                continue

        logger.info(
            "KOSPI 뉴스 배치 완료: 대상 %d종목 중 %d종목 뉴스 확보 (기준일 %s)",
            len(targets), updated, snapshot_date,
        )
        return updated
