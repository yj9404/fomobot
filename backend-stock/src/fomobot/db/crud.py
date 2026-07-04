from datetime import date
from typing import Sequence

from sqlalchemy import func, or_, case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from fomobot.db.models import PriceDaily, IndexDaily, RankingSnapshot, SecuritiesMaster


# ── RankingSnapshot ──────────────────────────────────────────────────────────

async def get_rankings(
    session: AsyncSession,
    market: str,
    period: str,
    top: int,
    snapshot_date: date | None = None,
    min_market_cap: int | None = None,
    max_market_cap: int | None = None,
) -> Sequence[RankingSnapshot]:
    """
    랭킹 스냅샷 조회.

    cap_tier 필터는 RankingSnapshot.market_cap 컬럼을 직접 사용한다.
    (구 PriceDaily 조인 방식 제거 — NASDAQ는 market_cap이 항상 NULL이었음)
    market_cap이 NULL 또는 0인 종목은 cap_tier 필터 적용 시 자동 제외된다.
    """
    need_cap_filter = min_market_cap is not None or max_market_cap is not None

    stmt = (
        select(RankingSnapshot)
        .where(
            RankingSnapshot.market == market,
            RankingSnapshot.period == period,
        )
        .order_by(RankingSnapshot.snapshot_date.desc(), RankingSnapshot.rank)
    )

    if need_cap_filter:
        if min_market_cap is not None:
            # mid/large: market_cap이 확인된 종목만 (NULL = 소형주 추정이므로 제외)
            stmt = stmt.where(
                RankingSnapshot.market_cap.isnot(None),
                RankingSnapshot.market_cap >= min_market_cap,
            )
            if max_market_cap is not None:
                stmt = stmt.where(RankingSnapshot.market_cap < max_market_cap)
        else:
            # small (min=None): yfinance 시총 미조회 종목(NULL)도 소형으로 포함
            # 1d 단기 급등 소형주는 yfinance market_cap이 None인 경우가 많음
            if max_market_cap is not None:
                stmt = stmt.where(
                    or_(
                        RankingSnapshot.market_cap.is_(None),
                        RankingSnapshot.market_cap < max_market_cap,
                    )
                )

    if snapshot_date:
        stmt = stmt.where(RankingSnapshot.snapshot_date == snapshot_date)

    # rank <= top 대신 LIMIT 사용: cap_tier 필터 후 상위 top개를 올바르게 반환
    stmt = stmt.limit(top)

    result = await session.execute(stmt)
    return result.scalars().all()



async def get_nearest_snapshot_date(
    session: AsyncSession,
    market: str,
    period: str,
    as_of: date,
) -> date | None:
    """as_of 이하의 가장 가까운 snapshot_date를 반환."""
    stmt = (
        select(RankingSnapshot.snapshot_date)
        .where(
            RankingSnapshot.market == market,
            RankingSnapshot.period == period,
            RankingSnapshot.snapshot_date <= as_of,
        )
        .order_by(RankingSnapshot.snapshot_date.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_snapshot_date(
    session: AsyncSession, market: str, period: str
) -> date | None:
    stmt = (
        select(RankingSnapshot.snapshot_date)
        .where(RankingSnapshot.market == market, RankingSnapshot.period == period)
        .order_by(RankingSnapshot.snapshot_date.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ── PriceDaily (배치에서 사용, sync) ─────────────────────────────────────────

def upsert_price_daily_sync(session: Session, records: list[dict]) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    if not records:
        return
    stmt = pg_insert(PriceDaily).values(records)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_price_daily",
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close_adj": stmt.excluded.close_adj,
            "volume": stmt.excluded.volume,
            "market_cap": stmt.excluded.market_cap,
        },
    )
    session.execute(stmt)
    session.commit()


def upsert_index_daily_sync(session: Session, records: list[dict]) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    if not records:
        return
    stmt = pg_insert(IndexDaily).values(records)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_index_daily",
        set_={"close_adj": stmt.excluded.close_adj},
    )
    session.execute(stmt)
    session.commit()


def upsert_ranking_snapshots_sync(session: Session, records: list[dict]) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    if not records:
        return
    stmt = pg_insert(RankingSnapshot).values(records)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_ranking_snapshot",
        set_={
            "ticker": stmt.excluded.ticker,
            "name": stmt.excluded.name,
            "return_pct": stmt.excluded.return_pct,
            "mdd_pct": stmt.excluded.mdd_pct,
            "volatility_annualized_pct": stmt.excluded.volatility_annualized_pct,
            "excess_return_pct": stmt.excluded.excess_return_pct,
            # close_price_at_snapshot: 기존 NULL만 덮어씌움 (이미 값이 있으면 유지)
            "close_price_at_snapshot": func.coalesce(
                RankingSnapshot.close_price_at_snapshot,
                stmt.excluded.close_price_at_snapshot,
            ),
            # market_cap: 새 값이 있으면 업데이트, 없으면 기존 값 유지
            "market_cap": func.coalesce(
                stmt.excluded.market_cap,
                RankingSnapshot.market_cap,
            ),
        },
    )
    session.execute(stmt)
    session.commit()


def get_price_range_sync(
    session: Session,
    market: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """배치·백테스트 계산용 가격 범위 조회 (sync)."""
    rows = session.execute(
        select(
            PriceDaily.ticker,
            PriceDaily.date,
            PriceDaily.close_adj,
            PriceDaily.volume,
            PriceDaily.market_cap,
        )
        .where(
            PriceDaily.market == market,
            PriceDaily.date >= start_date,
            PriceDaily.date <= end_date,
        )
        .order_by(PriceDaily.date)
    ).fetchall()
    return [r._asdict() for r in rows]


def get_index_range_sync(
    session: Session,
    index_code: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    rows = session.execute(
        select(IndexDaily.date, IndexDaily.close_adj)
        .where(
            IndexDaily.index_code == index_code,
            IndexDaily.date >= start_date,
            IndexDaily.date <= end_date,
        )
        .order_by(IndexDaily.date)
    ).fetchall()
    return [r._asdict() for r in rows]


def get_recent_trading_days_sync(
    session: Session,
    market: str,
    limit: int,
) -> list[date]:
    """
    market 기준 최근 거래일 목록을 오름차순으로 최대 limit개 반환한다 (gap-fill용).

    거래일 캘린더를 따로 두지 않고 price_daily에 실제로 존재하는 날짜를
    그대로 거래일 정의로 쓴다 — 시장별 휴장일(한국 공휴일 vs 미국 공휴일)이
    자동으로 반영된다.
    """
    stmt = (
        select(PriceDaily.date)
        .where(PriceDaily.market == market)
        .distinct()
        .order_by(PriceDaily.date.desc())
        .limit(limit)
    )
    rows = session.execute(stmt).scalars().all()
    return sorted(rows)


def get_snapshot_dates_in_range_sync(
    session: Session,
    market: str,
    period: str,
    dates: list[date],
) -> set[date]:
    """dates 중 (market, period) 조합으로 ranking_snapshot에 이미 존재하는 날짜 집합."""
    if not dates:
        return set()
    stmt = (
        select(RankingSnapshot.snapshot_date)
        .where(
            RankingSnapshot.market == market,
            RankingSnapshot.period == period,
            RankingSnapshot.snapshot_date.in_(dates),
        )
        .distinct()
    )
    return set(session.execute(stmt).scalars().all())


# ── SecuritiesMaster (배치용 sync, API용 async) ──────────────────────────────

def upsert_securities_master_sync(session: Session, records: list[dict]) -> None:
    """ticker+market 기준 upsert. name은 NULL이 아닌 경우에만 덮어쓴다."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    if not records:
        return
    stmt = pg_insert(SecuritiesMaster).values(records)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_securities_master",
        set_={
            "name": func.coalesce(stmt.excluded.name, SecuritiesMaster.name),
            "is_active": stmt.excluded.is_active,
            "updated_at": func.now(),
        },
    )
    session.execute(stmt)
    session.commit()


async def search_securities(
    session: AsyncSession,
    market: str,
    q: str,
    limit: int = 50,
) -> Sequence[SecuritiesMaster]:
    """ticker 접두 매칭 + 종목명 부분일치(대소문자 무시). 정확 매칭 우선 정렬."""
    stmt = (
        select(SecuritiesMaster)
        .where(SecuritiesMaster.market == market)
        .where(
            or_(
                SecuritiesMaster.ticker.ilike(q + "%"),
                SecuritiesMaster.name.ilike("%" + q + "%"),
            )
        )
        .order_by(
            case(
                (SecuritiesMaster.ticker.ilike(q), 0),
                (SecuritiesMaster.ticker.ilike(q + "%"), 1),
                else_=2,
            ),
            SecuritiesMaster.ticker,
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_security_name(
    session: AsyncSession,
    market: str,
    ticker: str,
) -> str | None:
    stmt = (
        select(SecuritiesMaster.name)
        .where(SecuritiesMaster.market == market, SecuritiesMaster.ticker == ticker)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_price_series_async(
    session: AsyncSession,
    market: str,
    ticker: str,
    start_date: date,
    end_date: date,
) -> list[tuple[date, float]]:
    """단일 종목의 날짜별 수정주가 시계열 반환 (오름차순)."""
    stmt = (
        select(PriceDaily.date, PriceDaily.close_adj)
        .where(
            PriceDaily.market == market,
            PriceDaily.ticker == ticker,
            PriceDaily.date >= start_date,
            PriceDaily.date <= end_date,
            PriceDaily.close_adj.isnot(None),
        )
        .order_by(PriceDaily.date)
    )
    result = await session.execute(stmt)
    return [(row.date, row.close_adj) for row in result.fetchall()]


async def get_price_history_bounds_async(
    session: AsyncSession,
    market: str,
    ticker: str,
) -> tuple[date | None, date | None]:
    """해당 종목의 PriceDaily 보유 이력 첫날·마지막날 반환."""
    stmt = select(
        func.min(PriceDaily.date),
        func.max(PriceDaily.date),
    ).where(
        PriceDaily.market == market,
        PriceDaily.ticker == ticker,
    )
    result = await session.execute(stmt)
    row = result.one()
    return row[0], row[1]


async def get_global_price_min_date_async(
    session: AsyncSession,
    market: str,
) -> date | None:
    """시장 전체 PriceDaily에서 가장 이른 날짜 반환."""
    stmt = select(func.min(PriceDaily.date)).where(PriceDaily.market == market)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_last_trading_day_async(
    session: AsyncSession,
    market: str,
    as_of: date | None = None,
) -> date | None:
    """
    market 기준으로 price_daily에 실제 존재하는 가장 최근 거래일을 반환한다.

    as_of가 주어지면 그 날짜 이하 중 가장 최근 거래일을 반환한다.
    date.today()는 휴장일(주말·공휴일)일 수 있어 "거래일"의 대용으로 쓰면
    안 되므로, 거래일이 필요한 모든 곳은 이 함수로 실측해야 한다.
    """
    stmt = select(func.max(PriceDaily.date)).where(PriceDaily.market == market)
    if as_of is not None:
        stmt = stmt.where(PriceDaily.date <= as_of)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def get_last_trading_day_sync(
    session: Session,
    market: str,
    as_of: date | None = None,
) -> date | None:
    """get_last_trading_day_async의 sync 버전 (배치용)."""
    stmt = select(func.max(PriceDaily.date)).where(PriceDaily.market == market)
    if as_of is not None:
        stmt = stmt.where(PriceDaily.date <= as_of)
    result = session.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_prices_async(
    session: AsyncSession,
    market: str,
    tickers: list[str],
) -> dict[str, float | None]:
    """
    주어진 티커 목록에 대해 price_daily 최신 날짜의 close_adj를 반환.

    오늘 주가가 없는 종목(상장폐지 등)은 반환 dict에 포함되지 않거나
    값이 None — 호출자가 None 처리해야 한다(생존 편향 유지).
    """
    if not tickers:
        return {}

    from sqlalchemy import text

    placeholders = ", ".join(f":t{i}" for i in range(len(tickers)))
    params = {f"t{i}": t for i, t in enumerate(tickers)}
    params["market"] = market

    # 단일 서브쿼리로 최신 날짜를 구한 뒤 해당 날짜의 가격만 반환.
    # 상장폐지 종목은 최신 날짜에 행이 없으므로 자연스럽게 누락된다.
    query = text(f"""
        SELECT pd.ticker, pd.close_adj
        FROM price_daily pd
        WHERE pd.market = :market
          AND pd.ticker IN ({placeholders})
          AND pd.date = (
              SELECT MAX(date)
              FROM price_daily
              WHERE market = :market
          )
    """)

    result = await session.execute(query, params)
    return {row.ticker: row.close_adj for row in result.fetchall()}
