"""
동/구 지역 관련 뉴스 수집 배치.

랭킹 계산(월 1회, batch/complex_rankings.py)과는 완전히 독립된 주기(주 1회)로
실행된다 — 랭킹 계산 로직은 건드리지 않고, 가장 최근에 존재하는 랭킹 스냅샷의
top/bottom 20 단지가 속한 동에 대해 뉴스만 재검색해 캐시를 갱신한다.

단지 단위(apt_name) 검색은 개별 단지 기사가 원래 희소해 회수율이 극히 낮았다.
뉴스의 자연스러운 단위인 동(1순위)/구(동 결과 부족 시 폴백)로 전환했다.

뉴스는 랭킹 구간(3m/6m)의 "구간 정합 지표"가 아니라 "최근 주목 표시"이므로
날짜 필터는 랭킹 구간이 아닌 이 배치 자체의 lookback(기본 30일)을 사용한다.

LLM 미사용 — 관련성 판정은 "제목에 지역명 직접 언급(+구 폴백 시 재료 키워드) +
발행일이 lookback 내" 규칙만 사용한다(realestate.services.naver_news.filter_relevant_articles).
"""

import logging
from datetime import date, timedelta

from realestate.config import settings
from realestate.db.crud import (
    delete_expired_region_news_sync,
    get_latest_complex_snapshot_ym_sync,
    get_region_news_targets_sync,
    replace_region_news_sync,
)
from realestate.db.session import SyncSessionLocal
from realestate.services.naver_news import (
    DONG_INSUFFICIENT_THRESHOLD,
    GU_FALLBACK_KEYWORDS,
    filter_relevant_articles,
    region_key,
    search_news,
)

logger = logging.getLogger(__name__)

NEWS_PERIODS = ("3m", "6m")


def collect_region_news() -> int:
    """
    가장 최근 랭킹 스냅샷(3m/6m) 상의 top/bottom 20 단지가 속한 동/구 뉴스를 갱신한다.

    랭킹 데이터가 한 번도 계산된 적 없으면(완전 초기 상태) 검색을 돌리지 않고
    0을 반환한다. 개별 동/구 검색 실패는 격리한다.

    Returns
    -------
    int : 뉴스가 1건 이상 갱신된 동 수
    """
    with SyncSessionLocal() as session:
        deleted = delete_expired_region_news_sync(session, settings.region_news_ttl_days)
        if deleted:
            logger.info("만료된 re_region_news %d건 삭제", deleted)

        dong_targets: dict[tuple[str, str], dict] = {}
        for period in NEWS_PERIODS:
            snapshot_ym = get_latest_complex_snapshot_ym_sync(session, period)
            if snapshot_ym is None:
                continue
            for target in get_region_news_targets_sync(session, period, snapshot_ym):
                dong_targets.setdefault(
                    (target["sigungu_code"], target["eupmyeondong"]), target,
                )

        if not dong_targets:
            logger.warning("단지 랭킹 스냅샷 없음(랭킹 배치 미실행) — 뉴스 배치 스킵")
            return 0

        window_end = date.today()
        window_start = window_end - timedelta(days=settings.region_news_lookback_days)

        updated = 0
        gu_needs_fallback: dict[str, str] = {}
        for (sigungu_code, eupmyeondong), target in dong_targets.items():
            sigungu_name = target["sigungu_name"]
            key = region_key(sigungu_code, eupmyeondong)
            label = f"{sigungu_name} {eupmyeondong}"
            try:
                raw = search_news(f"{sigungu_name} {eupmyeondong} 아파트", display=100)
                articles = filter_relevant_articles(
                    raw,
                    target_name=eupmyeondong,
                    window_start=window_start,
                    window_end=window_end,
                )
                replace_region_news_sync(session, key, label, "dong", articles)
                if articles:
                    updated += 1
                if len(articles) < DONG_INSUFFICIENT_THRESHOLD:
                    gu_needs_fallback.setdefault(sigungu_code, sigungu_name)
            except Exception:
                logger.exception("%s 뉴스 수집 실패 — 다음 동으로 진행", label)
                continue

        for sigungu_code, sigungu_name in gu_needs_fallback.items():
            key = region_key(sigungu_code)
            try:
                raw = search_news(f"{sigungu_name} 부동산", display=100)
                articles = filter_relevant_articles(
                    raw,
                    target_name=sigungu_name,
                    window_start=window_start,
                    window_end=window_end,
                    also_require_any=GU_FALLBACK_KEYWORDS,
                )
                replace_region_news_sync(session, key, sigungu_name, "gu", articles)
            except Exception:
                logger.exception("%s 구 단위 폴백 뉴스 수집 실패 — 다음 구로 진행", sigungu_name)
                continue

        logger.info(
            "지역 뉴스 배치 완료: 대상 %d개 동(구 폴백 %d개 구) 중 %d개 동 뉴스 확보",
            len(dong_targets), len(gu_needs_fallback), updated,
        )
        return updated
