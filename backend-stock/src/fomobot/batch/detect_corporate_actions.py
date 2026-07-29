"""
corporate action(액면분할·병합·감자 등) 후보 탐지.

일일 배치가 좁은 창(최근 7일)만 재조회하고(collect_kospi.py) pykrx의
adjusted=True가 그 창 밖 과거 이력을 소급 조정하지 않아, 분할·병합 시점에
close_adj가 구주가/신주가로 갈라지는 사고가 11종목에서 반복 발생했다.
이 모듈은 그 재발을 사전에 잡기 위한 탐지기다 — 이번 단계는 탐지 결과를
반환만 하고 corporate_action_flag에 자동 insert하지 않는다
(수동 검토 후 별도 seed, compute_rankings.py는 이미 등록된 플래그만 소비).
"""
import logging
from datetime import date, timedelta

from fomobot.db.crud import (
    get_last_real_trade_date_sync,
    get_pending_halted_flags_sync,
    get_price_range_sync,
    get_resolved_flags_sync,
)
from fomobot.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)

JUMP_LO, JUMP_HI = 0.35, 3.0
LIMIT_LO, LIMIT_HI = 0.65, 1.35  # 상/하한가(±30%) 오탐 방지 구간 — [0.35,3]과 마진 충분(조사로 확인됨)
SHARES_TOLERANCE = 0.01  # 1%
RESOLVED_SUPPRESS_TRADING_DAYS = 3  # resolved flag_date와 이 거래일수 이내면 재알림 억제

# halt 재개 알림에 고정으로 붙이는 다음 액션 안내 — 지금까지 5종목+3종목 정정에 쓴
# 것과 동일한 dry-run→승인→write 3단계 패턴을 그대로 쓰면 된다는 걸 알림 자체에
# 남겨서, 사람이 절차를 매번 새로 찾지 않고 바로 착수할 수 있게 한다.
RESUMPTION_NEXT_STEPS = (
    "다음 액션: 기존과 동일한 3단계로 진행 — "
    "(1) shares_ratio(market_cap/close_adj) 재검증으로 factor·cutoff 확정 "
    "(2) dry-run(검증 A/B) 결과 보고 후 승인 대기 "
    "(3) 승인 후 단일 트랜잭션 write + 필요 시 ranking_snapshot 재계산. "
    "자동 정정 없음 — 승인 게이트 유지."
)
# 병합/분할 비율은 이사회 결의로 임의 정수로 정해지므로(15:1, 30:1 등 실제 관측됨),
# 고정된 후보 목록 대신 "가장 가까운 정수"로 일반화한다. 2~100 범위로 제한 —
# 그 이상은 단일 corporate action으로 보기 어렵고 데이터 오류일 가능성이 커진다.
MIN_FACTOR, MAX_FACTOR = 2, 100


def _nearest_int_candidate(ratio: float) -> tuple[float, float] | None:
    """
    ratio(또는 그 역수)가 가장 가까운 정수(2~100)에 1% 이내로 근접하면
    (후보 factor, 오차) 반환. 004870(4.7571→5), 002070(30.13→30)처럼 실거래가
    섞여 후보값이 정확히 정수는 아니지만 근접한 경우까지 포괄한다.
    """
    best = None
    for value, is_inverse in ((ratio, False), (1.0 / ratio, True)):
        if value < MIN_FACTOR - 0.5 or value > MAX_FACTOR + 0.5:
            continue
        nearest = round(value)
        if nearest < MIN_FACTOR or nearest > MAX_FACTOR:
            continue
        err = abs(value - nearest) / nearest
        if err <= SHARES_TOLERANCE and (best is None or err < best[1]):
            factor = float(nearest) if not is_inverse else 1.0 / nearest
            best = (factor, err)
    return best


def _resolved_suppresses(series: list[dict], prev_idx: int, flag_date: date) -> bool:
    """
    resolved flag_date가 점프 cutoff 추정 위치(prev_idx)와 거래일 기준
    ±RESOLVED_SUPPRESS_TRADING_DAYS 이내에 있으면 True(억제 대상).

    flag_date가 series의 실제 거래일 범위 밖이면(예: lookback_days가 짧아
    조회 창에 그 날짜가 아예 없는 경우) "가장 가까운 인덱스" 탐색이
    창 경계로 잘못 clamp되어 엉뚱하게 근접 판정될 수 있다 — 그런 경우는
    억제하지 않는다(범위 밖이면 애초에 같은 이벤트인지 판단할 근거가 없음).
    """
    if flag_date < series[0]["date"] or flag_date > series[-1]["date"]:
        return False
    nearest_idx = min(range(len(series)), key=lambda k: abs((series[k]["date"] - flag_date).days))
    return abs(prev_idx - nearest_idx) <= RESOLVED_SUPPRESS_TRADING_DAYS


def detect_corporate_actions(
    market: str, lookback_days: int, suppress_resolved: bool = True,
) -> list[dict]:
    """
    price_daily에서 corporate action 의심 후보를 탐지해 반환한다(DB write 없음).

    두 신호 중 하나라도 걸리면 후보로 채택한다:
      1차(shares_ratio): (market_cap/close_adj)의 전일 대비 비율이 정수/역수
        후보(2,3,4,5,6,10 및 역수)에 1% 이내로 근접 — market_cap 양끝이
        non-null이어야 하며, 당일 실거래가 섞여도(004870 사례) 안정적이다.
      2차(halt_fallback): close_adj 인접 비율이 [0.35,3] 밖이고, 점프 양끝 중
        하나가 거래정지(당일 volume=0)에 인접 — market_cap 결측 시 대비용.

    상/하한가(±30%) 오탐 방지: close_adj 비율이 [0.65,1.35]에 있으면 두 신호
    모두 무시한다(정상적인 상한가·하한가가 [0.35,3] 임계값에 오탐되지 않도록
    이미 검증된 마진 — 025560 2026-07-28 하한가(-30%) 등).

    resolved 억제(suppress_resolved=True 기본): corporate_action_flag에서
    status=resolved인 티커의 flag_date가 이번에 잡힌 점프의 cutoff 추정일
    (prev_date)과 거래일 기준 ±3일 이내면 후보에서 제외한다 — 이미 정정
    완료된 이벤트를 매일 재알림하지 않기 위함. 같은 종목에 flag_date와
    멀리 떨어진 "새" 점프가 생기면 계속 탐지한다(재발 케이스 방지 목적).
    excluded/pending 상태는 억제하지 않는다 — 아직 미해결이라 계속 알려야 함.

    Parameters
    ----------
    market : str            "kospi" | "nasdaq"
    lookback_days : int     최근 며칠 구간을 스캔할지
    suppress_resolved : bool  resolved 이벤트 재알림 억제 여부(기본 True)

    Returns
    -------
    list[dict]  각 항목: ticker, market, prev_date, cur_date, price_ratio,
                shares_ratio(nullable), signal_type("shares_ratio"|"halt_fallback"),
                detected_signal(str), reason_guess, halt_adjacent(bool)
    """
    today = date.today()
    # 첫 날짜의 "전일" 비교가 가능하도록 조회 시작을 며칠 더 앞당긴다.
    query_start = today - timedelta(days=lookback_days + 10)
    cutoff_start = today - timedelta(days=lookback_days)

    with SyncSessionLocal() as session:
        rows = get_price_range_sync(session, market, query_start, today)
        resolved_flags = get_resolved_flags_sync(session, market) if suppress_resolved else {}

    by_ticker: dict[str, list[dict]] = {}
    for r in rows:
        by_ticker.setdefault(r["ticker"], []).append(r)

    candidates: list[dict] = []
    suppressed_count = 0

    for ticker, series in by_ticker.items():
        series.sort(key=lambda r: r["date"])
        for i in range(1, len(series)):
            prev, cur = series[i - 1], series[i]
            if cur["date"] < cutoff_start:
                continue
            if not prev["close_adj"] or not cur["close_adj"]:
                continue

            price_ratio = cur["close_adj"] / prev["close_adj"]

            # 상/하한가 오탐 방지 — 진짜 급변은 여기서 걸러진다.
            if LIMIT_LO <= price_ratio <= LIMIT_HI:
                continue

            shares_ratio_value = None
            shares_match = None
            if prev["market_cap"] and cur["market_cap"]:
                shares_prev = prev["market_cap"] / prev["close_adj"]
                shares_cur = cur["market_cap"] / cur["close_adj"]
                shares_ratio_value = shares_prev / shares_cur
                shares_match = _nearest_int_candidate(shares_ratio_value)

            is_jump = price_ratio < JUMP_LO or price_ratio > JUMP_HI
            halt_adjacent = (not prev["volume"]) or (not cur["volume"])

            fired_by_shares = shares_match is not None
            fired_by_halt_fallback = is_jump and halt_adjacent

            if not (fired_by_shares or fired_by_halt_fallback):
                continue

            # resolved 억제: 이미 정정 완료된 이벤트면 스킵
            flag_date = resolved_flags.get(ticker)
            if flag_date is not None and _resolved_suppresses(series, i - 1, flag_date):
                suppressed_count += 1
                continue

            if fired_by_shares:
                factor, err = shares_match
                signal_type = "shares_ratio"
                detected_signal = f"shares_ratio={shares_ratio_value:.4f} candidate={factor:.4f} (오차 {err*100:.2f}%)"
                reason_guess = "merge" if price_ratio > 1 else "split"
            else:
                signal_type = "halt_fallback"
                detected_signal = f"price_ratio={price_ratio:.4f} (halt-adjacent, shares 신호 없음/불일치)"
                reason_guess = "manual"

            candidates.append({
                "ticker": ticker,
                "market": market,
                "prev_date": prev["date"],
                "cur_date": cur["date"],
                "price_ratio": price_ratio,
                "shares_ratio": shares_ratio_value,
                "signal_type": signal_type,
                "detected_signal": detected_signal,
                "reason_guess": reason_guess,
                "halt_adjacent": halt_adjacent,
            })

    if suppressed_count:
        logger.info(
            "%s resolved 억제로 재알림 스킵 %d건 (이미 정정 완료된 이벤트)",
            market, suppressed_count,
        )

    if candidates:
        logger.warning(
            "%s corporate action 후보 %d건 탐지(자동 flag 미연결, 수동 검토 필요): %s",
            market, len(candidates), [c["ticker"] for c in candidates],
        )
    else:
        logger.info("%s corporate action 후보 없음 (최근 %d일)", market, lookback_days)

    return candidates


def check_halt_resumption(market: str) -> list[dict]:
    """
    status=pending AND reason=halted인 종목(현재 009310)의 거래 재개 여부를
    확인한다(DB write 없음, 재계산·정정은 트리거하지 않음 — 알림만).

    flag_date 이후 실거래일(volume>0)이 새로 생겼으면 재개로 판단한다
    (halt 시작일 자체를 별도로 저장하지 않으므로, "이 종목을 pending으로
    등록한 시점 이후 실거래가 생겼는가"를 재개 신호로 사용 — 등록 이후
    줄곧 지켜보는 용도이므로 flag_date 기준으로 충분하다).

    Returns
    -------
    list[dict]  각 항목: ticker, flag_date, last_real_trade_date(nullable), resumed(bool)
    """
    with SyncSessionLocal() as session:
        pending = get_pending_halted_flags_sync(session, market)
        results = []
        for item in pending:
            last_trade = get_last_real_trade_date_sync(session, market, item["ticker"])
            resumed = last_trade is not None and last_trade > item["flag_date"]
            results.append({
                "ticker": item["ticker"],
                "flag_date": item["flag_date"],
                "last_real_trade_date": last_trade,
                "resumed": resumed,
            })

    for r in results:
        if r["resumed"]:
            logger.warning(
                "%s %s 거래 재개 감지 — 재개 첫 실거래일 %s. %s",
                market, r["ticker"], r["last_real_trade_date"], RESUMPTION_NEXT_STEPS,
            )

    return results
