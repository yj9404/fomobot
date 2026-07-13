"""
뉴스 관련성 필터 / 지역 키 단위 테스트 (부동산).

LLM 없이 "제목 직접 언급 + 날짜 구간 내(+구 폴백 시 재료 키워드)" 규칙만으로
관련성을 판정하는 filter_relevant_articles와, 동/구 캐시 키 포맷을 한 곳에서
관리하는 region_key가 정확히 동작하는지 검증한다(네트워크·DB 의존 없음).
"""

from datetime import date

from realestate.services.naver_news import (
    _parse_pub_date,
    _strip_tags,
    filter_relevant_articles,
    region_key,
)


def make_article(title: str, published_at: date, link: str = "https://example.com/a") -> dict:
    return {"title": title, "link": link, "published_at": published_at}


class TestFilterRelevantArticles:
    def test_title_and_window_match_passes(self):
        articles = [make_article("개포동 재건축 이슈", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "개포동", date(2026, 6, 10), date(2026, 7, 10),
        )
        assert len(result) == 1

    def test_title_not_mentioned_excluded(self):
        articles = [make_article("강남구 아파트값 상승세", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "개포동", date(2026, 6, 10), date(2026, 7, 10),
        )
        assert result == []

    def test_date_outside_lookback_excluded(self):
        """랭킹 구간(3m/6m)이 아니라 뉴스 배치 자체의 lookback 창을 사용한다."""
        articles = [make_article("개포동 시세", date(2026, 1, 1))]
        result = filter_relevant_articles(
            articles, "개포동", date(2026, 6, 10), date(2026, 7, 10),
        )
        assert result == []

    def test_no_matching_articles_returns_empty_not_forced(self):
        articles = [make_article("타 지역 뉴스", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "개포동", date(2026, 6, 10), date(2026, 7, 10),
        )
        assert result == []

    def test_limit_and_latest_first(self):
        articles = [
            make_article("개포동 A", date(2026, 7, 1), link="a"),
            make_article("개포동 B", date(2026, 7, 5), link="b"),
            make_article("개포동 C", date(2026, 7, 3), link="c"),
            make_article("개포동 D", date(2026, 7, 8), link="d"),
        ]
        result = filter_relevant_articles(
            articles, "개포동", date(2026, 6, 10), date(2026, 7, 10), limit=3,
        )
        assert len(result) == 3
        assert [a["link"] for a in result] == ["d", "b", "c"]

    def test_gu_fallback_without_material_keyword_excluded(self):
        """구 단위 폴백은 also_require_any(재료 키워드) 없이는 일반 시황 기사와 섞일 위험 — 필터가 이를 보완."""
        articles = [make_article("강남구 아파트값 상승세", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "강남구", date(2026, 6, 10), date(2026, 7, 10),
            also_require_any=["재건축", "재개발"],
        )
        assert result == []

    def test_gu_fallback_with_material_keyword_passes(self):
        articles = [make_article("강남구 재건축 속도전", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "강남구", date(2026, 6, 10), date(2026, 7, 10),
            also_require_any=["재건축", "재개발"],
        )
        assert len(result) == 1


class TestRegionKey:
    def test_dong_key_format(self):
        assert region_key("11680", "개포동") == "11680:개포동"

    def test_gu_key_format_without_dong(self):
        assert region_key("11680") == "11680"
        assert region_key("11680", None) == "11680"

    def test_dong_and_gu_keys_differ(self):
        assert region_key("11680", "개포동") != region_key("11680")


class TestStripTags:
    def test_strip_bold_tags(self):
        assert _strip_tags("<b>래미안</b> 개포1단지") == "래미안 개포1단지"


class TestParsePubDate:
    def test_valid_rfc822(self):
        assert _parse_pub_date("Fri, 10 Jul 2026 09:00:00 +0900") == date(2026, 7, 10)

    def test_invalid_returns_none(self):
        assert _parse_pub_date("not a date") is None
