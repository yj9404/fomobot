"""
NASDAQ 역분할 오염 종목 환산 정정(1회성) — yfinance 원본이 미조정이라 재수집으로 못 고치는 종목용.

refetch_nasdaq_splits.py가 hold로 남긴 종목 중 "분할 이력은 있는데 yfinance 가격이 미조정"인 것
(CPOP, IPDN, IZM, BTLN, DLXY, GMEX, IMMP — 2026-10-26)이 대상이다. DB에서 관측된 절벽일 이전
행에 분할 비율의 역수 F를 곱한다 (가격 ×F, 거래량 ÷F). 판정 기준은
fomobot.batch.nasdaq_split_refetch.plan_scale 참조.

동작 (기본 --dry-run, --apply를 줘야만 DB에 쓴다):
  1. status=excluded / reason=split 종목과 flag_date 앞뒤 종가를 읽는다 (--db-input이면 파일).
  2. 종목마다 yfinance 분할 이력으로 plan_scale 판정. 점프 배율 × 분할 비율이 0.7~1.3이어야 한다.
  3. dry-run: 판정 요약만 출력. --apply: scalable 종목마다 한 트랜잭션으로 환산 + flag resolved.
     쓰기 직전 DB의 점프 배율을 다시 확인해 이미 환산된 종목은 건너뛴다 (이중 환산 방지).

DB 입력: 로컬 dry-run은 운영 DB에 접속하지 않도록 --db-input 파일을 쓴다 (--apply와는 함께 쓸 수 없다).
  {"flags": {"BTLN": "2026-09-28", ...},
   "closes": {"BTLN": {"2026-09-25": 0.64, "2026-09-28": 5.25, ...}}}   # flag_date 앞뒤 종가

yfinance에 분할 기록이 없는 종목(GCTK, GLMD 등)은 공시로 분할일·비율을 확인한 뒤 --split으로 지정한다.
점프 배율 × 분할 비율 검증은 그대로 적용되므로 비율이 틀리면 hold가 된다.

실행 (Railway 셸, 일일 수집 cron과 겹치지 않게):
    cd backend-stock
    python scripts/scale_nasdaq_splits.py              # dry-run
    python scripts/scale_nasdaq_splits.py --apply      # 쓰기
    python scripts/scale_nasdaq_splits.py --split GCTK=15@2026-08-31 --split GLMD=8@2026-08-19
"""

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("scale_nasdaq_splits")

WINDOW_DAYS = 10  # nasdaq_split_refetch.CLIFF_CHECK_DAYS와 같은 값


def _read_db_input_from_db() -> dict:
    from sqlalchemy import text

    from fomobot.db.session import SyncSessionLocal

    with SyncSessionLocal() as s:
        flags = {t: d for t, d in s.execute(text(
            "SELECT ticker, flag_date FROM corporate_action_flag "
            "WHERE market = 'nasdaq' AND reason = 'split' AND status = 'excluded'")).fetchall()}
        closes: dict[str, dict] = {}
        for t, d, c in s.execute(text(
            "SELECT p.ticker, p.date, p.close_adj FROM price_daily p "
            "JOIN corporate_action_flag f ON f.ticker = p.ticker AND f.market = p.market "
            "WHERE p.market = 'nasdaq' AND f.reason = 'split' AND f.status = 'excluded' "
            "AND p.date BETWEEN f.flag_date - :w AND f.flag_date + :w"), {"w": WINDOW_DAYS}).fetchall():
            closes.setdefault(t, {})[d] = c
    return {"flags": flags, "closes": closes}


def _load_db_input(path: Path) -> dict:
    raw = json.load(open(path, encoding="utf-8"))
    return {
        "flags": {t: date.fromisoformat(d) for t, d in raw["flags"].items()},
        "closes": {t: {date.fromisoformat(d): c for d, c in m.items()} for t, m in (raw.get("closes") or {}).items()},
    }


def summarize(plans: list[dict]) -> str:
    ok = [p for p in plans if p["category"] == "scalable"]
    hold = [p for p in plans if p["category"] == "hold"]
    out = [f"종목 {len(plans)}개 — scalable {len(ok)}, hold {len(hold)}", "", "[scalable: 환산 대상]"]
    for p in ok:
        out.append(f"  {p['ticker']:<6} 절벽 {p['cliff_date']} x{p['jump']:.2f} / 분할 {p['split_date']} "
                   f"({p['split_ratio']:g}) → 이전 행 ×{p['factor']:g}, 배율 대비 {p['magnitude']:.2f}")
    out += ["", "[hold: 쓰지 않음]"]
    for p in hold:
        out.append(f"  {p['ticker']:<6} flag {p['flag_date']}: {p['reason']}")
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser(description="NASDAQ 역분할 오염 종목 분할 비율 환산 정정")
    p.add_argument("--db-input", type=Path, help="로컬 dry-run용 DB 값(JSON). 운영 DB에 접속하지 않는다")
    p.add_argument("--split", action="append", default=[], metavar="TICKER=N@YYYY-MM-DD",
                   help="yfinance에 기록이 없는 분할을 공시(8-K/6-K)로 확인해 직접 지정 (N-for-1 역분할, "
                        "예: GCTK=15@2026-08-31). 해당 종목의 yfinance 조회를 대체한다")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    manual_splits: dict[str, list[tuple[date, float]]] = {}
    for item in args.split:
        try:
            ticker, rest = item.split("=", 1)
            n, d = rest.split("@", 1)
            manual_splits[ticker.strip()] = [(date.fromisoformat(d), 1 / float(n))]
        except ValueError:
            p.error(f"--split 형식 오류: {item} (TICKER=N@YYYY-MM-DD)")

    if args.apply and args.db_input:
        p.error("--apply는 --db-input과 함께 쓸 수 없다(DB를 직접 읽어야 함)")

    db_input = _load_db_input(args.db_input) if args.db_input else _read_db_input_from_db()
    if not db_input["flags"]:
        logger.info("정정 대상 없음")
        return

    from fomobot.batch.detect_nasdaq_quality import fetch_splits
    from fomobot.batch.nasdaq_split_refetch import CLIFF_CHECK_DAYS, apply_scale, plan_scale

    plans = []
    for ticker, flag_date in sorted(db_input["flags"].items()):
        rows = [{"date": d, "close_adj": c} for d, c in sorted(db_input["closes"].get(ticker, {}).items())
                if abs((d - flag_date).days) <= CLIFF_CHECK_DAYS]
        if ticker in manual_splits:
            logger.info("%s: 수동 지정 분할 사용 %s (yfinance 조회 생략)", ticker, manual_splits[ticker])
        splits = manual_splits[ticker] if ticker in manual_splits else fetch_splits(ticker)
        plans.append(plan_scale(ticker, flag_date, splits, rows))
    print(summarize(plans))

    if args.apply:
        apply_scale(plans)
    else:
        logger.info("dry-run — DB에 쓰지 않음 (--apply로 실행 시에만 쓰기)")


if __name__ == "__main__":
    main()
