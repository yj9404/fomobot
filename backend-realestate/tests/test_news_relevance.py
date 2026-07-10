"""
뉴스 관련성 필터 단위 테스트 (부동산).

LLM 없이 "제목 직접 언급 + 날짜 구간 내" 규칙만으로 관련성을 판정하는
filter_relevant_articles와, 브랜드 단독명(자이/래미안류) 판정 휴리스틱인
is_generic_short_name이 정확히 동작하는지 검증한다(네트워크·DB 의존 없음).
"""

from datetime import date

from realestate.services.naver_news import (
    _parse_pub_date,
    _strip_tags,
    filter_relevant_articles,
    is_generic_short_name,
)


def make_article(title: str, published_at: date, link: str = "https://example.com/a") -> dict:
    return {"title": title, "link": link, "published_at": published_at}


class TestFilterRelevantArticles:
    def test_title_and_window_match_passes(self):
        articles = [make_article("래미안개포1단지 재건축 이슈", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "래미안개포1단지", date(2026, 6, 10), date(2026, 7, 10),
        )
        assert len(result) == 1

    def test_title_not_mentioned_excluded(self):
        articles = [make_article("강남구 아파트값 상승세", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "래미안개포1단지", date(2026, 6, 10), date(2026, 7, 10),
        )
        assert result == []

    def test_date_outside_lookback_excluded(self):
        """랭킹 구간(3m/6m)이 아니라 뉴스 배치 자체의 lookback 창을 사용한다."""
        articles = [make_article("래미안개포1단지 시세", date(2026, 1, 1))]
        result = filter_relevant_articles(
            articles, "래미안개포1단지", date(2026, 6, 10), date(2026, 7, 10),
        )
        assert result == []

    def test_no_matching_articles_returns_empty_not_forced(self):
        articles = [make_article("타 단지 뉴스", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "래미안개포1단지", date(2026, 6, 10), date(2026, 7, 10),
        )
        assert result == []

    def test_limit_and_latest_first(self):
        articles = [
            make_article("래미안개포1단지 A", date(2026, 7, 1), link="a"),
            make_article("래미안개포1단지 B", date(2026, 7, 5), link="b"),
            make_article("래미안개포1단지 C", date(2026, 7, 3), link="c"),
            make_article("래미안개포1단지 D", date(2026, 7, 8), link="d"),
        ]
        result = filter_relevant_articles(
            articles, "래미안개포1단지", date(2026, 6, 10), date(2026, 7, 10), limit=3,
        )
        assert len(result) == 3
        assert [a["link"] for a in result] == ["d", "b", "c"]

    def test_generic_brand_name_without_region_excluded(self):
        """자이/래미안류 브랜드 단독명은 also_require_any(지역명) 없이는 오탐 위험 — 필터가 이를 보완."""
        articles = [make_article("전국 자이 브랜드 인기몰이", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "자이", date(2026, 6, 10), date(2026, 7, 10),
            also_require_any=["강남구", "개포동"],
        )
        assert result == []

    def test_generic_brand_name_with_region_passes(self):
        articles = [make_article("강남구 자이 시세 상승", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "자이", date(2026, 6, 10), date(2026, 7, 10),
            also_require_any=["강남구", "개포동"],
        )
        assert len(result) == 1


class TestIsGenericShortName:
    def test_short_brand_name_is_generic(self):
        assert is_generic_short_name("자이") is True
        assert is_generic_short_name("래미안") is True

    def test_specific_complex_name_is_not_generic(self):
        assert is_generic_short_name("래미안개포1단지") is False
        assert is_generic_short_name("개포자이프레지던스") is False

    def test_numeric_suffix_stripped_before_length_check(self):
        """숫자·차수 접미사를 뗀 뒤 길이를 판정 — '자이2차'도 짧은 브랜드명으로 간주."""
        assert is_generic_short_name("자이2차") is True


class TestStripTags:
    def test_strip_bold_tags(self):
        assert _strip_tags("<b>래미안</b> 개포1단지") == "래미안 개포1단지"


class TestParsePubDate:
    def test_valid_rfc822(self):
        assert _parse_pub_date("Fri, 10 Jul 2026 09:00:00 +0900") == date(2026, 7, 10)

    def test_invalid_returns_none(self):
        assert _parse_pub_date("not a date") is None
