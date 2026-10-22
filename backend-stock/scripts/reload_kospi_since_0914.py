"""
KOSPI price_daily 재적재(1회성) — 2026-09-14 이후 네이버 fchart 값을 KRX 원 종가 + 기준가 소급 보정으로 교체.

배경: 이전 수집(pykrx adjusted=True)은 네이버 fchart를 썼고, 네이버 일봉은 2026-09-14부터
NXT 애프터마켓이 섞인 통합 시세라 KRX 공식 종가와 다르다. 그 이전은 KRX와 같다.
그래서 9/14 이후만 KRX 값으로 다시 쓰고, 9/14 이전 이력은 원칙적으로 그대로 둔다.

동작 (기본 --dry-run, --apply를 줘야만 DB에 쓴다):
  1. KRX: 앵커일(--start 직전 거래일, 9/11) ~ --end 전종목시세 + 지수 달력. 로그인 1회.
     --krx-cache 파일이 있으면 KRX에 접속하지 않고 그 파일을 쓴다(없으면 받아서 저장).
  2. 구간 내 이벤트: 날짜 오름차순으로 kospi_price_adjust.classify_price_basis를 적용한다.
     prev는 전 거래일의 KRX 원 종가다 — 재적재 후 구간 안의 DB 값이 곧 KRX 원값 기준이므로,
     운영 수집기의 "DB D-1 close_adj"와 같은 값이다. 첫날 prev는 앵커일 KRX 원 종가.
  3. 종목별 r = DB 앵커일 close_adj ÷ KRX 앵커일 원 종가, F = 구간 내 자동 계수의 곱:
       이벤트 있음 + r ≈ F → corrected   이미 정정됨(9/21 수동 정정 6종목 등). 구간 행만 쓴다.
       이벤트 있음 + r ≈ 1 → uncorrected 구간 행을 쓰고 앵커일 이하 DB 이력에도 F를 곱한다.
       이벤트 없음 + r ≈ 1 → ok          구간 행만 쓴다.
       앵커일 DB 행 없음   → new         구간 중 신규상장 등. 구간 행만 쓴다.
       그 외 / 보류 이벤트 → hold        이 종목은 쓰지 않는다(보류 목록).
     --override TICKER=FACTOR로 보류 이벤트의 계수를 사람이 지정하면 그 계수로 위 분류를 다시 한다
     (2026-10-21: 002630=2 — 9/22 병합 재상장 기준가가 913×2가 아닌 1,936, 9/21 수동 ×2 정정과 맞춤).
  4. 구간 행의 새 값 = KRX 원값 × (그 날짜 이후 구간 내 자동 계수의 곱). 거래량은 ÷.
  5. dry-run: 콘솔 요약 + --out 폴더에 상세(JSON). --apply: 한 트랜잭션으로 쓰고 이벤트를
     corporate_action_flag에 기록한다(운영 수집기와 같은 규칙).

DB 입력: Railway 셸에서는 DB를 직접 읽는다. 로컬 dry-run은 운영 DB에 접속하지 않도록
--db-input 파일(사용자가 Railway 콘솔 SQL로 뽑은 값)을 쓴다 — --apply와는 함께 쓸 수 없다.
  {"anchor_close": {"005930": 259500, ...},                 # 앵커일 close_adj
   "pre_counts": {"005930": 1520, ...},                     # 선택: 앵커일 이하 행 수
   "samples": {"005930": {"2026-09-09": 269500, ...}}}      # 선택: 변경 전 값 대조용

실행 (Railway 셸, 18:00 cron과 겹치지 않게):
    cd backend-stock
    python scripts/reload_kospi_since_0914.py                       # dry-run
    python scripts/reload_kospi_since_0914.py --apply               # 쓰기
"""

import argparse
import json
import logging
import os
import pickle
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("reload_kospi")

MARKET = "kospi"
R_EXACT = 1e-6         # r ≈ 1 / r ≈ F 정확 일치(상대오차)
R_NEAR = 0.01          # 수동 정수배 정정 vs 기준가 계수(호가 반올림) 허용 차이
F_DISTINCT = 0.02      # |F − 1|이 이보다 작으면 r ≈ 1과 r ≈ F를 근사로 구분할 수 없다
SAMPLE_TICKERS = ("005930", "109070", "009140")


# ── KRX ──────────────────────────────────────────────────────────────────────

def fetch_krx(start: date, end: date, extra_dates: list[date]) -> dict:
    """로그인 1회로 달력·앵커·구간·추가 날짜의 전종목시세를 받는다."""
    from fomobot.batch import collect_kospi as ck
    from pykrx.website.krx.market.core import 전종목시세

    ck._ensure_krx_auth()
    idx = ck._fetch_kospi_index((start - timedelta(days=14)).strftime("%Y%m%d"), end.strftime("%Y%m%d"))
    calendar = sorted(ts.date() for ts in idx.index)
    window = [d for d in calendar if start <= d <= end]
    anchor = max(d for d in calendar if d < start)

    snapshots: dict[date, object] = {}
    raw_sample = None
    for d in [anchor, *window, *extra_dates]:
        raw = 전종목시세().fetch(d.strftime("%Y%m%d"), "STK")
        if raw_sample is None:
            raw_sample = raw.head(20)
        snapshots[d] = ck.parse_day_snapshot(raw)
        logger.info("KRX %s 전종목 %d종목", d, len(snapshots[d]))
        time.sleep(0.5)
    return {"calendar": calendar, "anchor": anchor, "window": window,
            "snapshots": snapshots, "raw_sample": raw_sample}


# ── 계획 ─────────────────────────────────────────────────────────────────────

def _rel(a: float, b: float) -> float:
    return abs(a / b - 1)


def classify_ticker(r: float | None, factor_product: float, has_auto: bool, has_hold: bool) -> str:
    if has_hold:
        return "hold"
    if r is None:
        return "new"
    if not has_auto:
        return "ok" if _rel(r, 1.0) <= R_EXACT else "hold"
    if _rel(r, 1.0) <= R_EXACT:
        return "uncorrected"
    distinct = abs(factor_product - 1) >= F_DISTINCT
    if _rel(r, factor_product) <= (R_NEAR if distinct else R_EXACT):
        return "corrected"
    return "hold"


def build_plan(krx: dict, anchor_close: dict[str, float], overrides: dict[str, float] | None = None) -> dict:
    """overrides: {ticker: 계수} — 구간 내 이벤트가 정확히 1건인 종목의 계수를 사람이 지정한다."""
    from dataclasses import replace

    from fomobot.batch.kospi_price_adjust import KIND_OVERRIDE, classify_price_basis

    overrides = overrides or {}

    anchor, window, snaps = krx["anchor"], krx["window"], krx["snapshots"]
    days = [anchor, *window]
    tickers = sorted(set().union(*(snaps[d].index for d in window)))

    plan = {"anchor": anchor.isoformat(), "start": window[0].isoformat(), "end": window[-1].isoformat(),
            "tickers": {}}
    for t in tickers:
        events = []
        for prev_d, d in zip(days, days[1:]):
            if t not in snaps[d].index:
                continue
            cur = snaps[d].loc[t]
            prev = snaps[prev_d].loc[t] if t in snaps[prev_d].index else None
            ev = classify_price_basis(
                t, d, float(cur["close"]), float(cur["cmpprevdd"]),
                float(prev["close"]) if prev is not None else None,
                int(cur["list_shrs"]), int(prev["list_shrs"]) if prev is not None else None,
            )
            if ev is not None:
                events.append(ev)

        if t in overrides:
            if len(events) != 1:
                raise ValueError(f"--override {t}: 구간 내 이벤트가 {len(events)}건 — 정확히 1건일 때만 지정 가능")
            events = [replace(events[0], kind=KIND_OVERRIDE, factor=overrides[t])]

        auto = [e for e in events if e.is_auto]
        factor_product = 1.0
        for e in auto:
            factor_product *= e.factor
        krx_anchor = float(snaps[anchor].loc[t, "close"]) if t in snaps[anchor].index else None
        db_anchor = anchor_close.get(t)
        r = (db_anchor / krx_anchor) if (db_anchor and krx_anchor) else None
        if db_anchor is None:
            r = None
        category = classify_ticker(r, factor_product, bool(auto), any(not e.is_auto for e in events))

        rows = []
        if category != "hold":
            for d in window:
                if t not in snaps[d].index:
                    continue
                g = 1.0
                for e in auto:
                    if e.date > d:
                        g *= e.factor
                row = snaps[d].loc[t]
                rows.append({
                    "date": d.isoformat(),
                    "open": row["open"] * g if row["open"] is not None else None,
                    "high": row["high"] * g if row["high"] is not None else None,
                    "low": row["low"] * g if row["low"] is not None else None,
                    "close_adj": float(row["close"]) * g,
                    "volume": int(round(int(row["volume"]) / g)),
                    "market_cap": int(row["market_cap"]) or None,
                })
        plan["tickers"][t] = {
            "category": category,
            "r": r,
            "db_anchor": db_anchor,
            "krx_anchor": krx_anchor,
            "factor_product": factor_product,
            "retro_factor": factor_product if category == "uncorrected" else None,
            "events": [{"date": e.date.isoformat(), "kind": e.kind, "f": e.f, "s": e.s,
                        "factor": e.factor, "base": e.base, "prev": e.prev} for e in events],
            "rows": rows,
        }
    return plan


# ── 출력 ─────────────────────────────────────────────────────────────────────

def summarize(plan: dict, krx: dict, db_input: dict) -> str:
    T = plan["tickers"]
    by_cat: dict[str, list[str]] = {}
    for t, v in T.items():
        by_cat.setdefault(v["category"], []).append(t)
    pre_counts = db_input.get("pre_counts") or {}
    window_rows = sum(len(v["rows"]) for v in T.values())
    retro = [t for t in by_cat.get("uncorrected", [])]
    retro_rows = sum(pre_counts.get(t, 0) for t in retro)

    out = [
        f"구간 {plan['start']} ~ {plan['end']} (거래일 {len(krx['window'])}일), 앵커 {plan['anchor']}",
        f"종목 {len(T)}개 — " + ", ".join(f"{k} {len(v)}" for k, v in sorted(by_cat.items())),
        f"쓰기 행: 구간(9/14 이후) {window_rows}행 / 앵커일 이하 소급 "
        + (f"{retro_rows}행" if pre_counts else f"(행 수는 pre_counts 필요) {len(retro)}종목"),
        "",
        "[이벤트가 있는 종목]",
    ]
    for t, v in sorted(T.items()):
        if not v["events"]:
            continue
        evs = "; ".join(
            f"{e['date']} {e['kind']} f={e['f']:.6f} s={e['s']:.6f} factor={e['factor']}" if e["s"] is not None
            else f"{e['date']} {e['kind']} f={e['f']:.6f} s=null factor={e['factor']}"
            for e in v["events"]
        )
        r_txt = f"{v['r']:.6f}" if v["r"] is not None else "null"
        out.append(f"  {t} {v['category']:<11} r={r_txt} F={v['factor_product']:.6f} | {evs}")
    out += ["", "[보류(hold) 종목과 사유]"]
    for t in sorted(by_cat.get("hold", [])):
        v = T[t]
        if any(not e["factor"] for e in v["events"]):
            why = "보류 이벤트: " + ", ".join(f"{e['date']} f={e['f']:.4f}" for e in v["events"] if not e["factor"])
        elif v["events"]:
            why = f"r={v['r']} 가 1도 F={v['factor_product']:.6f}도 아님"
        else:
            why = f"이벤트 없는데 r={v['r']} ≠ 1 (DB {v['db_anchor']} vs KRX {v['krx_anchor']})"
        out.append(f"  {t}: {why}")

    samples = db_input.get("samples") or {}
    if samples:
        out += ["", "[샘플 대조: DB 현재 → 재적재 후]"]
        for t in SAMPLE_TICKERS:
            if t not in T:
                continue
            new = {row["date"]: row["close_adj"] for row in T[t]["rows"]}
            retro_g = T[t]["retro_factor"]
            for d in sorted(set(samples.get(t, {})) | set(new)):
                before = samples.get(t, {}).get(d)
                if d < plan["start"]:
                    after = before * retro_g if (before is not None and retro_g) else before
                else:
                    after = new.get(d)
                out.append(f"  {t} {d}: {before} → {after}")
    return "\n".join(out)


# ── 쓰기 ─────────────────────────────────────────────────────────────────────

def apply_plan(plan: dict) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from fomobot.batch.kospi_price_adjust import PriceBasisEvent, _record_flag, _scale_history
    from fomobot.db.models import PriceDaily
    from fomobot.db.session import SyncSessionLocal

    anchor = date.fromisoformat(plan["anchor"])
    start = date.fromisoformat(plan["start"])
    with SyncSessionLocal() as session:
        for t, v in plan["tickers"].items():
            if v["category"] == "hold":
                # 쓰지 않는 종목은 구간 값이 네이버 기준으로 남으므로 pending으로 랭킹에서 뺀다.
                first = v["events"][0] if v["events"] else None
                _record_flag(session, MARKET, PriceBasisEvent(
                    t, date.fromisoformat(first["date"]) if first else start,
                    first["base"] if first else (v["krx_anchor"] or 0),
                    first["prev"] if first else (v["db_anchor"] or 0),
                    first["f"] if first else (v["r"] or 0),
                    first["s"] if first else None, "hold", None))
                continue
            if v["retro_factor"]:
                # 앵커일 이하 전체 이력(date < start)에 구간 내 계수 곱을 적용
                _scale_history(session, MARKET, t, anchor + timedelta(days=1), v["retro_factor"])
            records = [{"ticker": t, "market": MARKET, "date": date.fromisoformat(r["date"]),
                        **{k: r[k] for k in ("open", "high", "low", "close_adj", "volume", "market_cap")}}
                       for r in v["rows"]]
            for i in range(0, len(records), 1000):
                stmt = pg_insert(PriceDaily).values(records[i:i + 1000])
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_price_daily",
                    set_={c: stmt.excluded[c] for c in ("open", "high", "low", "close_adj", "volume", "market_cap")},
                )
                session.execute(stmt)
            for e in v["events"]:
                _record_flag(session, MARKET, PriceBasisEvent(
                    t, date.fromisoformat(e["date"]), e["base"], e["prev"], e["f"], e["s"], e["kind"], e["factor"]))
        session.commit()
    logger.info("apply 완료")


def _read_db_input_from_db(anchor: date) -> dict:
    from sqlalchemy import text

    from fomobot.db.session import SyncSessionLocal

    with SyncSessionLocal() as s:
        anchor_close = dict(s.execute(text(
            "SELECT ticker, close_adj FROM price_daily WHERE market = :m AND date = :d"),
            {"m": MARKET, "d": anchor}).fetchall())
        pre_counts = dict(s.execute(text(
            "SELECT ticker, COUNT(*) FROM price_daily WHERE market = :m AND date <= :d GROUP BY ticker"),
            {"m": MARKET, "d": anchor}).fetchall())
        rows = s.execute(text(
            "SELECT ticker, date, close_adj FROM price_daily WHERE market = :m AND ticker = ANY(:t) "
            "AND date >= :d ORDER BY ticker, date"),
            {"m": MARKET, "t": list(SAMPLE_TICKERS), "d": anchor - timedelta(days=5)}).fetchall()
    samples: dict[str, dict] = {}
    for t, d, c in rows:
        samples.setdefault(t, {})[d.isoformat()] = c
    return {"anchor_close": anchor_close, "pre_counts": pre_counts, "samples": samples}


def main() -> None:
    p = argparse.ArgumentParser(description="KOSPI 2026-09-14 이후 KRX 원 종가 재적재")
    p.add_argument("--start", type=date.fromisoformat, default=date(2026, 9, 14))
    p.add_argument("--end", type=date.fromisoformat, required=False,
                   help="기본: DB 최신일(--db-input이면 필수)")
    p.add_argument("--krx-cache", type=Path, help="KRX 응답 캐시(pickle). 있으면 KRX에 접속하지 않는다")
    p.add_argument("--db-input", type=Path, help="로컬 dry-run용 DB 값(JSON). 운영 DB에 접속하지 않는다")
    p.add_argument("--extra-date", type=date.fromisoformat, action="append", default=[],
                   help="함께 받아 둘 추가 날짜(검증용, 계획에는 쓰지 않음)")
    p.add_argument("--out", type=Path, default=Path("reload_kospi_out"))
    p.add_argument("--override", action="append", default=[], metavar="TICKER=FACTOR",
                   help="자동 분류가 보류한 종목의 계수 수동 지정(예: 002630=2). 구간 내 이벤트 1건일 때만")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    if args.apply and args.db_input:
        p.error("--apply는 --db-input과 함께 쓸 수 없다(DB를 직접 읽어야 함)")

    end = args.end
    if end is None:
        if args.db_input:
            p.error("--db-input이면 --end를 지정")
        from fomobot.db.crud import get_last_trading_day_sync
        from fomobot.db.session import SyncSessionLocal
        with SyncSessionLocal() as s:
            end = get_last_trading_day_sync(s, MARKET)

    from fomobot.batch.collect_kospi import collection_upper_bound
    if end > collection_upper_bound():
        p.error(f"--end {end}는 KST 기준 어제({collection_upper_bound()}) 이후 — 당일 KRX 값은 확정 전이라 쓸 수 없다")

    if args.krx_cache and args.krx_cache.exists():
        krx = pickle.load(open(args.krx_cache, "rb"))
        logger.info("KRX 캐시 사용: %s", args.krx_cache)
    else:
        krx = fetch_krx(args.start, end, args.extra_date)
        if args.krx_cache:
            pickle.dump(krx, open(args.krx_cache, "wb"))

    db_input = json.load(open(args.db_input, encoding="utf-8")) if args.db_input else _read_db_input_from_db(krx["anchor"])
    anchor_close = {t: float(c) for t, c in db_input["anchor_close"].items()}

    overrides = {}
    for item in args.override:
        t, _, v = item.partition("=")
        if not t or not v:
            p.error(f"--override 형식 오류: {item} (TICKER=FACTOR)")
        overrides[t.strip()] = float(v)
    plan = build_plan(krx, anchor_close, overrides)
    summary = summarize(plan, krx, db_input)
    print(summary)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.txt").write_text(summary, encoding="utf-8")
    json.dump(plan, open(args.out / "plan.json", "w", encoding="utf-8"), ensure_ascii=False, default=str)
    logger.info("상세: %s", args.out.resolve())

    if args.apply:
        apply_plan(plan)
    else:
        logger.info("dry-run — DB에 쓰지 않음 (--apply로 실행 시에만 쓰기)")


if __name__ == "__main__":
    main()
