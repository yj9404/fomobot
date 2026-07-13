"""
수도권 시군구 코드 목록.

법정동코드 5자리 기준 (국토부 실거래가 API 파라미터 단위).
시도코드: 11=서울, 28=인천, 41=경기

PublicDataReader의 코드 조회 기능(pdr.code_bdong())으로 갱신할 수 있으나,
코드 변경이 드물고 런타임 의존성을 최소화하기 위해 하드코딩한다.
"""

import re
from typing import Iterable

SUDOGWON_SIGUNGU: list[dict[str, str]] = [
    # 서울특별시 (25개 구)
    {"code": "11110", "name": "종로구", "sido": "서울"},
    {"code": "11140", "name": "중구", "sido": "서울"},
    {"code": "11170", "name": "용산구", "sido": "서울"},
    {"code": "11200", "name": "성동구", "sido": "서울"},
    {"code": "11215", "name": "광진구", "sido": "서울"},
    {"code": "11230", "name": "동대문구", "sido": "서울"},
    {"code": "11260", "name": "중랑구", "sido": "서울"},
    {"code": "11290", "name": "성북구", "sido": "서울"},
    {"code": "11305", "name": "강북구", "sido": "서울"},
    {"code": "11320", "name": "도봉구", "sido": "서울"},
    {"code": "11350", "name": "노원구", "sido": "서울"},
    {"code": "11380", "name": "은평구", "sido": "서울"},
    {"code": "11410", "name": "서대문구", "sido": "서울"},
    {"code": "11440", "name": "마포구", "sido": "서울"},
    {"code": "11470", "name": "양천구", "sido": "서울"},
    {"code": "11500", "name": "강서구", "sido": "서울"},
    {"code": "11530", "name": "구로구", "sido": "서울"},
    {"code": "11545", "name": "금천구", "sido": "서울"},
    {"code": "11560", "name": "영등포구", "sido": "서울"},
    {"code": "11590", "name": "동작구", "sido": "서울"},
    {"code": "11620", "name": "관악구", "sido": "서울"},
    {"code": "11650", "name": "서초구", "sido": "서울"},
    {"code": "11680", "name": "강남구", "sido": "서울"},
    {"code": "11710", "name": "송파구", "sido": "서울"},
    {"code": "11740", "name": "강동구", "sido": "서울"},
    # 인천광역시 (10개 구/군)
    {"code": "28110", "name": "중구", "sido": "인천"},
    {"code": "28140", "name": "동구", "sido": "인천"},
    {"code": "28177", "name": "미추홀구", "sido": "인천"},
    {"code": "28185", "name": "연수구", "sido": "인천"},
    {"code": "28200", "name": "남동구", "sido": "인천"},
    {"code": "28237", "name": "부평구", "sido": "인천"},
    {"code": "28245", "name": "계양구", "sido": "인천"},
    {"code": "28260", "name": "서구", "sido": "인천"},
    {"code": "28710", "name": "강화군", "sido": "인천"},
    {"code": "28720", "name": "옹진군", "sido": "인천"},
    # 경기도 — 구 단위로 분리된 시
    {"code": "41111", "name": "수원 장안구", "sido": "경기"},
    {"code": "41113", "name": "수원 권선구", "sido": "경기"},
    {"code": "41115", "name": "수원 팔달구", "sido": "경기"},
    {"code": "41117", "name": "수원 영통구", "sido": "경기"},
    {"code": "41131", "name": "성남 수정구", "sido": "경기"},
    {"code": "41133", "name": "성남 중원구", "sido": "경기"},
    {"code": "41135", "name": "성남 분당구", "sido": "경기"},
    {"code": "41171", "name": "안양 만안구", "sido": "경기"},
    {"code": "41173", "name": "안양 동안구", "sido": "경기"},
    {"code": "41271", "name": "안산 상록구", "sido": "경기"},
    {"code": "41273", "name": "안산 단원구", "sido": "경기"},
    {"code": "41281", "name": "고양 덕양구", "sido": "경기"},
    {"code": "41285", "name": "고양 일산동구", "sido": "경기"},
    {"code": "41287", "name": "고양 일산서구", "sido": "경기"},
    {"code": "41461", "name": "용인 처인구", "sido": "경기"},
    {"code": "41463", "name": "용인 기흥구", "sido": "경기"},
    {"code": "41465", "name": "용인 수지구", "sido": "경기"},
    # 경기도 — 단일 시/군
    {"code": "41150", "name": "의정부시", "sido": "경기"},
    {"code": "41190", "name": "부천시", "sido": "경기"},
    {"code": "41210", "name": "광명시", "sido": "경기"},
    {"code": "41220", "name": "평택시", "sido": "경기"},
    {"code": "41250", "name": "동두천시", "sido": "경기"},
    {"code": "41290", "name": "과천시", "sido": "경기"},
    {"code": "41310", "name": "구리시", "sido": "경기"},
    {"code": "41360", "name": "남양주시", "sido": "경기"},
    {"code": "41370", "name": "오산시", "sido": "경기"},
    {"code": "41390", "name": "시흥시", "sido": "경기"},
    {"code": "41410", "name": "군포시", "sido": "경기"},
    {"code": "41430", "name": "의왕시", "sido": "경기"},
    {"code": "41450", "name": "하남시", "sido": "경기"},
    {"code": "41480", "name": "파주시", "sido": "경기"},
    {"code": "41500", "name": "이천시", "sido": "경기"},
    {"code": "41550", "name": "안성시", "sido": "경기"},
    {"code": "41570", "name": "김포시", "sido": "경기"},
    {"code": "41590", "name": "화성시", "sido": "경기"},
    {"code": "41610", "name": "광주시", "sido": "경기"},
    {"code": "41630", "name": "양주시", "sido": "경기"},
    {"code": "41650", "name": "포천시", "sido": "경기"},
    {"code": "41670", "name": "여주시", "sido": "경기"},
    {"code": "41800", "name": "연천군", "sido": "경기"},
    {"code": "41820", "name": "가평군", "sido": "경기"},
    {"code": "41830", "name": "양평군", "sido": "경기"},
]

# 코드 → (name, sido) 빠른 조회
SIGUNGU_MAP: dict[str, dict[str, str]] = {r["code"]: r for r in SUDOGWON_SIGUNGU}


def get_display_name(sigungu_code: str, sigungu_name: str, eupmyeondong: str | None = None) -> str:
    sido = SIGUNGU_MAP.get(sigungu_code, {}).get("sido", "")
    if eupmyeondong:
        return f"{sigungu_name} {eupmyeondong}"
    return f"{sido} {sigungu_name}".strip()


def get_sido(sigungu_code: str) -> str | None:
    """시군구 코드로 시/도("서울"/"인천"/"경기")를 조회한다."""
    return SIGUNGU_MAP.get(sigungu_code, {}).get("sido")


# 뉴스 제목에서 시/도를 지칭할 때 쓰이는 표기 변형. 수도권 3개뿐이라 안정적인
# 국가 행정구역 상수로 취급한다(뉴스 매칭용 브랜드/토픽 사전과는 성격이 다름).
SIDO_NAME_VARIANTS: dict[str, list[str]] = {
    "서울": ["서울", "서울시", "서울특별시"],
    "인천": ["인천", "인천시", "인천광역시"],
    "경기": ["경기", "경기도"],
}

# 방위 문자 하나 + "구"로만 이뤄진 이름 패턴(중구/동구/서구/남구/북구) — 대구·
# 광주·대전·울산 등 우리 데이터셋 밖 도시에도 전국적으로 흔히 재사용되는
# 구조라, 특정 지역명을 나열한 사전이 아니라 한글 구조 규칙으로 취급한다.
# 방위 문자 2개 이상의 복합명(예: 남동구)은 전국적으로 드물어 제외한다.
_DIRECTIONAL_GU_RE = re.compile(r"^[동서남북중]구$")


def _find_cross_sido_duplicates(pairs: Iterable[tuple[str, str]]) -> set[str]:
    """
    (sigungu_code, name) 목록에서 name이 2개 이상 서로 다른 시/도에 걸쳐
    등장하면 "중복 지역명"으로 판정한다(뉴스 관련성 필터에서 시/도 동시
    확인이 필요한지 결정하는 데 사용).
    """
    name_to_sidos: dict[str, set[str]] = {}
    for code, name in pairs:
        sido = get_sido(code)
        if sido:
            name_to_sidos.setdefault(name, set()).add(sido)
    return {name for name, sidos in name_to_sidos.items() if len(sidos) > 1}


def _compute_duplicate_gu_names() -> set[str]:
    data_driven = _find_cross_sido_duplicates((r["code"], r["name"]) for r in SUDOGWON_SIGUNGU)
    pattern_driven = {r["name"] for r in SUDOGWON_SIGUNGU if _DIRECTIONAL_GU_RE.match(r["name"])}
    return data_driven | pattern_driven


# 구 단위 뉴스 폴백 검색에서 시/도를 함께 요구해야 하는 "동명 위험" 구 이름 집합.
# 예: 중구(서울+인천 중복 데이터) / 서구·동구(인천에만 있지만 방위구 패턴이라 포함).
DUPLICATE_GU_NAMES: set[str] = _compute_duplicate_gu_names()
