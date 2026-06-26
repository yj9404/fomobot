from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from realestate.db.models import (
    ReCollectionLog,
    ReMonthlystat,
    ReRankingSnapshot,
    ReTransaction,
)


# ── 비동기 (API용) ─────────────────────────────────────────────────────

async def get_latest_snapshot_ym(
    session: AsyncSession,
    region_level: str,
    period: str,
) -> str | None:
    result = await session.execute(
        select(ReRankingSnapshot.snapshot_ym)
        .where(
            ReRankingSnapshot.region_level == region_level,
            ReRankingSnapshot.period == period,
        )
        .order_by(ReRankingSnapshot.snapshot_ym.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_rankings_async(
    session: AsyncSession,
    region_level: str,
    period: str,
    snapshot_ym: str,
    top: int,
    sigungu_filter: str | None = None,
) -> list[ReRankingSnapshot]:
    q = (
        select(ReRankingSnapshot)
        .where(
            ReRankingSnapshot.region_level == region_level,
            ReRankingSnapshot.period == period,
            ReRankingSnapshot.snapshot_ym == snapshot_ym,
        )
        .order_by(
            ReRankingSnapshot.data_status,   # 'ok' < 'insufficient' etc. (알파벳순)
            ReRankingSnapshot.rank.asc().nulls_last(),
        )
    )
    if sigungu_filter:
        q = q.where(ReRankingSnapshot.sigungu_code.like(f"{sigungu_filter[:2]}%"))
    if top > 0:
        # data_status='ok' 기준 top N + excluded 모두 반환
        q = q.limit(top + 500)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_region_monthly_stats_async(
    session: AsyncSession,
    sigungu_code: str,
    eupmyeondong: str | None,
    start_ym: str,
    end_ym: str,
) -> list[ReMonthlystat]:
    q = (
        select(ReMonthlystat)
        .where(
            ReMonthlystat.sigungu_code == sigungu_code,
            ReMonthlystat.eupmyeondong == eupmyeondong,
            ReMonthlystat.deal_ym >= start_ym,
            ReMonthlystat.deal_ym <= end_ym,
        )
        .order_by(ReMonthlystat.deal_ym)
    )
    result = await session.execute(q)
    return list(result.scalars().all())


# ── 동기 (배치용) ──────────────────────────────────────────────────────

def upsert_transactions_sync(session: Session, records: list[dict[str, Any]]) -> int:
    if not records:
        return 0
    stmt = (
        insert(ReTransaction)
        .values(records)
        .on_conflict_do_nothing(constraint="uq_re_transaction")
    )
    result = session.execute(stmt)
    session.commit()
    return result.rowcount


def upsert_collection_log_sync(
    session: Session,
    sigungu_code: str,
    deal_ym: str,
    status: str,
    transaction_count: int = 0,
    error_message: str | None = None,
) -> None:
    stmt = (
        insert(ReCollectionLog)
        .values(
            sigungu_code=sigungu_code,
            deal_ym=deal_ym,
            status=status,
            transaction_count=transaction_count,
            error_message=error_message,
        )
        .on_conflict_do_update(
            constraint="uq_re_collection_log",
            set_={
                "status": status,
                "transaction_count": transaction_count,
                "error_message": error_message,
                "collected_at": text("now()"),
            },
        )
    )
    session.execute(stmt)
    session.commit()


def get_done_collection_pairs_sync(session: Session, sigungu_code: str) -> set[str]:
    """이미 수집 완료(success/empty)된 deal_ym 집합을 반환한다."""
    result = session.execute(
        select(ReCollectionLog.deal_ym)
        .where(
            ReCollectionLog.sigungu_code == sigungu_code,
            ReCollectionLog.status.in_(["success", "empty"]),
        )
    )
    return {row[0] for row in result}


def upsert_monthly_stats_sync(session: Session, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    stmt = (
        insert(ReMonthlystat)
        .values(records)
        .on_conflict_do_update(
            constraint="uq_re_monthly_stat",
            set_={
                "median_price_per_sqm": text("excluded.median_price_per_sqm"),
                "transaction_count": text("excluded.transaction_count"),
                "updated_at": text("now()"),
            },
        )
    )
    session.execute(stmt)
    session.commit()


def upsert_ranking_snapshots_sync(session: Session, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    stmt = (
        insert(ReRankingSnapshot)
        .values(records)
        .on_conflict_do_update(
            constraint="uq_re_ranking_snapshot",
            set_={
                "rank": text("excluded.rank"),
                "start_price": text("excluded.start_price"),
                "end_price": text("excluded.end_price"),
                "change_pct": text("excluded.change_pct"),
                "start_tx_count": text("excluded.start_tx_count"),
                "end_tx_count": text("excluded.end_tx_count"),
                "data_status": text("excluded.data_status"),
                "insufficient_reason": text("excluded.insufficient_reason"),
                "created_at": text("now()"),
            },
        )
    )
    session.execute(stmt)
    session.commit()


def get_monthly_stats_for_ranking_sync(
    session: Session,
    region_level: str,
    yms: list[str],
) -> list[dict[str, Any]]:
    """랭킹 계산에 필요한 월별 집계 데이터를 로드한다."""
    if not yms:
        return []
    if region_level == "gu":
        where_dong = "ms.eupmyeondong IS NULL"
    else:
        where_dong = "ms.eupmyeondong IS NOT NULL"

    ym_placeholders = ", ".join(f"'{ym}'" for ym in yms)
    sql = text(f"""
        SELECT
            ms.sigungu_code,
            ms.eupmyeondong,
            ms.deal_ym,
            ms.median_price_per_sqm,
            ms.transaction_count
        FROM re_monthly_stat ms
        WHERE {where_dong}
          AND ms.deal_ym IN ({ym_placeholders})
        ORDER BY ms.sigungu_code, ms.eupmyeondong, ms.deal_ym
    """)
    result = session.execute(sql)
    return [dict(row._mapping) for row in result]


def get_sigungu_names_sync(session: Session) -> dict[str, str]:
    """sigungu_code → sigungu_name 맵을 반환한다 (re_transaction에서)."""
    result = session.execute(
        text("SELECT DISTINCT sigungu_code, sigungu_name FROM re_transaction")
    )
    return {row.sigungu_code: row.sigungu_name for row in result}
