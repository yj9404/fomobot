"""
NASDAQ 역분할 오염 정정 — 분할이 확인된 종목의 전체 이력을 yfinance에서 다시 받아 덮어쓴다.

배경: 일일 수집기는 최근 7일만 다시 받아 업서트하므로(collect_nasdaq.run_nasdaq_collection),
역분할 직후 수집은 그 구간만 분할 반영 값으로 덮어쓰고 이전 행은 옛 값으로 남긴다.
그 경계가 가격 절벽이다. yfinance raw Close(auto_adjust=False)가 분할을 소급 반영한
종목은 전체 이력을 다시 받아 같은 업서트로 덮어쓰면 배율·경계를 추정하지 않고도 정정된다
(2026-10 샘플 6종목 DB 행으로 경계가 깨끗함을 확인, 재수집 값은 절벽 이후 DB와 일치).

모든 종목이 그런 것은 아니다. 2026-10-26 dry-run에서 CPOP·IPDN·IZM·BTLN·DLXY·GMEX·IMMP는
yfinance 원본 자체가 분할일에 절벽을 그대로 갖고 있어(분할 이력은 있는데 가격은 미조정),
재수집해도 절벽이 남는다. 이런 종목은 hold가 되며, 정정하려면 분할 비율로 이전 행을 직접
환산해야 한다 (이 모듈의 범위 밖).

정정 대상 판정은 plan_refetch가 하며, 아래 중 하나라도 어긋나면 hold(쓰지 않음)다:
  - yfinance 분할 이력에서 flag_date 근처의 역분할이 확인되지 않음
  - 재수집한 시계열에 flag_date ±CLIFF_CHECK_DAYS일 안에 절벽이 남아 있음
  - (db_closes가 있으면) 절벽 이후 DB 종가가 재수집 값과 크게 다름 — 같은 소스인데 다르면
    분할 외 요인이 섞였다는 신호
"""

import logging
import statistics
import time
from datetime import date, timedelta

from fomobot.batch import collect_nasdaq
from fomobot.batch.detect_nasdaq_quality import CLIFF_HI, CLIFF_LO, SPLIT_WINDOW_DAYS, fetch_splits
from fomobot.db.crud import upsert_corporate_action_flag_sync, upsert_price_daily_sync
from fomobot.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)

MARKET = "nasdaq"
CLIFF_CHECK_DAYS = 10          # 정정 후 flag_date 앞뒤로 절벽이 없어야 하는 구간(달력일)
SPLIT_BEFORE_TOLERANCE = 3     # flag_date보다 이만큼 앞선 분할까지 인정 (수동 격리 flag_date 오차 여유)
MIN_ROWS_AROUND = 2            # 절벽 앞뒤 CLIFF_CHECK_DAYS 안에 있어야 하는 재수집 최소 행 수
FIRST_DATE_TOLERANCE_DAYS = 7  # 재수집 첫 행이 DB 최초 거래일보다 이만큼까지 늦는 건 허용 (주말·휴장)
DB_MISMATCH_MEDIAN = 0.02      # 절벽 이후 DB 종가 vs 재수집 종가 상대차 중앙값 허용치
UPSERT_CHUNK = 1000
DOWNLOAD_DELAY_SEC = 1.0


def find_cliffs(records: list[dict]) -> list[dict]:
    """연속 거래일 종가 비율이 [CLIFF_LO, CLIFF_HI] 밖인 지점 — [{date, ratio}]."""
    rows = sorted((r for r in records if r["close_adj"] and r["close_adj"] > 0), key=lambda r: r["date"])
    cliffs = []
    for prev, cur in zip(rows, rows[1:]):
        ratio = cur["close_adj"] / prev["close_adj"]
        if ratio < CLIFF_LO or ratio > CLIFF_HI:
            cliffs.append({"date": cur["date"], "ratio": ratio})
    return cliffs


def plan_refetch(
    ticker: str,
    flag_date: date,
    splits: list[tuple[date, float]] | None,
    records: list[dict],
    db_closes: dict[date, float] | None = None,
    first_date: date | None = None,
) -> dict:
    """
    재수집 결과로 이 종목을 정정해도 되는지 판정한다 (DB 접근 없음).

    Returns
    -------
    dict  category("fixable"|"hold"), reason, split_date, split_ratio, rows,
          remaining_cliffs(flag_date 근처 밖에 남은 절벽 — 실제 이벤트이거나 다른 오염),
          db_mismatch(중앙값 상대차, db_closes가 없으면 None)
    """
    plan = {
        "ticker": ticker, "flag_date": flag_date, "category": "hold", "reason": "",
        "split_date": None, "split_ratio": None, "rows": len(records),
        "remaining_cliffs": [], "db_mismatch": None,
    }
    if not records:
        plan["reason"] = "재수집 응답 없음"
        return plan

    match = next(
        ((d, r) for d, r in sorted(splits or [])
         if r < 1 and -SPLIT_BEFORE_TOLERANCE <= (d - flag_date).days <= SPLIT_WINDOW_DAYS),
        None,
    )
    if match is None:
        plan["reason"] = "yfinance 분할 이력에서 역분할 미확인" + (" (조회 실패/빈 응답)" if not splits else "")
        return plan
    plan["split_date"], plan["split_ratio"] = match

    # 절벽 앞뒤 데이터가 충분해야 "절벽 없음"이 의미 있다 (거의 빈 응답이 공허하게 통과하는 것 방지)
    dates = [r["date"] for r in records]
    before = sum(1 for d in dates if 0 < (flag_date - d).days <= CLIFF_CHECK_DAYS)
    after = sum(1 for d in dates if 0 <= (d - flag_date).days <= CLIFF_CHECK_DAYS)
    if before < MIN_ROWS_AROUND or after < MIN_ROWS_AROUND:
        plan["reason"] = f"절벽 앞뒤 재수집 행 부족 (앞 {before}, 뒤 {after})"
        return plan
    # 재수집 이력이 DB보다 짧으면 DB의 더 오래된 행이 옛 값으로 남아 재수집 시작점에 새 경계가 생긴다
    if first_date is not None and min(dates) > first_date + timedelta(days=FIRST_DATE_TOLERANCE_DAYS):
        plan["reason"] = f"재수집 이력({min(dates)}~)이 DB 최초 거래일({first_date})보다 짧음"
        return plan

    cliffs = find_cliffs(records)
    near = [c for c in cliffs if abs((c["date"] - flag_date).days) <= CLIFF_CHECK_DAYS]
    plan["remaining_cliffs"] = [c for c in cliffs if c not in near]
    if near:
        plan["reason"] = "재수집 후에도 절벽 잔존: " + ", ".join(f"{c['date']} x{c['ratio']:.2f}" for c in near)
        return plan

    if db_closes:
        new_closes = {r["date"]: r["close_adj"] for r in records}
        diffs = [abs(new_closes[d] / c - 1) for d, c in db_closes.items()
                 if d >= flag_date and d in new_closes and c]
        if diffs:
            plan["db_mismatch"] = statistics.median(diffs)
            if plan["db_mismatch"] > DB_MISMATCH_MEDIAN:
                plan["reason"] = f"절벽 이후 DB 종가와 재수집 값 불일치 (중앙값 상대차 {plan['db_mismatch']:.1%})"
                return plan

    plan["category"] = "fixable"
    plan["reason"] = f"역분할 확인 {plan['split_date']} (비율 {plan['split_ratio']:g}), 재수집 시 절벽 해소"
    return plan


def fetch_history(ticker: str, start: date, end: date) -> list[dict]:
    """collect_nasdaq과 같은 다운로드·변환으로 price_daily 레코드를 만든다 (end는 exclusive)."""
    df = collect_nasdaq._download_batch([ticker], start.isoformat(), end.isoformat())
    return collect_nasdaq._parse_batch_df(df, [ticker], MARKET)


def build_plans(
    flags: dict[str, date],
    start: date,
    end: date,
    first_dates: dict[str, date] | None = None,
    db_closes: dict[str, dict[date, float]] | None = None,
) -> tuple[list[dict], dict[str, list[dict]]]:
    """flags({ticker: flag_date})마다 분할 이력·전체 이력을 받아 plan_refetch한다. (plans, records_by_ticker)"""
    plans, records_by_ticker = [], {}
    for ticker, flag_date in sorted(flags.items()):
        # DB의 가장 오래된 행부터 받아야 재수집 구간 시작점에 새 경계가 생기지 않는다.
        # DB에 없는 과거 행을 새로 채우지는 않으므로 최초 거래일을 우선한다.
        t_start = (first_dates or {}).get(ticker, start)
        try:
            records = fetch_history(ticker, t_start, end)
            plan = plan_refetch(
                ticker, flag_date, fetch_splits(ticker), records,
                (db_closes or {}).get(ticker), (first_dates or {}).get(ticker),
            )
        except Exception as e:
            logger.warning("%s 재수집 실패", ticker, exc_info=True)
            records = []
            plan = plan_refetch(ticker, flag_date, None, [])
            plan["reason"] = f"재수집 중 예외: {type(e).__name__}: {e}"
        plans.append(plan)
        if plan["category"] == "fixable":
            records_by_ticker[ticker] = records
        time.sleep(DOWNLOAD_DELAY_SEC)
    return plans, records_by_ticker


def apply_refetch(plans: list[dict], records_by_ticker: dict[str, list[dict]]) -> None:
    """fixable 종목마다 한 트랜잭션으로 가격을 덮어쓰고 격리 flag를 resolved로 전환한다."""
    for plan in plans:
        if plan["category"] != "fixable":
            continue
        ticker = plan["ticker"]
        records = records_by_ticker[ticker]
        with SyncSessionLocal() as session:
            for i in range(0, len(records), UPSERT_CHUNK):
                upsert_price_daily_sync(session, records[i:i + UPSERT_CHUNK], commit=False)
            # upsert_corporate_action_flag_sync가 같은 세션에서 커밋한다 (가격+flag 원자적)
            upsert_corporate_action_flag_sync(session, [{
                "ticker": ticker,
                "market": MARKET,
                "flag_date": plan["flag_date"],
                "reason": "split",
                "status": "resolved",
                "detected_signal": plan["reason"][:2000],
                "note": (
                    f"yfinance 전체 이력 재수집으로 정정({len(records)}행, {records[0]['date']}~{records[-1]['date']}). "
                    f"분할 {plan['split_date']} 비율 {plan['split_ratio']:g}."
                )[:2000],
            }])
        logger.info("%s 정정 완료: %d행 덮어쓰기, flag resolved", ticker, len(records))
