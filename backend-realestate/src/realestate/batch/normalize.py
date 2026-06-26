"""
아파트 단지 식별·정규화.

정규화 규칙:
 1. NFKC 유니코드 정규화 (전각 → 반각, 합성 문자 정규화)
 2. 공백·하이픈·구두점 모두 제거
 → 같은 단지의 표기 흔들림(띄어쓰기, 전각 숫자 등)을 하나로 병합

알려진 한계:
 - 오타(래미안 ↔ 레미안)는 병합 불가
 - 리모델링 후 이름 변경은 별개 단지로 처리
 - 같은 동에 완전히 동일한 이름의 단지가 여럿이면 잘못 병합될 수 있음
   (거래 데이터에 지번·도로명 정보가 없을 경우 불가피)
"""

import hashlib
import re
import unicodedata


def normalize_apt_name(raw: str) -> str:
    """아파트명 정규화 — 공백·구두점 제거, 전각→반각 변환."""
    s = unicodedata.normalize("NFKC", raw)
    s = re.sub(r"[\s\-·•]+", "", s)
    return s.strip()


def make_complex_key(sigungu_code: str, eupmyeondong: str, apt_name_norm: str) -> str:
    """단지 고유 키 (SHA-1 hex 40자).

    동일 단지를 항상 같은 키로 식별한다.
    key = SHA1(sigungu_code|eupmyeondong|apt_name_norm)
    """
    composite = f"{sigungu_code}|{eupmyeondong}|{apt_name_norm}"
    return hashlib.sha1(composite.encode("utf-8")).hexdigest()
