"""
학군 세그먼트 정의.

seg_key → 메타 매핑. dongs는 (sigungu_code, eupmyeondong) 튜플 목록.
sigungu_code를 함께 저장하는 이유: 동 이름이 타 시군구에 중복될 수 있으므로
(sigungu_code, eupmyeondong) 조합으로 정확히 좁힘.

eupmyeondong 표기는 국토부 실거래가 API 법정동 기준.
  - 목1동~목7동은 법정동상 '목동' 하나로 통합됨.
  - 평촌/분당서현은 regions.py에 포함되어 있으나 수집 배치 미실행 상태.
    세그먼트 정의는 유지하고, 수집 후 자동 표시됨.
"""

from typing import TypedDict


class SegmentDef(TypedDict):
    label: str           # 프론트 표시명 (한글)
    description: str     # 소속 시/구 (셀렉트 보조 텍스트)
    dongs: list[tuple[str, str]]  # [(sigungu_code, eupmyeondong), ...]


SEGMENTS: dict[str, SegmentDef] = {
    "목동": {
        "label": "목동",
        "description": "서울 양천구",
        "dongs": [
            ("11470", "목동"),
            ("11470", "신정동"),
        ],
    },
    "대치": {
        "label": "대치",
        "description": "서울 강남구",
        "dongs": [
            ("11680", "대치동"),
            ("11680", "도곡동"),
        ],
    },
    "평촌": {
        "label": "평촌",
        "description": "경기 안양시 동안구",
        "dongs": [
            ("41173", "평촌동"),
            ("41173", "귀인동"),
        ],
    },
    "중계": {
        "label": "중계",
        "description": "서울 노원구",
        "dongs": [
            ("11350", "중계동"),
        ],
    },
    "분당서현": {
        "label": "분당 서현",
        "description": "경기 성남시 분당구",
        "dongs": [
            ("41135", "서현동"),
            ("41135", "수내동"),
        ],
    },
}
