"""
NASDAQ 상장 디렉토리(nasdaqlisted.txt) 해석용 순수 함수.

수집 배치(collect_nasdaq)와 랭킹 배치(compute_rankings)가 같은 파일을 각자
읽으므로, 티커/종목명 해석 규칙은 여기 한 곳에 둔다.
"""

import re

# 종목명 끝에 남은 when-issued 표기. 거래소 디렉토리가 정규 거래 전환 후에도
# 갱신하지 않는 경우가 있다(2026-10 확인: CEG, SNDK 정식 티커 이름에 잔존).
# 표기가 "When-Issued"/"When Issued"로 섞여 있고, 분사 모회사는
# "Ex-Distribution When Issued"로 나온다.
_WHEN_ISSUED_NAME_SUFFIX = re.compile(
    r"\s*(?:ex-distribution\s+)?when[- ]issued\s*$", re.IGNORECASE
)


def is_when_issued_symbol(ticker: str) -> bool:
    """
    NASDAQ 5자리 심볼의 5번째 글자 V = when-issued/when-distributed.

    4자리 티커는 V로 끝나도 정상 종목(CRWV, FFIV, VIAV 등)이므로 5자리만 본다.
    종목명에 표기가 없는 WI도 있어서(SKHYV) 이름이 아니라 심볼로 판정한다.
    """
    return len(ticker) == 5 and ticker.endswith("V")


def normalize_security_name(name: str) -> str:
    """종목명 끝의 when-issued 표기를 제거한다 (정식 티커에 남은 잔존 표기 정리용)."""
    return _WHEN_ISSUED_NAME_SUFFIX.sub("", name).strip()
