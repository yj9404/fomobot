"""
KOSPI 소급 보정(kospi_price_adjust)과 KRX 원 종가 수집(collect_kospi) 테스트.

fixture(tests/fixtures/krx_daily_events.json)는 2026-10-20 KRX에서 받은 실제 원값이다
(종가·등락률·상장주식수). 전일대비(CMPPREVDD_PRC)는 그 수집에 없어서, 등락률로 기준가를
역산한 뒤 호가 단위로 반올림해 만든다 — 이 역산은 fixture 전 구간에서 이벤트일을 뺀 모든
날 기준가 = 전일 종가로 정확히 맞는다(test_fixture_기준가_역산이_평일엔_전일종가와_같다).

DB는 쓰지 않는다. DB가 필요한 테스트는 SQLite 메모리 DB를 쓴다.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import sessionmaker

from fomobot.batch import collect_kospi
from fomobot.batch import kospi_price_adjust as adj
from fomobot.batch.kospi_price_adjust import (
    KIND_HOLD,
    KIND_RIGHTS,
    KIND_SHARE_BASIS,
    PriceBasisEvent,
    classify_price_basis,
    detect_price_basis_events,
)
from fomobot.db.models import PriceDaily

FIXTURE = Path(__file__).parent / "fixtures" / "krx_daily_events.json"
D = date(2026, 8, 14)


# ── fixture 재생 ─────────────────────────────────────────────────────────────

def _tick(price: float, on: str) -> int:
    """KOSPI 호가 단위. 2023-01-25 개편 전후가 다르다."""
    table = (
        ((2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500))
        if on >= "2023-01-25"
        else ((1000, 1), (5000, 5), (10000, 10), (50000, 50), (100000, 100), (500000, 500))
    )
    for limit, tick in table:
        if price < limit:
            return tick
    return 1000


def _krx_days(ticker: str) -> list[dict]:
    """fixture 행 → KRX 원값 dict 목록. 상장주식수가 없는 시계열은 상수로 둔다."""
    rows = json.load(open(FIXTURE, encoding="utf-8"))["series"][ticker]
    out = []
    for i, (d, close, fluc, shares) in enumerate(rows):
        if i == 0:
            cmp = 0.0
        else:
            est = close / (1 + fluc / 100)
            tick = _tick(est, d)
            cmp = close - round(est / tick) * tick
        # 006400·005930·267260은 상장주식수를 받지 않았다. 006400의 권리락일은 신주 상장 전이라
        # 주식 수가 그대로이므로 상수로 두면 실제와 같다(그 외 두 종목은 이벤트가 없어 무관).
        out.append({"date": date.fromisoformat(d), "close": float(close), "cmpprevdd": cmp,
                    "list_shrs": shares if shares is not None else 1})
    return out


def _replay(ticker: str) -> tuple[list[PriceBasisEvent], dict[date, float]]:
    """
    운영과 같은 순서로 하루씩 "분류 → 소급 보정 → 그날 원값 저장"을 재생한다.
    매일 같은 날짜를 한 번 더 분류해 이벤트가 0건인지(멱등성)도 확인한다.
    """
    days = _krx_days(ticker)
    db = {days[0]["date"]: days[0]["close"]}
    events = []
    for prev, cur in zip(days, days[1:]):
        ev = classify_price_basis(ticker, cur["date"], cur["close"], cur["cmpprevdd"],
                                  db[prev["date"]], cur["list_shrs"], prev["list_shrs"])
        if ev is not None:
            events.append(ev)
            if ev.is_auto:
                for k in db:
                    db[k] *= ev.factor
        again = classify_price_basis(ticker, cur["date"], cur["close"], cur["cmpprevdd"],
                                     db[prev["date"]], cur["list_shrs"], prev["list_shrs"])
        assert again is None, f"{ticker} {cur['date']} 재실행 시 이벤트 재검출: {again}"
        db[cur["date"]] = cur["close"]
    return events, db


@pytest.mark.parametrize("ticker", ["027970", "001210", "109070", "004920", "025560", "006400", "005930", "267260"])
def test_fixture_기준가_역산이_평일엔_전일종가와_같다(ticker):
    days = _krx_days(ticker)
    diff = [c["date"] for p, c in zip(days, days[1:]) if c["close"] - c["cmpprevdd"] != p["close"]]
    assert len(diff) <= 1  # 이벤트일 하루만 다르다


EXPECTED = {
    # ticker: (이벤트일, 분류, 계수 f = 기준가 / D-1 종가, 이벤트 전날 보정 후 종가 = 기준가)
    "027970": (date(2026, 8, 14), KIND_SHARE_BASIS, 2680 / 536, 2680),       # 1:5 감자, 정지 후 재개일
    "001210": (date(2026, 7, 31), KIND_SHARE_BASIS, 4470 / 894, 4470),       # 1:5 감자
    "109070": (date(2026, 9, 28), KIND_SHARE_BASIS, 7750 / 1550, 7750),      # 5:1 병합
    "004920": (date(2026, 10, 2), KIND_SHARE_BASIS, 9070 / 907, 9070),       # 10:1 병합
    "025560": (date(2026, 7, 27), KIND_SHARE_BASIS, 8350 / 41750, 8350),     # 1:5 액면분할
    "006400": (date(2025, 4, 10), KIND_RIGHTS, 168100 / 171700, 168100),     # 유상증자 권리락
}


@pytest.mark.parametrize("ticker", sorted(EXPECTED))
def test_이벤트_종목_분류와_계수(ticker):
    exp_date, exp_kind, exp_factor, exp_prev_after = EXPECTED[ticker]
    events, db = _replay(ticker)

    assert len(events) == 1
    ev = events[0]
    assert (ev.date, ev.kind) == (exp_date, exp_kind)
    assert ev.factor == pytest.approx(exp_factor, rel=1e-12)
    prev_date = max(k for k in db if k < exp_date)
    assert db[prev_date] == pytest.approx(exp_prev_after, rel=1e-12)  # 보정 후 D-1 = 기준가


@pytest.mark.parametrize("ticker", ["005930", "267260"])
def test_현금배당_종목은_이벤트_0건(ticker):
    events, _ = _replay(ticker)
    assert events == []


# ── 분류 규칙 ────────────────────────────────────────────────────────────────

def _cls(close, cmp, prev, shares=100, shares_prev=100):
    return classify_price_basis("T", D, close, cmp, prev, shares, shares_prev)


def test_기준가가_전일종가와_같으면_이벤트_없음():
    assert _cls(1000, 20, 980) is None


def test_보정_후_소수_prev도_상대오차로_같다고_본다():
    assert _cls(2750, 70, 2680.0000000001) is None


def test_주식수_불변_권리락은_f로_자동():
    ev = _cls(9800, 0, 10000)
    assert (ev.kind, ev.factor) == (KIND_RIGHTS, pytest.approx(0.98))


def test_주식수_불변인데_기준가가_오르면_보류():
    ev = _cls(12000, 0, 10000)
    assert (ev.kind, ev.factor) == (KIND_HOLD, None)


def test_주식수_불변인데_f가_너무_작으면_보류():
    ev = _cls(500, 0, 10000)
    assert ev.kind == KIND_HOLD


def test_호가_반올림된_병합도_계수는_f():
    ev = _cls(7800, 30, 1553, shares=20, shares_prev=100)  # 기준가 7770 = 1553×5 호가 반올림
    assert ev.kind == KIND_SHARE_BASIS
    assert ev.factor == ev.f == pytest.approx(7770 / 1553)  # 1/s(=5)는 판정에만 쓴다


def test_병합_보정_후_재실행은_이벤트_없음():
    ev = _cls(7800, 30, 1553, shares=20, shares_prev=100)
    assert _cls(7800, 30, 1553 * ev.factor, shares=20, shares_prev=100) is None


def test_주식수만_바뀌고_기준가가_그대로면_이벤트_없음():
    assert _cls(10010, 10, 10000, shares=105, shares_prev=100) is None  # 소각·CB 전환 등


def test_주식수가_바뀌고_기준가가_비례하지_않게_조금_바뀌면_보류():
    ev = _cls(10010, 0, 10000, shares=105, shares_prev=100)  # f=1.001, s=1.05
    assert (ev.kind, ev.factor) == (KIND_HOLD, None)


def test_주식수_변동과_기준가_변동이_맞지_않으면_보류():
    ev = _cls(3000, 0, 1000, shares=50, shares_prev=100)  # f=3, s=0.5
    assert (ev.kind, ev.factor) == (KIND_HOLD, None)


def test_주식수를_모르면_보류():
    ev = _cls(5000, 0, 1000, shares=None)
    assert ev.kind == KIND_HOLD


def test_D_1_행이_없는_신규상장은_skip():
    snapshot = {
        "NEW": {"close": 15000, "cmpprevdd": 5000, "list_shrs": 100},
        "OLD": {"close": 1000, "cmpprevdd": 0, "list_shrs": 100},
    }
    events = detect_price_basis_events(D, snapshot, prev_close={"OLD": 1000}, prev_shares={"OLD": 100})
    assert events == []


# ── DB 적용 (SQLite) ─────────────────────────────────────────────────────────

FLAG_DDL = """
CREATE TABLE corporate_action_flag (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ticker VARCHAR(20) NOT NULL UNIQUE, market VARCHAR(10) NOT NULL,
    flag_date DATE NOT NULL, reason VARCHAR(20) NOT NULL, status VARCHAR(10) NOT NULL,
    detected_signal TEXT, note TEXT, created_at TIMESTAMP, updated_at TIMESTAMP
)
"""


@pytest.fixture
def sqlite_session_factory():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _now(dbapi_conn, _):
        dbapi_conn.create_function("NOW", 0, lambda: "2026-10-20 00:00:00")

    PriceDaily.__table__.create(engine)
    with engine.begin() as conn:
        conn.execute(text(FLAG_DDL))
    return sessionmaker(engine)


def _seed(session, ticker, rows):
    for d, close, vol in rows:
        session.add(PriceDaily(ticker=ticker, market="kospi", date=d, open=close, high=close,
                               low=close, close_adj=close, volume=vol, market_cap=1))
    session.commit()


def _closes(session, ticker):
    rows = session.execute(
        select(PriceDaily.date, PriceDaily.close_adj, PriceDaily.volume)
        .where(PriceDaily.ticker == ticker).order_by(PriceDaily.date)
    ).fetchall()
    return [(r.date, r.close_adj, r.volume) for r in rows]


def _event(ticker, d, kind=KIND_SHARE_BASIS, factor=5.0):
    return PriceBasisEvent(ticker, d, base=2680, prev=536, f=5.0, s=0.2, kind=kind, factor=factor)


def test_자동_적용은_D_이전만_조정하고_되돌릴_수_있다(sqlite_session_factory):
    s = sqlite_session_factory()
    _seed(s, "A", [(date(2026, 8, 12), 536, 1000), (date(2026, 8, 13), 536, 0), (D, 2750, 500)])

    adj.apply_price_basis_events(s, "kospi", D, [_event("A", D)])
    s.commit()
    assert _closes(s, "A") == [
        (date(2026, 8, 12), pytest.approx(2680), 200),
        (date(2026, 8, 13), pytest.approx(2680), 0),
        (D, 2750, 500),
    ]

    adj.revert_price_basis_event(s, "kospi", "A", D, 5.0)
    s.commit()
    assert _closes(s, "A") == [
        (date(2026, 8, 12), pytest.approx(536), 1000),
        (date(2026, 8, 13), pytest.approx(536), 0),
        (D, 2750, 500),
    ]


def _flag(s, ticker):
    return s.execute(text("SELECT reason, status, flag_date, detected_signal FROM corporate_action_flag "
                          "WHERE ticker = :t"), {"t": ticker}).first()


def test_플래그_신규_자동은_resolved_보류는_pending(sqlite_session_factory):
    s = sqlite_session_factory()
    adj.apply_price_basis_events(s, "kospi", D, [
        _event("A", D),
        _event("B", D, factor=0.2),
        _event("C", D, kind=KIND_RIGHTS, factor=0.98),
        _event("H", D, kind=KIND_HOLD, factor=None),
    ])
    s.commit()
    assert _flag(s, "A")[:2] == ("merge", "resolved")
    assert _flag(s, "B")[:2] == ("split", "resolved")
    assert _flag(s, "C")[:2] == ("new_issuance", "resolved")
    assert _flag(s, "H")[:2] == ("manual", "pending")
    assert "[basis 2026-08-14] kind=share_basis" in _flag(s, "A").detected_signal


def test_기존_플래그는_상태를_지키고_내역만_덧붙인다(sqlite_session_factory):
    s = sqlite_session_factory()
    s.execute(text("INSERT INTO corporate_action_flag (ticker, market, flag_date, reason, status, detected_signal) "
                   "VALUES ('P', 'kospi', '2026-08-01', 'halted', 'pending', 'old'), "
                   "('R', 'kospi', '2026-07-01', 'merge', 'resolved', 'old')"))
    s.commit()

    adj.apply_price_basis_events(s, "kospi", D, [_event("P", D), _event("R", D, kind=KIND_HOLD, factor=None)])
    s.commit()

    p, r = _flag(s, "P"), _flag(s, "R")
    assert (p.reason, p.status) == ("halted", "pending")       # 자동 적용은 정지 종목 제외를 풀지 않는다
    assert p.detected_signal.startswith("old\n[basis 2026-08-14]")
    assert (r.reason, r.status) == ("merge", "pending")        # 보류는 resolved를 다시 제외
    assert r.detected_signal.startswith("old\n")


# ── 수집기 (collect_kospi) ───────────────────────────────────────────────────

def _raw(rows):
    """KRX 전종목시세 원 응답 형태(쉼표 문자열, 부호 있는 전일대비, 체결 없으면 '-')."""
    def fmt(v):
        return v if isinstance(v, str) else f"{v:,}"
    return pd.DataFrame([{
        "ISU_SRT_CD": t, "ISU_ABBRV": f"종목{t}", "TDD_OPNPRC": fmt(o), "TDD_HGPRC": fmt(o),
        "TDD_LWPRC": fmt(o), "TDD_CLSPRC": fmt(c), "ACC_TRDVOL": fmt(v), "CMPPREVDD_PRC": fmt(cmp),
        "MKTCAP": fmt(c * sh) if isinstance(c, int) else "-", "LIST_SHRS": fmt(sh),
    } for t, o, c, v, cmp, sh in rows])


def test_parse_day_snapshot_원_응답_파싱():
    df = collect_kospi.parse_day_snapshot(_raw([
        ("000001", 2370, 2365, 152157, -5, 1000),
        ("000002", "-", 536, 0, 0, 2000),        # 거래정지: 시가 없음
        ("000003", "-", "-", 0, 0, 10),          # 종가 없음 → 버림
    ]))
    assert list(df.index) == ["000001", "000002"]
    assert df.loc["000001", "cmpprevdd"] == -5
    assert df.loc["000001", "close"] == 2365
    assert df.loc["000001", "list_shrs"] == 1000
    assert df.loc["000002", "open"] is None


def test_missing_trading_days는_DB_최신일_이후만_오름차순():
    cal = [date(2026, 10, 16), date(2026, 10, 14), date(2026, 10, 15), date(2026, 10, 13)]
    assert collect_kospi.missing_trading_days(cal, date(2026, 10, 14)) == [date(2026, 10, 15), date(2026, 10, 16)]


D0, D1, D2, D3 = date(2026, 8, 12), date(2026, 8, 13), date(2026, 8, 14), date(2026, 8, 18)

# 날짜별 KRX 원 응답: (ticker, 시가, 종가, 거래량, 전일대비, 상장주식수)
SNAPSHOTS = {
    D0: [("027970", 536, 536, 0, 0, 190150720), ("005930", 10000, 10000, 100, 0, 5000)],
    D1: [("027970", "-", 536, 0, 0, 190150720), ("005930", 10100, 10100, 100, 100, 5000)],
    # 027970 재개: 기준가 2680(=536×5), 상장주식수 1/5. 신규상장 NEWIPO는 D-1 행이 없다.
    D2: [("027970", 2750, 2750, 35792, 70, 38030144), ("005930", 10050, 10050, 100, -50, 5000),
         ("NEWIPO", 20000, 26000, 100, 6000, 1000)],
    D3: [("027970", 2765, 2765, 10426, 15, 38030144), ("005930", 10050, 10050, 100, 0, 5000),
         ("NEWIPO", 25000, 25000, 100, -1000, 1000)],
}


@pytest.fixture
def fake_collector(monkeypatch, sqlite_session_factory):
    factory = sqlite_session_factory
    fetched: list[date] = []

    def fake_upsert(session, records, commit=True):
        stmt = sqlite_insert(PriceDaily).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["ticker", "market", "date"],
            set_={c: stmt.excluded[c] for c in ("open", "high", "low", "close_adj", "volume", "market_cap")},
        )
        session.execute(stmt)
        if commit:
            session.commit()

    def fake_fetch(d):
        fetched.append(d)
        return collect_kospi.parse_day_snapshot(_raw(SNAPSHOTS[d]))

    def fake_index(start, end):
        s, e = date.fromisoformat(f"{start[:4]}-{start[4:6]}-{start[6:]}"), date.fromisoformat(f"{end[:4]}-{end[4:6]}-{end[6:]}")
        days = [d for d in sorted(SNAPSHOTS) if s <= d <= e]
        return pd.DataFrame({"종가": [2500.0] * len(days)}, index=pd.to_datetime(days))

    monkeypatch.setattr(collect_kospi, "SyncSessionLocal", factory)
    monkeypatch.setattr(collect_kospi, "_ensure_krx_auth", lambda: None)
    monkeypatch.setattr(collect_kospi, "_fetch_kospi_index", fake_index)
    monkeypatch.setattr(collect_kospi, "_fetch_day_snapshot", fake_fetch)
    monkeypatch.setattr(collect_kospi, "upsert_price_daily_sync", fake_upsert)
    monkeypatch.setattr(collect_kospi, "upsert_index_daily_sync", lambda s, r: None)
    monkeypatch.setattr(collect_kospi, "upsert_securities_master_sync", lambda s, r: None)
    monkeypatch.setattr(adj, "report_price_basis_events", lambda m, e: None)

    s = factory()
    _seed(s, "027970", [(D0, 536, 0)])
    _seed(s, "005930", [(D0, 10000, 100)])
    s.close()
    return factory, fetched


def test_여러_날_공백은_오름차순으로_수집_보정을_하루씩_반복(fake_collector):
    factory, fetched = fake_collector

    days = collect_kospi.run_kospi_collection(target_date=D3)

    assert days == [D1, D2, D3]
    assert fetched == [D0, D1, D2, D3]  # D0은 D1 보정용 D-1 상장주식수
    s = factory()
    assert [c for _, c, _ in _closes(s, "027970")] == pytest.approx([2680, 2680, 2750, 2765])
    assert [c for _, c, _ in _closes(s, "005930")] == [10000, 10100, 10050, 10050]
    assert [c for _, c, _ in _closes(s, "NEWIPO")] == [26000, 25000]  # 신규상장은 보정 없이 저장
    assert _flag(s, "027970")[:2] == ("merge", "resolved")
    assert _flag(s, "NEWIPO") is None


def test_같은_날짜를_다시_돌리면_수집도_보정도_없다(fake_collector):
    factory, fetched = fake_collector
    collect_kospi.run_kospi_collection(target_date=D3)
    fetched.clear()

    assert collect_kospi.run_kospi_collection(target_date=D3) == []
    assert fetched == []
    assert [c for _, c, _ in _closes(factory(), "027970")] == pytest.approx([2680, 2680, 2750, 2765])


def test_같은_날_보정을_다시_적용해도_이벤트_0건(fake_collector):
    factory, _ = fake_collector
    collect_kospi.run_kospi_collection(target_date=D3)

    s = factory()
    snap = collect_kospi.parse_day_snapshot(_raw(SNAPSHOTS[D2]))
    rows = snap[["close", "cmpprevdd", "list_shrs"]].to_dict("index")
    prev_close = {t: c for t, c in s.execute(
        select(PriceDaily.ticker, PriceDaily.close_adj).where(PriceDaily.date == D1)).fetchall()}
    prev_shares = collect_kospi.parse_day_snapshot(_raw(SNAPSHOTS[D1]))["list_shrs"].to_dict()
    assert detect_price_basis_events(D2, rows, prev_close, prev_shares) == []


def test_KRX_로그인_실패_후에는_같은_프로세스에서_다시_시도하지_않는다(monkeypatch):
    import os

    if os.getenv("KRX_ID") or os.getenv("KRX_PW"):
        pytest.skip("실제 KRX 계정이 환경에 있으면 pykrx import가 로그인을 시도하므로 건너뛴다")
    import pykrx.website.comm.auth as krx_auth

    monkeypatch.setattr(collect_kospi, "_krx_login_failed", False)
    monkeypatch.setattr(krx_auth, "_auth_session", None)

    with pytest.raises(RuntimeError, match="KRX 로그인 실패"):
        collect_kospi._ensure_krx_auth()
    assert collect_kospi._krx_login_failed is True

    class Boom:
        def is_valid(self):
            raise AssertionError("실패 후에는 세션을 다시 건드리면 안 된다")

    monkeypatch.setattr(krx_auth, "_auth_session", Boom())
    with pytest.raises(RuntimeError, match="이미 실패"):
        collect_kospi._ensure_krx_auth()


def test_KRX_만료된_세션은_refresh를_1회만_시도한다(monkeypatch):
    import os

    if os.getenv("KRX_ID") or os.getenv("KRX_PW"):
        pytest.skip("실제 KRX 계정이 환경에 있으면 건너뛴다")
    import pykrx.website.comm.auth as krx_auth

    calls = []

    class Expired:
        def is_valid(self):
            return False

        def refresh(self, login_id, login_pw):
            calls.append(1)
            return False

    monkeypatch.setattr(collect_kospi, "_krx_login_failed", False)
    monkeypatch.setattr(krx_auth, "_auth_session", Expired())
    for _ in range(3):
        with pytest.raises(RuntimeError):
            collect_kospi._ensure_krx_auth()
    assert calls == [1]


# ── 재적재 스크립트의 종목 분류 (scripts/reload_kospi_since_0914.py) ─────────

@pytest.fixture(scope="module")
def reload_mod():
    import runpy
    return runpy.run_path(str(Path(__file__).parent.parent / "scripts" / "reload_kospi_since_0914.py"), run_name="reload_mod")


@pytest.mark.parametrize("r, F, has_auto, has_hold, expected", [
    (1.0, 1.0, False, False, "ok"),
    (1.003, 1.0, False, False, "hold"),        # 이벤트 없는데 9/11 연속성 깨짐
    (None, 1.0, False, False, "new"),          # 앵커일 DB 행 없음(신규상장)
    (5.0, 5.0, True, False, "corrected"),      # 9/21 수동 ×5 정정
    (5.0, 5.0032, True, False, "corrected"),   # 수동 정수배 vs 호가 반올림된 f
    (1.0, 0.5, True, False, "uncorrected"),    # 009140: 아직 정정 안 됨 → 앵커 이하에도 F
    (2.0, 3.0, True, False, "hold"),           # r이 1도 F도 아님
    (1.0, 0.995, True, False, "uncorrected"),  # F가 1에 가까워도 r이 정확히 1이면 미정정
    (0.995, 0.995, True, False, "corrected"),  # F가 1에 가까우면 정확 일치만 인정
    (0.996, 0.995, True, False, "hold"),       # 1에 가까운 F와 근사 일치는 구분 불가 → 보류
    (1.0, 5.0, True, True, "hold"),            # 보류 이벤트가 있으면 무조건 보류
])
def test_재적재_종목_분류(reload_mod, r, F, has_auto, has_hold, expected):
    assert reload_mod["classify_ticker"](r, F, has_auto, has_hold) == expected


def test_수동_지정_계수_플래그는_랭킹_제외가_아니다(sqlite_session_factory):
    from fomobot.batch.kospi_price_adjust import KIND_OVERRIDE

    s = sqlite_session_factory()
    s.execute(text("INSERT INTO corporate_action_flag (ticker, market, flag_date, reason, status, detected_signal) "
                   "VALUES ('E', 'kospi', '2026-09-21', 'merge', 'resolved', 'old')"))
    s.commit()
    adj.apply_price_basis_events(s, "kospi", D, [
        _event("N", D, kind=KIND_OVERRIDE, factor=2.0),   # 기존 플래그 없음
        _event("E", D, kind=KIND_OVERRIDE, factor=2.0),   # 기존 resolved 플래그
    ])
    s.commit()
    assert _flag(s, "N")[:2] == ("manual", "resolved")
    assert _flag(s, "E")[:2] == ("merge", "resolved")
    assert "kind=override" in _flag(s, "E").detected_signal


def test_재적재_수동_지정은_보류를_corrected로_바꾼다(reload_mod):
    d0, d1, d2 = date(2026, 9, 11), date(2026, 9, 21), date(2026, 9, 22)
    snap = lambda close, cmp, shrs: pd.DataFrame(  # noqa: E731
        {"name": ["x"], "open": [close], "high": [close], "low": [close], "close": [float(close)],
         "volume": [10], "cmpprevdd": [float(cmp)], "market_cap": [1], "list_shrs": [shrs]},
        index=["002630"])
    krx = {"anchor": d0, "window": [d1, d2], "snapshots": {
        d0: snap(913, 0, 100), d1: snap(913, 0, 100), d2: snap(2000, 64, 50)}}  # 9/22 기준가 1936 ≠ 913×2

    held = reload_mod["build_plan"](krx, {"002630": 1826.0})["tickers"]["002630"]
    assert held["category"] == "hold"

    plan = reload_mod["build_plan"](krx, {"002630": 1826.0}, {"002630": 2.0})["tickers"]["002630"]
    assert plan["category"] == "corrected"
    assert plan["r"] == pytest.approx(2.0)
    assert [r["close_adj"] for r in plan["rows"]] == [1826.0, 2000.0]  # 9/21 원값 ×2, 9/22 원값
    assert plan["retro_factor"] is None  # 9/11 이하는 이미 ×2 정정돼 있어 건드리지 않음


# ── 수집 상한: KST 기준 어제까지만 (collection_upper_bound) ──────────────────

def _utc(y, m, d, hh, mm):
    from datetime import datetime, timezone
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


@pytest.mark.parametrize("utc_now, target, expected", [
    (_utc(2026, 10, 22, 1, 0), None, date(2026, 10, 21)),             # KST 10-22 10:00(장중) → 10-21
    (_utc(2026, 10, 22, 15, 5), None, date(2026, 10, 22)),            # KST 10-23 00:05 → 10-22 (UTC 날짜로는 10-22)
    (_utc(2026, 10, 22, 14, 59), None, date(2026, 10, 21)),           # KST 10-22 23:59 → 아직 10-21
    (_utc(2026, 10, 22, 1, 0), date(2026, 10, 25), date(2026, 10, 21)),  # target이 미래여도 KST 어제로 자름
    (_utc(2026, 10, 22, 1, 0), date(2026, 10, 15), date(2026, 10, 15)),  # target이 더 이르면 target
])
def test_수집_상한은_KST_어제(monkeypatch, utc_now, target, expected):
    monkeypatch.setattr(collect_kospi, "_utc_now", lambda: utc_now)
    assert collect_kospi.collection_upper_bound(target) == expected


def test_KST_당일_장중_실행은_전날까지만_수집(fake_collector, monkeypatch):
    factory, fetched = fake_collector
    monkeypatch.setattr(collect_kospi, "_utc_now", lambda: _utc(2026, 8, 18, 1, 0))  # KST 8/18(D3) 10:00

    assert collect_kospi.run_kospi_collection() == [D1, D2]
    assert D3 not in fetched
    assert [d for d, _, _ in _closes(factory(), "005930")] == [D0, D1, D2]


def test_KST_자정_직후_실행은_전날까지_수집(fake_collector, monkeypatch):
    factory, fetched = fake_collector
    monkeypatch.setattr(collect_kospi, "_utc_now", lambda: _utc(2026, 8, 18, 15, 5))  # KST 8/19 00:05, UTC는 8/18

    assert collect_kospi.run_kospi_collection() == [D1, D2, D3]


def test_휴장일_다음_실행은_마지막_거래일까지만(fake_collector, monkeypatch):
    factory, fetched = fake_collector
    # KST 8/17(월, 대체공휴일) 10:00 — 달력상 마지막 거래일은 8/14(금, D2)
    monkeypatch.setattr(collect_kospi, "_utc_now", lambda: _utc(2026, 8, 17, 1, 0))
    assert collect_kospi.run_kospi_collection() == [D1, D2]

    # 같은 날 다시 돌면 달력상 새 거래일이 없어 전종목 조회를 하지 않는다
    fetched.clear()
    assert collect_kospi.run_kospi_collection() == []
    assert fetched == []


def test_DB_최신일이_이미_KST_어제면_KRX_로그인_없이_끝난다(fake_collector, monkeypatch):
    factory, fetched = fake_collector
    monkeypatch.setattr(collect_kospi, "_utc_now", lambda: _utc(2026, 8, 18, 1, 0))  # KST 8/18 10:00
    collect_kospi.run_kospi_collection()                                            # D1, D2 수집
    monkeypatch.setattr(collect_kospi, "_utc_now", lambda: _utc(2026, 8, 15, 1, 0))  # KST 8/15 → 상한 8/14 = DB 최신일

    def no_login():
        raise AssertionError("DB 최신일이 상한과 같으면 KRX 로그인을 하면 안 된다")
    monkeypatch.setattr(collect_kospi, "_ensure_krx_auth", no_login)
    fetched.clear()
    assert collect_kospi.run_kospi_collection() == []
    assert fetched == []
