"""
NASDAQ 가격 데이터 품질 상시 감시 — 2026-07-29~30 세션에서 수동으로 잡은
음수(CBIO), 센티널(SVA), 내부절벽(74종목 격리) 패턴의 재발을 자동으로
잡기 위한 두 탐지기.

NASDAQ은 KOSPI와 달리 price_daily.market_cap이 전량 NULL이라
detect_corporate_actions.py의 1차 신호(shares_ratio)를 못 쓴다. 그래서
가격 절벽 + 거래량 신호만으로 판단한다(STEP2.7d에서 검증된 방식).

두 함수의 비용·신뢰도가 달라 배치 편입 방식을 분리한다:
  - detect_nasdaq_negative: WHERE 한 줄, 가볍다. 음수 가격은 명백한 오류라
    오탐 여지가 없어 자동 격리(insert)까지 이 함수가 수행한다.
    → 일일 수집 배치 끝에 편입(무겁지 않음).
  - detect_nasdaq_cliffs: 5년 윈도우 전 종목 스캔, 무겁다. 절벽은 실제
    급락(뉴스 이벤트)과 오염을 거래량 신호로만 구분하므로 오탐 여지가
    있어 이 단계는 자동 insert하지 않고 후보 목록만 반환한다(운영 확인
    후 자동 insert 전환 여부 별도 결정).
    → 주간(또는 수동) 배치로 분리.
"""
import logging
import statistics
from datetime import date, timedelta

from fomobot.db.crud import (
    get_cliff_candidates_sync,
    get_flagged_tickers_sync,
    get_last_trading_day_sync,
    get_negative_price_rows_sync,
    get_price_series_for_tickers_sync,
    get_resolved_flags_sync,
    upsert_corporate_action_flag_sync,
)
from fomobot.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)

# ── detect_nasdaq_negative ───────────────────────────────────────────────────


def detect_nasdaq_negative(market: str = "nasdaq") -> list[dict]:
    """
    price_daily에서 close_adj<=0인 행을 전수 조회해 종목별로 집계하고,
    발견 시 corporate_action_flag에 자동 격리한다
    (reason=negative_price, status=excluded).

    음수/0 가격은 auto_adjust 아티팩트나 파이프라인 센티널 값 등 명백한
    데이터 오류이며 실제 시장 이벤트로 정당화될 수 없다 — 절벽 탐지와
    달리 오탐 여지가 없으므로 자동 insert가 안전하다(사람이 나중에 정정
    필요 여부만 판단하면 됨. resolved 전환은 이번 범위 밖 — 수동 정정
    트랙에서 처리).

    분류:
      - sentinel(센티널 의심): 값이 상수로 반복 + volume=0 (파이프라인이
        진짜 가격 대신 채워넣은 placeholder로 추정, SVA 사례)
      - artifact(아티팩트 의심): 값이 변동함 (auto_adjust 배당 역산 등
        계산 과정의 부작용으로 추정, CBIO 사례)

    Returns
    -------
    list[dict]  각 항목: ticker, count, last_negative_date, is_constant,
                classification("sentinel"|"artifact")
    """
    with SyncSessionLocal() as session:
        rows = get_negative_price_rows_sync(session, market)

    if not rows:
        logger.info("%s 음수/0 가격 없음 (close_adj<=0 0건)", market.upper())
        return []

    by_ticker: dict[str, list[dict]] = {}
    for r in rows:
        by_ticker.setdefault(r["ticker"], []).append(r)

    results: list[dict] = []
    records: list[dict] = []
    for ticker, series in by_ticker.items():
        series.sort(key=lambda r: r["date"])
        values = {r["close_adj"] for r in series}
        is_constant = len(values) == 1
        all_zero_volume = all(not r["volume"] for r in series)
        classification = "sentinel" if (is_constant and all_zero_volume) else "artifact"
        last_date = series[-1]["date"]

        results.append({
            "ticker": ticker,
            "count": len(series),
            "last_negative_date": last_date,
            "is_constant": is_constant,
            "classification": classification,
        })

        detected_signal = (
            f"count={len(series)} last={last_date} value={series[-1]['close_adj']} "
            f"constant={is_constant} volume0={all_zero_volume} classification={classification}"
        )
        records.append({
            "ticker": ticker,
            "market": market,
            "flag_date": last_date,
            "reason": "negative_price",
            "status": "excluded",
            "detected_signal": detected_signal[:2000],
            "note": (
                f"detect_nasdaq_negative 자동 격리 — close_adj<=0 {len(series)}건 "
                f"({classification}). 수동 정정 트랙에서 원인 확인 필요."
            )[:2000],
        })

    with SyncSessionLocal() as session:
        upsert_corporate_action_flag_sync(session, records)

    logger.warning(
        "%s 음수/0 가격 %d종목 자동 격리: %s",
        market.upper(), len(results), [r["ticker"] for r in results],
    )
    return results


# ── detect_nasdaq_cliffs ─────────────────────────────────────────────────────

CLIFF_LO, CLIFF_HI = 0.35, 3.0
SINGLE_DAY_REVERT_LO, SINGLE_DAY_REVERT_HI = 0.8, 1.25  # 단일일 이상치(익일 복귀) 배제
STABILITY_CV_MAX = 0.12  # 전후 5일 변동계수(CV)가 이 값 미만이어야 "안정-안정"(지속절벽)
VOL_SPIKE_KEEP = 3.0      # 절벽일 거래량이 전일 대비 이 배수 이상이면 "실제 이벤트" 후보
VOL_SPIKE_ISOLATE = 2.0   # 이 배수 이하면 명백히 "격리후보" (2~3배 경계는 안전측 격리)
POST_CLIFF_ZERO_DAYS_THRESHOLD = 3  # 절벽 후 5일 중 이 값 이상 거래량0이면 격리후보
RESOLVED_SUPPRESS_TRADING_DAYS = 3  # detect_corporate_actions.py와 동일 clamp 가드
LAG_RECENT_DAYS = 5  # 절벽일이 데이터 최신일 기준 이 값 이내면 "랙 가능성"으로 분리
LOOKBACK_DAYS = 1825 + 10  # 5년 + 첫 날짜 전일 비교용 여유


def _cv(vals: list[float | None]) -> float | None:
    vals = [v for v in vals if v is not None and v > 0]
    if len(vals) < 2:
        return None
    m = statistics.mean(vals)
    if m == 0:
        return None
    return statistics.pstdev(vals) / m


def _resolved_suppresses(series: list[dict], cliff_date: date, flag_date: date) -> bool:
    """
    resolved flag_date가 절벽일과 거래일 기준 ±RESOLVED_SUPPRESS_TRADING_DAYS
    이내면 True(억제 대상). detect_corporate_actions.py의 동명 함수와 동일
    원칙 — flag_date가 series의 실제 거래일 범위 밖이면(clamp 버그 가드)
    억제하지 않는다.
    """
    if not series:
        return False
    if flag_date < series[0]["date"] or flag_date > series[-1]["date"]:
        return False
    cliff_idx = min(range(len(series)), key=lambda k: abs((series[k]["date"] - cliff_date).days))
    flag_idx = min(range(len(series)), key=lambda k: abs((series[k]["date"] - flag_date).days))
    return abs(cliff_idx - flag_idx) <= RESOLVED_SUPPRESS_TRADING_DAYS


def detect_nasdaq_cliffs(
    market: str = "nasdaq", full_scan: bool = True, suppress_resolved: bool = True,
) -> dict:
    """
    full_scan: 현재는 항상 전수 스캔(파라미터 자체는 향후 증분 스캔 모드를
    위해 시그니처에 예약해둔 것 — 지금은 무시되고 5년 윈도우 전체를 본다).

    랭킹대상(미플래그) 전 종목의 5년 윈도우 내부절벽을 전수 검출하고
    거래량 신호로 분류한다(STEP2.7d 로직 상시화, DB write 없음).

    분류 기준(STEP2.7d 그대로):
      - vol_ratio(절벽일 거래량 / 전일 거래량) <= 2배            → 격리후보
      - 절벽 후 5일 중 3일 이상 거래량 0                          → 격리후보
      - vol_ratio >= 3배 AND 절벽 후 거래 지속                    → 유지(실제 이벤트)
      - 2~3배 경계                                                → 격리후보(안전측)

    안정-안정 필터: 절벽 전후 5일의 변동계수(CV)가 모두 0.12 미만이어야
    "지속 절벽"으로 채택한다(단발성 노이즈·회복성 급등락 배제).

    resolved 억제: 이미 resolved인 티커의 flag_date에 거래일 기준 ±3일
    이내인 절벽은 재보고하지 않는다. resolved 티커는 보통 소수(현재 5개)
    이므로, 이 판정에 필요한 정확한 시계열만 별도로 조회해 거래일 기준
    최근접 인덱스로 비교한다(detect_corporate_actions.py와 동일 clamp
    가드 — flag_date가 조회 범위 밖이면 억제하지 않음). 같은 종목에
    flag_date와 무관한 "새/잔여" 절벽이 있으면 계속 탐지한다 — 실제로
    이번 세션에서 5종목을 부분 정정했고 매칭 안 된 잔여 절벽이 남아있는데,
    이런 잔여 절벽은 flag_date와 멀리 떨어져 있으므로 계속 탐지되는 게 맞다.

    최근 랙 분리: 절벽일이 데이터 최신일 기준 5일 이내면 "즉시 격리후보"가
    아니라 lag_possible로 분리한다 — yfinance가 분할을 소급 반영하는 데
    며칠 걸리는 케이스(TJGC/GIBO 등)가 다음 주간 스캔 전에 자연 해소될
    수 있어, 성급한 격리보다 재조회 권장이 더 안전하다.

    이 함수는 격리후보를 자동 insert하지 않는다 — 목록만 반환한다
    (오탐 여지가 negative_price보다 크므로, 운영 확인 후 자동 insert
    전환 여부를 별도로 결정한다).

    Returns
    -------
    dict  keys: keep(list[dict]), isolate_candidates(list[dict]),
                lag_possible(list[dict]), suppressed_count(int),
                scanned_candidate_rows(int)
    """
    today = date.today()
    window_start = today - timedelta(days=LOOKBACK_DAYS)

    with SyncSessionLocal() as session:
        flagged = get_flagged_tickers_sync(session, market, statuses=("excluded", "pending"))
        resolved = get_resolved_flags_sync(session, market) if suppress_resolved else {}
        candidate_rows = get_cliff_candidates_sync(session, market, window_start)
        overall_latest = get_last_trading_day_sync(session, market) or today

    # resolved 억제 판정에 필요한 정확한 시계열은 후보에 등장하고 resolved인
    # 소수 티커만 조회한다(전 종목 시계열을 다시 끌어오지 않기 위함).
    resolved_series_by_ticker: dict[str, list[dict]] = {}
    if suppress_resolved and resolved:
        candidate_tickers = {r["ticker"] for r in candidate_rows}
        need_series = sorted(candidate_tickers & set(resolved.keys()))
        if need_series:
            with SyncSessionLocal() as session:
                rows = get_price_series_for_tickers_sync(session, market, need_series, window_start, today)
            for r in rows:
                resolved_series_by_ticker.setdefault(r["ticker"], []).append(r)
            for t in resolved_series_by_ticker:
                resolved_series_by_ticker[t].sort(key=lambda r: r["date"])

    per_ticker_cliffs: dict[str, list[dict]] = {}
    suppressed_count = 0

    for r in candidate_rows:
        ticker = r["ticker"]
        if ticker in flagged:
            continue

        cm1, c0 = r["cm1"], r["c0"]
        ratio = c0 / cm1

        # 단일일 이상치 배제: 익일이 절벽 이전 수준으로 복귀하면 지속절벽 아님
        cp1 = r["cp1"]
        if cp1 is not None and cp1 > 0 and SINGLE_DAY_REVERT_LO <= (cp1 / cm1) <= SINGLE_DAY_REVERT_HI:
            continue

        before = [r["cm5"], r["cm4"], r["cm3"], r["cm2"], r["cm1"]]
        after = [r["cp1"], r["cp2"], r["cp3"], r["cp4"], r["cp5"]]
        cvb, cva = _cv(before), _cv(after)
        if not (cvb is not None and cva is not None and cvb < STABILITY_CV_MAX and cva < STABILITY_CV_MAX):
            continue  # 안정-안정 패턴 아님 = 지속절벽 아님(단순 변동성)

        # resolved 억제
        flag_date = resolved.get(ticker)
        if flag_date is not None:
            series = resolved_series_by_ticker.get(ticker, [])
            if _resolved_suppresses(series, r["date"], flag_date):
                suppressed_count += 1
                continue

        vm1 = r["vm1"] or 0
        v0 = r["v0"] or 0
        vol_ratio = (v0 / vm1) if vm1 > 0 else (float("inf") if v0 > 0 else 0.0)

        after_vols = [r["vp1"], r["vp2"], r["vp3"], r["vp4"], r["vp5"]]
        zero_days_after = sum(1 for v in after_vols if v is not None and v == 0)

        if vol_ratio >= VOL_SPIKE_KEEP and zero_days_after < POST_CLIFF_ZERO_DAYS_THRESHOLD:
            decision = "keep"
            vol_reason = f"거래량 급증({vol_ratio:.2f}x) + 이후 거래 지속"
        elif vol_ratio <= VOL_SPIKE_ISOLATE:
            decision = "isolate_candidate"
            vol_reason = f"거래량 급증없음(비율 {vol_ratio:.2f}x)"
        elif zero_days_after >= POST_CLIFF_ZERO_DAYS_THRESHOLD:
            decision = "isolate_candidate"
            vol_reason = f"절벽후 5일중 {zero_days_after}일 거래량0"
        else:  # 2~3배 경계
            decision = "isolate_candidate"
            vol_reason = f"경계구간 거래량비율({vol_ratio:.2f}x), 안전측 격리"

        is_recent = (overall_latest - r["date"]).days <= LAG_RECENT_DAYS

        per_ticker_cliffs.setdefault(ticker, []).append({
            "ticker": ticker,
            "cliff_date": r["date"],
            "prev_close": cm1,
            "cur_close": c0,
            "ratio": ratio,
            "vol_ratio": vol_ratio,
            "zero_days_after": zero_days_after,
            "decision": decision,
            "vol_reason": vol_reason,
            "is_recent": is_recent,
        })

    # 종목 단위 집계: 하나라도 isolate_candidate면 종목 전체를 isolate_candidates로
    # (STEP2.7d와 동일 원칙 — 종목당 격리는 all-or-nothing). 단, 남은 isolate 절벽이
    # 전부 최근(랙 가능성)이면 lag_possible로 분리해 즉시 격리 대상에서 뺀다.
    keep, isolate_candidates, lag_possible = [], [], []
    for ticker, cliffs in per_ticker_cliffs.items():
        isolate_cliffs = [c for c in cliffs if c["decision"] == "isolate_candidate"]
        if not isolate_cliffs:
            keep.append({"ticker": ticker, "cliffs": cliffs})
            continue

        old_isolate = [c for c in isolate_cliffs if not c["is_recent"]]
        if old_isolate:
            isolate_candidates.append({"ticker": ticker, "cliffs": cliffs, "isolate_cliffs": old_isolate})
        else:
            lag_possible.append({"ticker": ticker, "cliffs": cliffs, "isolate_cliffs": isolate_cliffs})

    if suppressed_count:
        logger.info(
            "%s resolved 억제로 재알림 스킵 %d건 (이미 정정 완료된 이벤트 근접)",
            market, suppressed_count,
        )

    if isolate_candidates:
        logger.warning(
            "%s 절벽 격리후보 %d종목 탐지(자동 flag 미연결, 수동 검토 필요): %s",
            market, len(isolate_candidates), [c["ticker"] for c in isolate_candidates],
        )
    if lag_possible:
        logger.info(
            "%s 최근 %d일 이내 절벽 %d종목 — 랙 가능성, 재조회 권장(즉시 격리 대상 아님): %s",
            market, LAG_RECENT_DAYS, len(lag_possible), [c["ticker"] for c in lag_possible],
        )
    if not isolate_candidates and not lag_possible:
        logger.info("%s 절벽 후보 없음 (유지 %d종목)", market, len(keep))

    return {
        "keep": keep,
        "isolate_candidates": isolate_candidates,
        "lag_possible": lag_possible,
        "suppressed_count": suppressed_count,
        "scanned_candidate_rows": len(candidate_rows),
    }
