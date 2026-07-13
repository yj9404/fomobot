"""
네이버 뉴스 검색 API 클라이언트 + 규칙 기반 관련성 필터.

LLM 미사용 — 관련성 판정은 "제목에 대상명 직접 언급 + 발행일이 구간 내"라는
규칙만으로 수행한다(뉴스의 분석·요약·인과 서술은 하지 않는다. 저장·표시하는
건 기사 제목+링크+날짜뿐).
"""

import logging
import re
from datetime import date
from email.utils import parsedate_to_datetime

import httpx

from realestate.config import settings

logger = logging.getLogger(__name__)

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"

_TAG_RE = re.compile(r"</?b>")

# 동 단위 검색+필터 결과가 이 값 미만이면 그 동이 속한 구 단위로 폴백 검색한다.
DONG_INSUFFICIENT_THRESHOLD = 3

# 구 단위 폴백 검색에서 "OO구 집값" 같은 일반 시황성 기사를 걸러내기 위해
# 제목에 하나 이상 포함되기를 요구하는 부동산 재료 키워드.
GU_FALLBACK_KEYWORDS = [
    "재건축", "재개발", "정비사업", "분양", "착공", "입주", "역세권", "GTX",
]


def _strip_tags(text: str) -> str:
    """네이버 API가 매칭 키워드를 감싸는 <b></b> 태그를 제거한다."""
    return _TAG_RE.sub("", text)


def _parse_pub_date(pub_date: str) -> date | None:
    """RFC 822 형식(pubDate)을 date로 변환한다. 파싱 실패 시 None."""
    try:
        return parsedate_to_datetime(pub_date).date()
    except (TypeError, ValueError, IndexError):
        return None


def region_key(sigungu_code: str, eupmyeondong: str | None = None) -> str:
    """
    지역 뉴스 캐시 키를 만든다. 동 단위는 "{sigungu_code}:{eupmyeondong}",
    구 단위(폴백)는 "{sigungu_code}" 단독 — 배치(쓰기)와 조회(읽기) 양쪽에서
    동일한 포맷을 쓰도록 한 곳에서 관리한다.
    """
    return f"{sigungu_code}:{eupmyeondong}" if eupmyeondong else sigungu_code


def search_news(query: str, display: int = 10) -> list[dict]:
    """
    네이버 뉴스 검색 API 호출 결과를 정제해 반환한다.

    반환 각 항목: {"title": str, "link": str, "published_at": date}
    - title: <b></b> 태그 제거 완료
    - link: originallink(언론사 원문) 우선, 없으면 link(네이버뉴스)로 폴백
    - published_at 파싱 실패 항목은 구간 판정이 불가능하므로 제외

    API 키가 설정되지 않았으면 빈 리스트를 반환한다(배치가 조용히 스킵하도록).
    """
    if not settings.naver_client_id or not settings.naver_client_secret:
        logger.warning("NAVER_CLIENT_ID/SECRET 미설정 — 뉴스 검색 스킵")
        return []

    try:
        resp = httpx.get(
            NAVER_NEWS_URL,
            params={"query": query, "display": display, "sort": "date"},
            headers={
                "X-Naver-Client-Id": settings.naver_client_id,
                "X-Naver-Client-Secret": settings.naver_client_secret,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception:
        logger.exception("네이버 뉴스 검색 실패: query=%s", query)
        return []

    results: list[dict] = []
    for item in items:
        published_at = _parse_pub_date(item.get("pubDate", ""))
        if published_at is None:
            continue
        link = item.get("originallink") or item.get("link") or ""
        if not link:
            continue
        results.append({
            "title": _strip_tags(item.get("title", "")),
            "link": link,
            "published_at": published_at,
        })
    return results


def filter_relevant_articles(
    raw_articles: list[dict],
    target_name: str,
    window_start: date,
    window_end: date,
    limit: int = 3,
    also_require_any: list[str] | None = None,
    also_require_sido: list[str] | None = None,
) -> list[dict]:
    """
    규칙 기반 관련성 필터 (LLM 미사용).

    통과 조건 (모두 충족해야 함):
      1. 제목에 target_name이 직접 포함
      2. also_require_any가 주어지면 그중 하나도 제목에 포함
         (구 단위 폴백 검색에서 일반 시황성 기사 축소용 — GU_FALLBACK_KEYWORDS 참조)
      3. also_require_sido가 주어지면 그중 하나도 제목에 포함
         (also_require_any와 독립적인 별도 AND 조건 — "중구"처럼 여러 시/도에
         동시 존재하는 동명 지역명 오탐 방지용. batch.regions.DUPLICATE_GU_NAMES 참조)
      4. 발행일이 [window_start, window_end] 구간 내

    통과분을 발행일 최신순으로 정렬해 최대 limit개 반환한다.
    조건을 만족하는 기사가 없으면 빈 리스트(억지 매칭 금지).
    """
    passed = []
    for article in raw_articles:
        title = article["title"]
        if target_name not in title:
            continue
        if also_require_any and not any(name in title for name in also_require_any if name):
            continue
        if also_require_sido and not any(name in title for name in also_require_sido if name):
            continue
        published_at = article["published_at"]
        if not (window_start <= published_at <= window_end):
            continue
        passed.append(article)

    passed.sort(key=lambda a: a["published_at"], reverse=True)
    return passed[:limit]
