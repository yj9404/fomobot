"""단지 식별·정규화 테스트."""

import pytest

from realestate.batch.normalize import make_complex_key, normalize_apt_name


class TestNormalizeAptName:
    def test_whitespace_variants(self):
        """공백 차이는 같은 단지로 병합된다."""
        assert normalize_apt_name("래미안 강남") == normalize_apt_name("래미안강남")
        assert normalize_apt_name("힐스테이트 1단지") == normalize_apt_name("힐스테이트1단지")
        assert normalize_apt_name("GS 자이") == normalize_apt_name("GS자이")

    def test_fullwidth_normalization(self):
        """전각 숫자는 반각으로 통일된다."""
        assert normalize_apt_name("힐스테이트１단지") == normalize_apt_name("힐스테이트1단지")
        assert normalize_apt_name("래미안２차") == normalize_apt_name("래미안2차")

    def test_punctuation_removal(self):
        """하이픈·중점 등 구두점은 제거된다."""
        assert normalize_apt_name("현대-아파트") == normalize_apt_name("현대아파트")
        assert normalize_apt_name("롯데·캐슬") == normalize_apt_name("롯데캐슬")

    def test_multiple_spaces(self):
        """연속 공백도 모두 제거된다."""
        assert normalize_apt_name("래미안  강남") == normalize_apt_name("래미안강남")

    def test_no_change_for_plain_name(self):
        """변형이 없는 이름은 그대로 반환된다."""
        assert normalize_apt_name("아이파크") == "아이파크"

    def test_typo_not_merged(self):
        """오타(레미안 vs 래미안)는 다른 단지로 구분된다."""
        assert normalize_apt_name("레미안강남") != normalize_apt_name("래미안강남")


class TestMakeComplexKey:
    def test_same_inputs_same_key(self):
        """동일 입력은 항상 같은 키를 반환한다."""
        k1 = make_complex_key("11680", "개포동", "래미안개포1단지")
        k2 = make_complex_key("11680", "개포동", "래미안개포1단지")
        assert k1 == k2

    def test_different_dong_different_key(self):
        """같은 아파트명이라도 동이 다르면 별개 단지다."""
        k1 = make_complex_key("11680", "개포동", "현대아파트")
        k2 = make_complex_key("11680", "일원동", "현대아파트")
        assert k1 != k2

    def test_different_sigungu_different_key(self):
        """같은 아파트명이라도 시군구가 다르면 별개 단지다."""
        k1 = make_complex_key("11680", "개포동", "래미안")
        k2 = make_complex_key("41135", "개포동", "래미안")
        assert k1 != k2

    def test_key_is_40_hex_chars(self):
        """키는 SHA-1 hex 40자다."""
        key = make_complex_key("11680", "개포동", "래미안개포1단지")
        assert len(key) == 40
        assert all(c in "0123456789abcdef" for c in key)

    def test_normalized_name_matches(self):
        """공백 표기가 달라도 정규화 후 같은 키를 생성한다."""
        from realestate.batch.normalize import normalize_apt_name

        raw_a = "래미안 개포 1단지"
        raw_b = "래미안개포1단지"
        norm_a = normalize_apt_name(raw_a)
        norm_b = normalize_apt_name(raw_b)
        k1 = make_complex_key("11680", "개포동", norm_a)
        k2 = make_complex_key("11680", "개포동", norm_b)
        assert k1 == k2
