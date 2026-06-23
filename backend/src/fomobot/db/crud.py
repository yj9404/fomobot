from datetime import date
from typing import Sequence

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from fomobot.db.models import PriceDaily, IndexDaily, RankingSnapshot


# ── RankingSnapshot ──────────────────────────────────────────────────────────

async def get_rankings(
    session: AsyncSession,
    market: str,
    period: str,
    top: int,
    snapshot_date: date | None = None,
) -> Sequence[RankingSnapshot]:
    stmt = (
        select(RankingSnapshot)
        .where(
            RankingSnapshot.market == market,
            RankingSnapshot.period == period,
            RankingSnapshot.rank <= top,
        )
        .order_by(RankingSnapshot.snapshot_date.desc(), RankingSnapshot.rank)
    )
    if snapshot_date:
        stmt = stmt.where(RankingSnapshot.snapshot_date == snapshot_date)

    result = await session.execute(stmt)
    return result.scalars().all()


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
