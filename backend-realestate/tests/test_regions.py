"""
수도권 시군구 코드표 / 중복 지역명 판정 단위 테스트.

'중구'처럼 여러 시/도에 동시 존재하는 지역명을 데이터 기반(시/도 간 이름
중복 집계) + 방위구 패턴(중/동/서/남/북+구)으로 판정하는 로직을 검증한다.
"""

from realestate.batch.regions import (
    DUPLICATE_GU_NAMES,
    SIDO_NAME_VARIANTS,
    _find_cross_sido_duplicates,
    get_sido,
)


class TestFindCrossSidoDuplicates:
    def test_name_in_two_sido_is_duplicate(self):
        pairs = [("11140", "중구"), ("28110", "중구")]
        assert _find_cross_sido_duplicates(pairs) == {"중구"}

    def test_name_in_single_sido_is_not_duplicate(self):
        pairs = [("11680", "강남구")]
        assert _find_cross_sido_duplicates(pairs) == set()

    def test_unknown_code_ignored(self):
        """SIGUNGU_MAP에 없는 코드(sido 조회 불가)는 집계에서 제외한다."""
        pairs = [("99999", "가상구")]
        assert _find_cross_sido_duplicates(pairs) == set()


class TestDuplicateGuNames:
    def test_includes_data_driven_duplicate(self):
        """중구는 서울/인천 모두에 실제로 존재 — 데이터 기반으로 잡힘."""
        assert "중구" in DUPLICATE_GU_NAMES

    def test_includes_directional_pattern_names(self):
        """서구/동구는 인천에만 있어도 방위구 패턴이라 포함된다."""
        assert "서구" in DUPLICATE_GU_NAMES
        assert "동구" in DUPLICATE_GU_NAMES

    def test_unique_names_excluded(self):
        assert "강남구" not in DUPLICATE_GU_NAMES
        assert "송파구" not in DUPLICATE_GU_NAMES

    def test_directional_compound_name_excluded(self):
        """남동구처럼 방위 문자 2개 이상 복합명은 전국적으로 드물어 패턴에서 제외한다."""
        assert "남동구" not in DUPLICATE_GU_NAMES


class TestSidoNameVariants:
    def test_seoul_variants(self):
        assert set(SIDO_NAME_VARIANTS["서울"]) == {"서울", "서울시", "서울특별시"}

    def test_covers_all_collected_sido(self):
        assert set(SIDO_NAME_VARIANTS.keys()) == {"서울", "인천", "경기"}


class TestGetSido:
    def test_known_code(self):
        assert get_sido("11140") == "서울"
        assert get_sido("28110") == "인천"

    def test_unknown_code_returns_none(self):
        assert get_sido("99999") is None
