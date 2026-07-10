"""
뉴스 관련성 필터 단위 테스트.

LLM 없이 "제목 직접 언급 + 날짜 구간 내" 규칙만으로 관련성을 판정하는
filter_relevant_articles가 정확히 동작하는지 검증한다(네트워크·DB 의존 없음).
"""

from datetime import date

from fomobot.services.naver_news import _parse_pub_date, _strip_tags, filter_relevant_articles


def make_article(title: str, published_at: date, link: str = "https://example.com/a") -> dict:
    return {"title": title, "link": link, "published_at": published_at}


class TestFilterRelevantArticles:
    def test_title_and_window_match_passes(self):
        articles = [make_article("삼성전자 주가 급등", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "삼성전자", date(2026, 7, 1), date(2026, 7, 10),
        )
        assert len(result) == 1

    def test_title_not_mentioned_excluded(self):
        """제목에 종목명이 없는 기사는 억지 매칭하지 않고 제외한다."""
        articles = [make_article("코스피 지수 상승 마감", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "삼성전자", date(2026, 7, 1), date(2026, 7, 10),
        )
        assert result == []

    def test_date_outside_window_excluded(self):
        articles = [make_article("삼성전자 주가 급등", date(2026, 6, 1))]
        result = filter_relevant_articles(
            articles, "삼성전자", date(2026, 7, 1), date(2026, 7, 10),
        )
        assert result == []

    def test_boundary_dates_inclusive(self):
        articles = [
            make_article("삼성전자 주가", date(2026, 7, 1)),
            make_article("삼성전자 주가", date(2026, 7, 10)),
        ]
        result = filter_relevant_articles(
            articles, "삼성전자", date(2026, 7, 1), date(2026, 7, 10),
        )
        assert len(result) == 2

    def test_no_matching_articles_returns_empty_not_forced(self):
        """조건 충족 기사가 없으면 빈 상태 — 아무거나 채워넣지 않는다."""
        articles = [
            make_article("타 종목 뉴스", date(2026, 7, 5)),
            make_article("삼성전자 지난달 실적", date(2026, 1, 1)),
        ]
        result = filter_relevant_articles(
            articles, "삼성전자", date(2026, 7, 1), date(2026, 7, 10),
        )
        assert result == []

    def test_limit_and_latest_first(self):
        """조건 충족분이 3개 넘으면 최신순 최대 3개만 반환한다."""
        articles = [
            make_article("삼성전자 주가 A", date(2026, 7, 1), link="a"),
            make_article("삼성전자 주가 B", date(2026, 7, 5), link="b"),
            make_article("삼성전자 주가 C", date(2026, 7, 3), link="c"),
            make_article("삼성전자 주가 D", date(2026, 7, 8), link="d"),
        ]
        result = filter_relevant_articles(
            articles, "삼성전자", date(2026, 7, 1), date(2026, 7, 10), limit=3,
        )
        assert len(result) == 3
        assert [a["link"] for a in result] == ["d", "b", "c"]

    def test_also_require_any_blocks_when_absent(self):
        """also_require_any 지정 시 그중 하나도 제목에 있어야 통과(동명 단지류 보완)."""
        articles = [make_article("자이 분양 소식", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "자이", date(2026, 7, 1), date(2026, 7, 10),
            also_require_any=["강남구", "개포동"],
        )
        assert result == []

    def test_also_require_any_passes_when_present(self):
        articles = [make_article("강남구 자이 재건축 이슈", date(2026, 7, 5))]
        result = filter_relevant_articles(
            articles, "자이", date(2026, 7, 1), date(2026, 7, 10),
            also_require_any=["강남구", "개포동"],
        )
        assert len(result) == 1

    def test_empty_input(self):
        assert filter_relevant_articles([], "삼성전자", date(2026, 7, 1), date(2026, 7, 10)) == []


class TestStripTags:
    def test_strip_bold_tags(self):
        assert _strip_tags("<b>삼성전자</b> 주가 급등") == "삼성전자 주가 급등"

    def test_no_tags_unchanged(self):
        assert _strip_tags("삼성전자 주가 급등") == "삼성전자 주가 급등"


class TestParsePubDate:
    def test_valid_rfc822(self):
        assert _parse_pub_date("Fri, 10 Jul 2026 09:00:00 +0900") == date(2026, 7, 10)

    def test_invalid_returns_none(self):
        assert _parse_pub_date("not a date") is None

    def test_empty_returns_none(self):
        assert _parse_pub_date("") is None
