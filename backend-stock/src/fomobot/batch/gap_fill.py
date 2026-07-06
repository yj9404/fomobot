"""
랭킹 스냅샷 self-healing (gap-fill) 배치.

이 모듈이 커버하는 범위 = "고립된 단일 거래일 랭킹 구멍"의 사후 자동 복구뿐이다.
2026-07-03 KOSPI 인시던트(cron 실행 중 DB 인증 실패로 그날 랭킹이 통째로
비었던 사건)처럼, 앞뒤로는 정상인데 하루만 비는 케이스를 다음 정기 실행이
스스로 감지해 채우는 것이 목적이다.

범위 밖 — 이 배치가 자동으로 해결하지 못하고 사람에게 넘기는 것:
  - 연속 다중일 공백(거래일 2개 이상 연속으로 비어 있는 경우): 판정 방식이
    "직전·직후 거래일 모두 스냅샷이 있어야 고립 gap으로 인정"이기 때문에,
    공백 내부 날짜는 이웃도 공백이라 원리상 고립이 성립하지 않는다.
    lookback을 아무리 늘려도 이 한계 자체는 없어지지 않는다 — 연속 공백은
    "몇 개까지 스캔하느냐"가 아니라 "이웃이 있어야 채운다"는 판정 구조 자체의
    한계다. 감지는 하되(연속공백 WARNING) 자동으로는 채우지 않는다.
  - 근본 원인(Postgres 자격증명 회전 시 cron 서비스 DATABASE_URL 미동기화):
    Railway 설정 영역이라 이 배치가 손댈 수 있는 부분이 아니다. 이 배치는
    증상(비어버린 스냅샷)을 사후에 메울 뿐, 재발 자체를 막지 않는다.
"""

import logging
from dataclasses import dataclass, field
from datetime import date

from fomobot.batch.compute_rankings import compute_rankings_for_market
from fomobot.db.crud import get_recent_trading_days_sync, get_snapshot_dates_in_range_sync
from fomobot.db.session import SyncSessionLocal
from fomobot.services.calculator import PERIOD_TO_DAYS

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_TRADING_DAYS = 10
DEFAULT_CAP = 30


@dataclass
class GapScanResult:
    """단일 (market, period)에 대한 스캔 결과."""

    fillable: list[date] = field(default_factory=list)
    # 자동 복구 불가 — 사람에게 넘기는 신호 (날짜범위로 묶어 보고)
    continuous_gaps: list[tuple[date, date]] = field(default_factory=list)


def find_gaps(trading_days: list[date], existing_dates: set[date]) -> GapScanResult:
    """
    순수 함수(DB 미접근) — 거래일 목록과 기존 스냅샷 날짜 집합만으로 gap을 분류한다.

    trading_days는 오름차순 정렬된 거래일 목록이어야 한다.
    맨 앞/맨 뒤 거래일은 "이웃 앵커"가 없어 고립 판정 대상에서 제외한다
    (맨 뒤 = 이번 실행의 정기 계산이 책임지는 당일치).
    """
    result = GapScanResult()
    if len(trading_days) < 3:
        return result

    missing_set = {d for d in trading_days if d not in existing_dates}

    # 고립 단일일 gap: 직전·직후 거래일 모두 존재해야 "고립"으로 인정.
    for i in range(1, len(trading_days) - 1):
        d = trading_days[i]
        if d in missing_set and trading_days[i - 1] not in missing_set and trading_days[i + 1] not in missing_set:
            result.fillable.append(d)

    # 연속 공백: 거래일 2개 이상이 연속으로 비어 있으면 샌드위치로 못 잡으므로
    # 별도 집계해 (시작, 끝) 날짜범위로 보고한다.
    run: list[date] = []
    for d in trading_days:
        if d in missing_set:
            run.append(d)
        else:
            if len(run) >= 2:
                result.continuous_gaps.append((run[0], run[-1]))
            run = []
    if len(run) >= 2:
        result.continuous_gaps.append((run[0], run[-1]))

    return result


def scan_market(
    market: str, lookback: int = DEFAULT_LOOKBACK_TRADING_DAYS
) -> dict[str, GapScanResult]:
    """market의 각 period에 대해 최근 lookback 거래일 구간을 스캔한다."""
    with SyncSessionLocal() as session:
        # 앞뒤 앵커용 여유 2일을 더 읽는다 (맨 앞/맨 뒤는 고립 판정에서 제외되므로).
        trading_days = get_recent_trading_days_sync(session, market, lookback + 2)
        if len(trading_days) < 3:
            logger.info("%s: 거래일이 %d개뿐이라 gap-fill 스캔 스킵", market, len(trading_days))
            return {}

        results: dict[str, GapScanResult] = {}
        for period in PERIOD_TO_DAYS:
            existing = get_snapshot_dates_in_range_sync(session, market, period, trading_days)
            results[period] = find_gaps(trading_days, existing)

    return results


def plan_fill_jobs(
    scan: dict[str, GapScanResult], cap: int = DEFAULT_CAP
) -> tuple[dict[date, list[str]], int]:
    """
    (period, date) 단위 fillable 후보를 date별로 묶어 실행 계획을 만든다.
    cap을 넘으면 오래된 날짜부터 우선 채우고 나머지는 다음 실행으로 이월한다.

    Returns
    -------
    (jobs_by_date, deferred_count)
        jobs_by_date : {date: [period, ...]} — 이번 실행에서 채울 대상
        deferred_count : cap 초과로 다음 실행으로 이월된 (period, date) 조합 수
    """
    candidates: list[tuple[date, str]] = []
    for period, result in scan.items():
        for d in result.fillable:
            candidates.append((d, period))

    # 오래된 gap부터 우선 처리 (날짜 오름차순, 동일 날짜 내에선 PERIOD_TO_DAYS 순서)
    period_order = {p: i for i, p in enumerate(PERIOD_TO_DAYS)}
    candidates.sort(key=lambda x: (x[0], period_order.get(x[1], 99)))

    accepted = candidates[:cap]
    deferred = candidates[cap:]

    jobs_by_date: dict[date, list[str]] = {}
    for d, period in accepted:
        jobs_by_date.setdefault(d, []).append(period)

    return jobs_by_date, len(deferred)


def run_gap_fill_for_market(
    market: str,
    lookback: int = DEFAULT_LOOKBACK_TRADING_DAYS,
    cap: int = DEFAULT_CAP,
    dry_run: bool = False,
) -> dict:
    """
    market의 gap-fill을 실행한다 (정기 cron과 별도로 도는 전용 cron에서 호출).

    dry_run=True면 스캔·계획만 하고 실제 계산/저장은 하지 않는다
    ("무엇을 채울 것인가" 목록만 필요할 때 사용 — DB 쓰기 없음).
    """
    scan = scan_market(market, lookback=lookback)

    # 연속 공백은 cap과 무관하게 항상 눈에 띄게 로깅 — 자동 복구가 안 되는
    # 진짜 위험 신호이므로 cap 초과(단순 이월) 로그보다 레벨/문구를 더 명확히 한다.
    for period, result in scan.items():
        for start, end in result.continuous_gaps:
            logger.warning(
                "[연속공백 — 자동복구 불가] %s %s: %s ~ %s 랭킹 스냅샷이 연속으로 비어 있음. "
                "샌드위치 판정 구조상 self-healing으로 못 채움 — 원인 확인 후 수동 backfill 필요.",
                market, period, start, end,
            )

    jobs_by_date, deferred_count = plan_fill_jobs(scan, cap=cap)

    if deferred_count:
        logger.info(
            "%s: gap-fill cap(%d) 초과로 %d건 다음 실행으로 이월",
            market, cap, deferred_count,
        )

    total_jobs = sum(len(periods) for periods in jobs_by_date.values())
    report = {
        "market": market,
        "dates_to_fill": {d: list(periods) for d, periods in sorted(jobs_by_date.items())},
        "total_period_date_jobs": total_jobs,
        "deferred_count": deferred_count,
        "continuous_gaps": {
            period: list(result.continuous_gaps)
            for period, result in scan.items()
            if result.continuous_gaps
        },
    }

    if dry_run:
        logger.info("%s: gap-fill dry-run — %d건 채울 예정 (실행 안 함)", market, total_jobs)
        return report

    filled = 0
    for d, periods in sorted(jobs_by_date.items()):
        try:
            count = compute_rankings_for_market(market, snapshot_date=d, periods=periods)
            filled += count
            logger.info(
                "%s: gap-fill %s (%s) → %d건 저장", market, d, ",".join(periods), count
            )
        except Exception:
            logger.exception("%s: gap-fill %s (%s) 실패", market, d, ",".join(periods))

    report["filled_records"] = filled
    return report


def run_gap_fill_today(dry_run: bool = False) -> None:
    """KOSPI + NASDAQ gap-fill을 모두 실행한다."""
    for market in ("kospi", "nasdaq"):
        try:
            run_gap_fill_for_market(market, dry_run=dry_run)
        except Exception:
            logger.exception("%s gap-fill 중 오류", market)
