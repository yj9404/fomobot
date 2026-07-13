"""
시장 breadth(상승/하락/보합 종목 수) 순수 계산 로직.

DB I/O는 batch/compute_breadth.py가 담당하고, 이 모듈은 입력을 받아
분류만 수행하는 순수 함수만 둔다 (DB 없이 단위 테스트 가능).
"""

import re

# SPAC 부속증권류 판정 패턴 — 단어 경계 매칭으로 "Bright", "United", "Uniti" 등의
# 부분 문자열 오탐을 방지한다. 대소문자 무시.
_NASDAQ_EXCLUDE_PATTERN = re.compile(r"\b(warrants?|rights?|units?)\b", re.IGNORECASE)


def is_excluded_nasdaq_security(name: str | None) -> bool:
    """종목명에 Warrant/Right(s)/Unit(s)가 단어 단위로 포함되면 True (SPAC 부속증권 추정)."""
    if not name:
        return False
    return bool(_NASDAQ_EXCLUDE_PATTERN.search(name))


def classify_breadth(pairs: list[tuple[float, float | None]]) -> dict[str, int]:
    """
    (당일 종가, 전일 종가) 페어 목록을 상승/하락/보합/제외로 분류한다.

    전일 종가가 None이면 excluded로 카운트한다(신규상장 등 전일 데이터가
    아예 없는 경우 — LAG 윈도우 함수를 쓰면 결측일 건너뛰고 그 이전 종가와
    비교해버리는 오류가 나므로, 명시적으로 "전일 종가 없음"을 구분한다).
    """
    advancers = decliners = unchanged = excluded = 0
    for close_curr, close_prev in pairs:
        if close_prev is None:
            excluded += 1
        elif close_curr > close_prev:
            advancers += 1
        elif close_curr < close_prev:
            decliners += 1
        else:
            unchanged += 1
    return {
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "excluded": excluded,
    }
