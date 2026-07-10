"""
아파트 단지 관련 뉴스 수집 배치.

랭킹 계산(월 1회, batch/complex_rankings.py)과는 완전히 독립된 주기(주 1회)로
실행된다 — 랭킹 계산 로직은 건드리지 않고, 가장 최근에 존재하는 랭킹 스냅샷의
top/bottom 20 단지에 대해 뉴스만 재검색해 캐시를 갱신한다.

뉴스는 랭킹 구간(3m/6m)의 "구간 정합 지표"가 아니라 "최근 주목 표시"이므로
날짜 필터는 랭킹 구간이 아닌 이 배치 자체의 lookback(기본 30일)을 사용한다.

LLM 미사용 — 관련성 판정은 "제목에 단지명 직접 언급 + 발행일이 lookback 내"
규칙만 사용한다(realestate.services.naver_news.filter_relevant_articles).
"""

import logging
from datetime import date, timedelta

from realestate.config import settings
from realestate.db.crud import (
    delete_expired_complex_news_sync,
    get_complex_news_targets_sync,
    get_latest_complex_snapshot_ym_sync,
    replace_complex_news_sync,
)
from realestate.db.session import SyncSessionLocal
from realestate.services.naver_news import (
    filter_relevant_articles,
    is_generic_short_name,
    search_news,
)

logger = logging.getLogger(__name__)

NEWS_PERIODS = ("3m", "6m")


def collect_complex_news() -> int:
    """
    가장 최근 랭킹 스냅샷(3m/6m) 상의 top/bottom 20 단지 뉴스를 갱신한다.

    랭킹 데이터가 한 번도 계산된 적 없으면(완전 초기 상태) 검색을 돌리지 않고
    0을 반환한다. 개별 단지 검색 실패는 격리한다.

    Returns
    -------
    int : 뉴스가 1건 이상 갱신된 단지 수
    """
    with SyncSessionLocal() as session:
        deleted = delete_expired_complex_news_sync(session, settings.complex_news_ttl_days)
        if deleted:
            logger.info("만료된 re_complex_news %d건 삭제", deleted)

        targets_by_key: dict[str, dict] = {}
        for period in NEWS_PERIODS:
            snapshot_ym = get_latest_complex_snapshot_ym_sync(session, period)
            if snapshot_ym is None:
                continue
            for target in get_complex_news_targets_sync(session, period, snapshot_ym):
                targets_by_key.setdefault(target["complex_key"], target)

        if not targets_by_key:
            logger.warning("단지 랭킹 스냅샷 없음(랭킹 배치 미실행) — 뉴스 배치 스킵")
            return 0

        window_end = date.today()
        window_start = window_end - timedelta(days=settings.complex_news_lookback_days)

        updated = 0
        for target in targets_by_key.values():
            complex_key = target["complex_key"]
            apt_name = target["apt_name"]
            sigungu_name = target["sigungu_name"]
            eupmyeondong = target["eupmyeondong"]
            try:
                raw = search_news(f"{apt_name} {sigungu_name}")
                also_require_any = (
                    [sigungu_name, eupmyeondong] if is_generic_short_name(apt_name) else None
                )
                articles = filter_relevant_articles(
                    raw,
                    target_name=apt_name,
                    window_start=window_start,
                    window_end=window_end,
                    also_require_any=also_require_any,
                )
                replace_complex_news_sync(session, complex_key, articles)
                if articles:
                    updated += 1
            except Exception:
                logger.exception("%s(%s) 뉴스 수집 실패 — 다음 단지로 진행", apt_name, complex_key)
                continue

        logger.info(
            "단지 뉴스 배치 완료: 대상 %d단지 중 %d단지 뉴스 확보",
            len(targets_by_key), updated,
        )
        return updated
