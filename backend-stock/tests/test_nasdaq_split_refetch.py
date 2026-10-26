"""역분할 재수집 정정 판정(plan_refetch)과 적용(apply_refetch) 테스트."""

from contextlib import nullcontext
from datetime import date, timedelta

from fomobot.batch import nasdaq_split_refetch as m

FLAG = date(2026, 10, 14)
SPLIT = (date(2026, 10, 21), 0.2)


def _rows(closes: dict[date, float]) -> list[dict]:
    return [{"ticker": "EHGO", "market": "nasdaq", "date": d, "open": c, "high": c, "low": c,
             "close_adj": c, "volume": 1000, "market_cap": None} for d, c in sorted(closes.items())]


def _series(days=30, level=2.8, shift_at=None, shift_to=None):
    """FLAG 앞뒤로 매일 level 근처인 시계열. shift_at 이후는 shift_to 수준."""
    start = FLAG - timedelta(days=days // 2)
    out = {}
    for i in range(days):
        d = start + timedelta(days=i)
        out[d] = shift_to if (shift_at and d >= shift_at) else level
    return out


class TestFindCliffs:
    def test_평탄하면_없음(self):
        assert m.find_cliffs(_rows(_series())) == []

    def test_3배_초과_점프를_찾음(self):
        cliffs = m.find_cliffs(_rows(_series(level=0.64, shift_at=FLAG, shift_to=2.87)))
        assert [(c["date"], round(c["ratio"], 2)) for c in cliffs] == [(FLAG, 4.48)]


class TestPlanRefetch:
    def test_분할_확인되고_절벽_해소되면_fixable(self):
        plan = m.plan_refetch("EHGO", FLAG, [SPLIT], _rows(_series()))
        assert plan["category"] == "fixable"
        assert plan["split_date"] == SPLIT[0] and plan["split_ratio"] == SPLIT[1]

    def test_분할_이력_없거나_조회_실패면_hold(self):
        for splits in (None, []):
            plan = m.plan_refetch("EHGO", FLAG, splits, _rows(_series()))
            assert plan["category"] == "hold" and "미확인" in plan["reason"]

    def test_정방향_분할이나_창_밖_분할은_불인정(self):
        for splits in ([(date(2026, 10, 21), 5.0)], [(date(2026, 11, 20), 0.2)], [(date(2026, 9, 1), 0.2)]):
            assert m.plan_refetch("EHGO", FLAG, splits, _rows(_series()))["category"] == "hold"

    def test_재수집_후에도_절벽이_남으면_hold(self):
        rows = _rows(_series(level=0.64, shift_at=FLAG, shift_to=2.87))
        plan = m.plan_refetch("EHGO", FLAG, [SPLIT], rows)
        assert plan["category"] == "hold" and "절벽 잔존" in plan["reason"]

    def test_정정_구간_밖의_절벽은_남아도_fixable이고_목록으로_알림(self):
        closes = _series(days=60)
        far = FLAG - timedelta(days=25)
        closes = {d: (10.0 if d >= far else 1.0) for d in closes}  # far 이후 x10 (flag_date와 25일 차)
        plan = m.plan_refetch("EHGO", FLAG, [SPLIT], _rows(closes))
        assert plan["category"] == "fixable"
        assert [c["date"] for c in plan["remaining_cliffs"]] == [far]

    def test_DB_종가와_재수집_값이_크게_다르면_hold(self):
        rows = _rows(_series(level=2.8))
        db = {d: 1.0 for d in _series(level=2.8) if d >= FLAG}
        plan = m.plan_refetch("EHGO", FLAG, [SPLIT], rows, db)
        assert plan["category"] == "hold" and "불일치" in plan["reason"]

    def test_DB_종가가_비슷하면_통과(self):
        db = {d: 2.79 for d in _series(level=2.8) if d >= FLAG}
        plan = m.plan_refetch("EHGO", FLAG, [SPLIT], _rows(_series(level=2.8)), db)
        assert plan["category"] == "fixable" and plan["db_mismatch"] < 0.01

    def test_절벽_앞뒤_행이_부족하면_hold(self):
        # 1행뿐인 응답은 절벽 검사가 공허하게 통과하므로 정정 대상이 아니다
        plan = m.plan_refetch("EHGO", FLAG, [SPLIT], _rows({FLAG + timedelta(days=1): 2.8}))
        assert plan["category"] == "hold" and "행 부족" in plan["reason"]

    def test_재수집_이력이_DB보다_짧으면_hold(self):
        rows = _rows(_series())  # 첫 행은 FLAG-15일
        short = m.plan_refetch("EHGO", FLAG, [SPLIT], rows, first_date=FLAG - timedelta(days=400))
        assert short["category"] == "hold" and "짧음" in short["reason"]
        ok = m.plan_refetch("EHGO", FLAG, [SPLIT], rows, first_date=FLAG - timedelta(days=15))
        assert ok["category"] == "fixable"

    def test_재수집_응답이_비면_hold(self):
        assert m.plan_refetch("EHGO", FLAG, [SPLIT], [])["category"] == "hold"


# 2026-10 DB 실제 값: 원본 미조정, 분할일에 절벽 (BTLN 1:8)
BTLN_ROWS = [{"date": date(2026, 9, 24), "close_adj": 0.650}, {"date": date(2026, 9, 25), "close_adj": 0.640},
             {"date": date(2026, 9, 28), "close_adj": 5.250}, {"date": date(2026, 9, 29), "close_adj": 4.550}]
BTLN_SPLIT = [(date(2026, 9, 28), 0.125)]


class TestPlanScale:
    def test_분할과_배율이_맞으면_scalable(self):
        plan = m.plan_scale("BTLN", date(2026, 9, 28), BTLN_SPLIT, BTLN_ROWS)
        assert plan["category"] == "scalable"
        assert plan["cliff_date"] == date(2026, 9, 28) and plan["factor"] == 8.0
        assert 0.9 < plan["magnitude"] < 1.1

    def test_분할_이력_없거나_조회_실패면_hold(self):
        for splits in (None, []):
            assert m.plan_scale("BTLN", date(2026, 9, 28), splits, BTLN_ROWS)["category"] == "hold"

    def test_배율이_범위_밖이면_hold(self):
        # 점프 x8.2에 분할 1:3(기대 x3)이면 분할 외 요인이 섞인 것
        plan = m.plan_scale("BTLN", date(2026, 9, 28), [(date(2026, 9, 28), 1 / 3)], BTLN_ROWS)
        assert plan["category"] == "hold" and "맞는 역분할 미확인" in plan["reason"]

    def test_상승_절벽이_없으면_hold(self):
        flat = [{"date": date(2026, 9, 24) + timedelta(days=i), "close_adj": 1.0} for i in range(5)]
        assert m.plan_scale("X", date(2026, 9, 26), BTLN_SPLIT, flat)["category"] == "hold"

    def test_하락_절벽은_대상_아님(self):
        down = [{"date": date(2026, 9, 25), "close_adj": 5.0}, {"date": date(2026, 9, 28), "close_adj": 0.6}]
        assert m.plan_scale("X", date(2026, 9, 28), [(date(2026, 9, 28), 8.0)], down)["category"] == "hold"


class _FakeSession:
    def __init__(self, jump_rows, log):
        self.jump_rows, self.log = jump_rows, log

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, stmt, params=None):
        sql = str(stmt)
        self.log.append((sql, params))

        class R:
            rowcount = 1200

            def fetchall(_):
                return self.jump_rows

        return R()


class TestApplyScale:
    def _run(self, monkeypatch, jump_rows):
        log, flags = [], []
        monkeypatch.setattr(m, "SyncSessionLocal", lambda: _FakeSession(jump_rows, log))
        monkeypatch.setattr(m, "upsert_corporate_action_flag_sync", lambda s, recs: flags.extend(recs))
        plan = m.plan_scale("BTLN", date(2026, 9, 28), BTLN_SPLIT, BTLN_ROWS)
        m.apply_scale([plan, m.plan_scale("XXXX", date(2026, 9, 28), None, BTLN_ROWS)])
        updates = [(s, p) for s, p in log if s.startswith("UPDATE")]
        return updates, flags

    def test_점프가_그대로면_환산하고_flag_resolved(self, monkeypatch):
        rows = [(date(2026, 9, 28), 5.25), (date(2026, 9, 25), 0.64)]
        updates, flags = self._run(monkeypatch, rows)
        (sql, params), = updates
        assert params["f"] == 8.0 and params["d"] == date(2026, 9, 28) and "date < :d" in sql
        assert "volume / :f" in sql  # 가격은 ×F, 거래량은 ÷F
        rec, = flags
        assert (rec["ticker"], rec["status"]) == ("BTLN", "resolved")
        assert "×8" in rec["note"]

    def test_이미_환산돼_점프가_사라졌으면_건너뜀(self, monkeypatch):
        rows = [(date(2026, 9, 28), 5.25), (date(2026, 9, 25), 5.12)]  # 점프 x1.03
        updates, flags = self._run(monkeypatch, rows)
        assert updates == [] and flags == []

    def test_절벽일_행이_없으면_건너뜀(self, monkeypatch):
        updates, flags = self._run(monkeypatch, [(date(2026, 9, 25), 0.64)])
        assert updates == [] and flags == []


class TestApplyRefetch:
    def test_fixable만_쓰고_flag를_resolved로(self, monkeypatch):
        prices, flags = [], []
        monkeypatch.setattr(m, "SyncSessionLocal", lambda: nullcontext())
        monkeypatch.setattr(m, "upsert_price_daily_sync", lambda s, recs, commit=True: prices.append((len(recs), commit)))
        monkeypatch.setattr(m, "upsert_corporate_action_flag_sync", lambda s, recs: flags.extend(recs))

        rows = _rows(_series())
        ok = m.plan_refetch("EHGO", FLAG, [SPLIT], rows)
        bad = m.plan_refetch("XXXX", FLAG, None, rows)
        m.apply_refetch([ok, bad], {"EHGO": rows})

        assert prices == [(len(rows), False)]  # 가격은 flag와 같은 트랜잭션에서 커밋
        rec, = flags
        assert (rec["ticker"], rec["status"], rec["reason"], rec["flag_date"]) == ("EHGO", "resolved", "split", FLAG)
