"""market breadth 순수 계산 로직 테스트 (DB 없이 검증 가능)."""

from fomobot.services.breadth import classify_breadth, is_excluded_nasdaq_security


class TestClassifyBreadth:
    def test_상승_하락_보합_분류(self):
        pairs = [
            (110.0, 100.0),  # 상승
            (90.0, 100.0),   # 하락
            (100.0, 100.0),  # 보합
        ]
        result = classify_breadth(pairs)
        assert result == {"advancers": 1, "decliners": 1, "unchanged": 1, "excluded": 0}

    def test_전일종가_없으면_excluded(self):
        pairs = [(110.0, None), (90.0, 100.0)]
        result = classify_breadth(pairs)
        assert result == {"advancers": 0, "decliners": 1, "unchanged": 0, "excluded": 1}

    def test_빈_입력(self):
        assert classify_breadth([]) == {
            "advancers": 0, "decliners": 0, "unchanged": 0, "excluded": 0,
        }


class TestIsExcludedNasdaqSecurity:
    def test_warrant_매칭(self):
        assert is_excluded_nasdaq_security("Armada Acquisition Corp. III - Warrant") is True

    def test_rights_매칭(self):
        assert is_excluded_nasdaq_security("Artius II Acquisition Inc. - Rights") is True

    def test_units_매칭(self):
        assert is_excluded_nasdaq_security("Abony Acquisition Corp. I - Units") is True

    def test_단수_unit_매칭(self):
        assert is_excluded_nasdaq_security("Some Corp - Unit") is True

    def test_bright_오탐_방지(self):
        assert is_excluded_nasdaq_security("Bright Health Group, Inc. - Common Stock") is False

    def test_united_오탐_방지(self):
        assert is_excluded_nasdaq_security("United Airlines Holdings, Inc.") is False

    def test_uniti_오탐_방지(self):
        assert is_excluded_nasdaq_security("Uniti Group Inc. - Common Stock") is False

    def test_일반_종목명_매칭_안됨(self):
        assert is_excluded_nasdaq_security("Apple Inc. - Common Stock") is False

    def test_none_이름_False(self):
        assert is_excluded_nasdaq_security(None) is False
