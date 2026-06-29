"""
검색 기능 단위 테스트.

DB 연결 없이 순수 로직만 검증한다.
- normalize_apt_name 기반 검색 쿼리 정규화
- 지역 ILIKE 필터 시뮬레이션
- 아파트 없음 / 스냅샷 없음 / 데이터 부족 세 가지 상태 구분 로직
"""

import pytest

from realestate.batch.normalize import normalize_apt_name


# ── 검색 쿼리 정규화 ────────────────────────────────────────────────────────

class TestSearchQueryNormalization:
    """검색어에 normalize_apt_name을 적용하면 DB의 apt_name_norm과 부분일치가 성립하는지."""

    def test_공백_포함_검색어가_정규화_후_매칭됨(self):
        """사용자가 '래미안 개포 1단지' 입력 → 정규화 후 'apt_name_norm'에서 부분일치."""
        q_norm = normalize_apt_name("래미안 개포 1단지")
        stored_norm = normalize_apt_name("래미안개포1단지")
        assert q_norm in stored_norm

    def test_하이픈_포함_검색어(self):
        """'힐스테이트-1단지' → 정규화 후 '힐스테이트1단지'와 매칭."""
        q_norm = normalize_apt_name("힐스테이트-1단지")
        stored_norm = normalize_apt_name("힐스테이트1단지")
        assert q_norm == stored_norm

    def test_전각_숫자_검색어(self):
        """전각 숫자가 포함된 검색어도 정규화 후 반각과 동일."""
        q_norm = normalize_apt_name("래미안２차")
        stored_norm = normalize_apt_name("래미안2차")
        assert q_norm == stored_norm

    def test_부분_검색어_포함_여부(self):
        """단어 일부만 입력해도 정규화된 단지명에 포함됨."""
        q_norm = normalize_apt_name("래미안")
        stored_norm = normalize_apt_name("래미안개포1단지")
        assert q_norm in stored_norm

    def test_없는_단지_검색어_미매칭(self):
        """존재하지 않는 이름은 어떤 norm에도 포함되지 않아야 한다."""
        q_norm = normalize_apt_name("ZZZZZ없는단지")
        stored_norm = normalize_apt_name("래미안개포1단지")
        assert q_norm not in stored_norm


# ── 지역 검색 필터 시뮬레이션 ───────────────────────────────────────────────

class TestRegionSearchFilter:
    """
    DB ILIKE 동작을 Python으로 시뮬레이션.
    sigungu_name ILIKE :q OR eupmyeondong ILIKE :q.
    """

    REGIONS = [
        {"sigungu_code": "11680", "sigungu_name": "강남구", "eupmyeondong": "개포동"},
        {"sigungu_code": "11680", "sigungu_name": "강남구", "eupmyeondong": "대치동"},
        {"sigungu_code": "11650", "sigungu_name": "서초구", "eupmyeondong": "서초동"},
        {"sigungu_code": "11650", "sigungu_name": "서초구", "eupmyeondong": "잠원동"},
        {"sigungu_code": "41135", "sigungu_name": "성남시분당구", "eupmyeondong": "정자동"},
    ]

    def _search(self, q: str) -> list[dict]:
        q_lower = q.lower()
        seen: set[tuple] = set()
        result = []
        for r in self.REGIONS:
            key = (r["sigungu_code"], r["eupmyeondong"])
            if key not in seen and (
                q_lower in r["sigungu_name"].lower()
                or q_lower in r["eupmyeondong"].lower()
            ):
                seen.add(key)
                result.append(r)
        return result

    def test_시군구명_부분일치(self):
        res = self._search("강남")
        codes = [r["eupmyeondong"] for r in res]
        assert "개포동" in codes
        assert "대치동" in codes
        assert "서초동" not in codes

    def test_법정동명_부분일치(self):
        res = self._search("대치")
        codes = [r["eupmyeondong"] for r in res]
        assert "대치동" in codes
        assert "개포동" not in codes

    def test_시군구명과_동명_동시_매칭(self):
        """'서초'는 sigungu_name='서초구'와 eupmyeondong='서초동' 둘 다 매칭."""
        res = self._search("서초")
        codes = [r["eupmyeondong"] for r in res]
        assert "서초동" in codes
        assert "잠원동" in codes  # 서초구에 속함

    def test_없는_지역_빈_결과(self):
        res = self._search("ZZZZZ없는지역")
        assert res == []

    def test_중복_없이_distinct_반환(self):
        """같은 (sigungu_code, eupmyeondong) 쌍이 중복 없이 반환된다."""
        res = self._search("강남")
        keys = [(r["sigungu_code"], r["eupmyeondong"]) for r in res]
        assert len(keys) == len(set(keys))


# ── 아파트 없음 / 스냅샷 없음 / 데이터 부족 구분 ────────────────────────────

# 가상 DB 상태
_STAT = [
    # complex_key: sha1은 실제로 안 쓰고 테스트용 짧은 키 사용
    {"complex_key": "key_ok",          "sigungu_code": "11680", "eupmyeondong": "개포동", "apt_name": "래미안개포1단지",  "apt_name_norm": "래미안개포1단지"},
    {"complex_key": "key_insufficient","sigungu_code": "11680", "eupmyeondong": "개포동", "apt_name": "래미안개포2단지",  "apt_name_norm": "래미안개포2단지"},
    {"complex_key": "key_no_start",    "sigungu_code": "11680", "eupmyeondong": "대치동", "apt_name": "래미안대치팰리스", "apt_name_norm": "래미안대치팰리스"},
    {"complex_key": "key_no_snapshot", "sigungu_code": "11650", "eupmyeondong": "서초동", "apt_name": "서초래미안",       "apt_name_norm": "서초래미안"},
]

_SNAP = {
    "key_ok":           {"complex_key": "key_ok",           "rank": 3,    "change_pct": 8.5,  "data_status": "ok",           "insufficient_reason": None},
    "key_insufficient": {"complex_key": "key_insufficient",  "rank": None, "change_pct": None, "data_status": "insufficient", "insufficient_reason": "종료 윈도우 거래 2건 (최소 3건 필요)"},
    "key_no_start":     {"complex_key": "key_no_start",      "rank": None, "change_pct": None, "data_status": "no_start",     "insufficient_reason": "시작 윈도우 거래 없음"},
    # key_no_snapshot 은 스냅샷 없음
}


def _simulate_merge(stat_rows: list[dict], snap_map: dict, q_norm: str) -> list[dict]:
    """
    search_complexes_async + 엔드포인트 merge 로직을 Python으로 시뮬레이션.
    q_norm이 apt_name_norm에 포함되는 단지만 반환.
    스냅샷이 없으면 data_status='no_snapshot'.
    """
    results = []
    for stat in stat_rows:
        if q_norm not in stat["apt_name_norm"]:
            continue
        snap = snap_map.get(stat["complex_key"])
        if snap:
            results.append({**stat, **snap})
        else:
            results.append({**stat, "rank": None, "change_pct": None, "data_status": "no_snapshot", "insufficient_reason": None})
    return results


class TestSearchDataStatusDistinction:
    """
    아파트 없음 / 스냅샷 없음 / 데이터 부족 세 가지 상태를 올바르게 구분하는지.
    """

    def test_아파트_없음_빈_results(self):
        """검색어가 어떤 apt_name_norm에도 매칭되지 않으면 results=[]."""
        results = _simulate_merge(_STAT, _SNAP, normalize_apt_name("ZZZZZ없는아파트"))
        assert results == []

    def test_스냅샷_없음_no_snapshot_status(self):
        """apt_name_norm 매칭 O, 스냅샷 없음 → data_status='no_snapshot'."""
        results = _simulate_merge(_STAT, _SNAP, normalize_apt_name("서초래미안"))
        assert len(results) == 1
        assert results[0]["data_status"] == "no_snapshot"
        assert results[0]["rank"] is None
        assert results[0]["change_pct"] is None

    def test_데이터_부족_insufficient_status(self):
        """스냅샷 있음 + 거래 부족 → data_status='insufficient', rank=None."""
        results = _simulate_merge(_STAT, _SNAP, normalize_apt_name("래미안개포2단지"))
        assert len(results) == 1
        assert results[0]["data_status"] == "insufficient"
        assert results[0]["rank"] is None
        assert results[0]["insufficient_reason"] is not None

    def test_데이터_정상_ok_status(self):
        """스냅샷 있음 + 데이터 충분 → data_status='ok', rank 값 존재."""
        results = _simulate_merge(_STAT, _SNAP, normalize_apt_name("래미안개포1단지"))
        assert len(results) == 1
        assert results[0]["data_status"] == "ok"
        assert results[0]["rank"] == 3
        assert results[0]["change_pct"] == pytest.approx(8.5)

    def test_no_start_status(self):
        """시작 윈도우 데이터 없음 → data_status='no_start'."""
        results = _simulate_merge(_STAT, _SNAP, normalize_apt_name("래미안대치팰리스"))
        assert len(results) == 1
        assert results[0]["data_status"] == "no_start"
        assert results[0]["rank"] is None

    def test_부분일치_복수_결과_상태_혼재(self):
        """
        '래미안' 검색 시 여러 단지 반환.
        ok / insufficient / no_start / no_snapshot 상태가 모두 포함될 수 있다.
        """
        results = _simulate_merge(_STAT, _SNAP, normalize_apt_name("래미안"))
        statuses = {r["data_status"] for r in results}
        # 래미안이 이름에 포함된 단지: key_ok(ok), key_insufficient, key_no_start, key_no_snapshot
        assert "ok" in statuses
        assert "insufficient" in statuses
        assert "no_start" in statuses
        assert "no_snapshot" in statuses

    def test_no_snapshot과_insufficient는_모두_results에_포함(self):
        """404가 아닌 results 리스트에 모든 상태가 포함되는지."""
        results = _simulate_merge(_STAT, _SNAP, normalize_apt_name("래미안"))
        assert all("data_status" in r for r in results)
        assert all(r.get("rank") is not None or r["data_status"] != "ok" for r in results)

    def test_검색_결과_없음과_스냅샷_없음_구분(self):
        """
        '검색 결과 없음'(results=[])과 '스냅샷 없음'(results에 no_snapshot)은 다르다.
        같은 단지명을 검색할 때 period가 달라 스냅샷 없으면 no_snapshot이지,
        empty list가 아니다.
        """
        # 스냅샷 없는 단지 검색 → results 비지 않음
        results_with_no_snap = _simulate_merge(_STAT, _SNAP, normalize_apt_name("서초래미안"))
        assert len(results_with_no_snap) > 0
        assert results_with_no_snap[0]["data_status"] == "no_snapshot"

        # 아예 없는 이름 검색 → results 비어있음
        results_empty = _simulate_merge(_STAT, _SNAP, normalize_apt_name("ZZZZ없는단지ZZZZ"))
        assert results_empty == []

    def test_띄어쓰기_다른_검색어_동일_단지_매칭(self):
        """'래미안 개포 1단지' (공백 포함) 검색 → 정규화 후 '래미안개포1단지'와 매칭."""
        q_norm = normalize_apt_name("래미안 개포 1단지")
        results = _simulate_merge(_STAT, _SNAP, q_norm)
        assert len(results) == 1
        assert results[0]["complex_key"] == "key_ok"
