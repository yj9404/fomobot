"""
NASDAQ 역분할 오염 종목 정정(1회성) — yfinance 전체 이력 재수집으로 price_daily를 덮어쓴다.

배경과 판정 기준은 fomobot.batch.nasdaq_split_refetch 모듈 docstring 참조.
대상은 corporate_action_flag의 nasdaq / reason=split / status=excluded 종목이다
(2026-10-26 수동 격리 49종목 + 이후 자동 격리분). 확인된 종목만 쓰고 나머지는 hold로 남긴다.

동작 (기본 --dry-run, --apply를 줘야만 DB에 쓴다):
  1. 대상 종목과 flag_date, DB 최초 거래일을 읽는다 (--db-input이면 파일, 아니면 DB).
  2. 종목마다 yfinance 전체 이력 + 분할 이력을 받아 plan_refetch로 판정한다.
  3. dry-run: 콘솔 요약 + --out 폴더에 summary.txt. --apply: fixable 종목마다 한 트랜잭션으로
     가격을 덮어쓰고 flag를 resolved로 바꾼다.

DB 입력: 로컬 dry-run은 운영 DB에 접속하지 않도록 --db-input 파일을 쓴다 (--apply와는 함께 쓸 수 없다).
  {"flags":      {"EHGO": "2026-10-14", ...},                    # 필수: ticker → flag_date
   "first_date": {"EHGO": "2021-10-20", ...},                    # 선택: DB 최초 거래일 (없으면 --start)
   "closes":     {"EHGO": {"2026-10-14": 2.871, ...}}}           # 선택: 절벽 이후 DB 종가 대조용

실행 (Railway 셸, 일일 수집 cron과 겹치지 않게):
    cd backend-stock
    python scripts/refetch_nasdaq_splits.py                    # dry-run
    python scripts/refetch_nasdaq_splits.py --apply            # 쓰기
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
logger = logging.getLogger("refetch_nasdaq_splits")


def _read_db_input_from_db() -> dict:
    from sqlalchemy import text

    from fomobot.db.session import SyncSessionLocal

    with SyncSessionLocal() as s:
        flags = {t: d for t, d in s.execute(text(
            "SELECT ticker, flag_date FROM corporate_action_flag "
            "WHERE market = 'nasdaq' AND reason = 'split' AND status = 'excluded'")).fetchall()}
        first_date = {t: d for t, d in s.execute(text(
            "SELECT ticker, MIN(date) FROM price_daily WHERE market = 'nasdaq' "
            "AND ticker = ANY(:t) GROUP BY ticker"), {"t": list(flags)}).fetchall()}
        closes: dict[str, dict] = {}
        for t, d, c in s.execute(text(
            "SELECT p.ticker, p.date, p.close_adj FROM price_daily p "
            "JOIN corporate_action_flag f ON f.ticker = p.ticker AND f.market = p.market "
            "WHERE p.market = 'nasdaq' AND f.reason = 'split' AND f.status = 'excluded' "
            "AND p.date >= f.flag_date")).fetchall():
            closes.setdefault(t, {})[d] = c
    return {"flags": flags, "first_date": first_date, "closes": closes}


def _load_db_input(path: Path) -> dict:
    raw = json.load(open(path, encoding="utf-8"))
    return {
        "flags": {t: date.fromisoformat(d) for t, d in raw["flags"].items()},
        "first_date": {t: date.fromisoformat(d) for t, d in (raw.get("first_date") or {}).items()},
        "closes": {t: {date.fromisoformat(d): c for d, c in m.items()} for t, m in (raw.get("closes") or {}).items()},
    }


def summarize(plans: list[dict]) -> str:
    fix = [p for p in plans if p["category"] == "fixable"]
    hold = [p for p in plans if p["category"] == "hold"]
    out = [f"종목 {len(plans)}개 — fixable {len(fix)}, hold {len(hold)}", "", "[fixable: 덮어쓰기 대상]"]
    for p in fix:
        mm = f", DB대조 {p['db_mismatch']:.2%}" if p["db_mismatch"] is not None else ", DB대조 안 함"
        out.append(f"  {p['ticker']:<6} 절벽 {p['flag_date']} / 분할 {p['split_date']} ({p['split_ratio']:g}) "
                   f"/ {p['rows']}행{mm}")
        if p["remaining_cliffs"]:
            out.append("         남는 다른 절벽(정정 범위 밖, 별도 확인): "
                       + ", ".join(f"{c['date']} x{c['ratio']:.2f}" for c in p["remaining_cliffs"]))
    out += ["", "[hold: 쓰지 않음]"]
    for p in hold:
        out.append(f"  {p['ticker']:<6} 절벽 {p['flag_date']}: {p['reason']}")
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser(description="NASDAQ 역분할 오염 종목 yfinance 전체 이력 재수집")
    p.add_argument("--start", type=date.fromisoformat, default=date(2020, 1, 1),
                   help="재수집 시작일 (DB 최초 거래일이 이보다 이르면 그 날짜부터)")
    p.add_argument("--db-input", type=Path, help="로컬 dry-run용 DB 값(JSON). 운영 DB에 접속하지 않는다")
    p.add_argument("--out", type=Path, default=Path("refetch_nasdaq_out"))
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    if args.apply and args.db_input:
        p.error("--apply는 --db-input과 함께 쓸 수 없다(DB를 직접 읽어야 함)")

    db_input = _load_db_input(args.db_input) if args.db_input else _read_db_input_from_db()
    if not db_input["flags"]:
        logger.info("정정 대상 없음")
        return

    from fomobot.batch.nasdaq_split_refetch import apply_refetch, build_plans

    # 오늘 행은 장중 부분 값일 수 있어 어제까지만 받는다 (end는 exclusive라 오늘 날짜)
    plans, records_by_ticker = build_plans(
        db_input["flags"], args.start, date.today(), db_input["first_date"], db_input["closes"])
    summary = summarize(plans)
    print(summary)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.txt").write_text(summary, encoding="utf-8")
    logger.info("상세: %s", args.out.resolve())

    if args.apply:
        apply_refetch(plans, records_by_ticker)
    else:
        logger.info("dry-run — DB에 쓰지 않음 (--apply로 실행 시에만 쓰기)")


if __name__ == "__main__":
    main()
