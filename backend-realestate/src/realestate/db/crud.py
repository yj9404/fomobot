from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from realestate.db.models import (
    ReCollectionLog,
    ReComplexRankingSnapshot,
    ReComplexStat,
    ReTransaction,
)


# ── 비동기 (API용) ─────────────────────────────────────────────────────

async def get_latest_complex_snapshot_ym(
    session: AsyncSession,
    period: str,
) -> str | None:
    result = await session.execute(
        select(ReComplexRankingSnapshot.snapshot_ym)
        .where(ReComplexRankingSnapshot.period == period)
        .order_by(ReComplexRankingSnapshot.snapshot_ym.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_complex_rankings_async(
    session: AsyncSession,
    period: str,
    snapshot_ym: str,
    top: int,
    sido: str | None = None,
    gu: str | None = None,
    dong: str | None = None,
) -> list[ReComplexRankingSnapshot]:
    """
    단지 랭킹 조회.

    필터 우선순위: gu > sido > 수도권 전체.
    dong은 독립적으로 추가 필터링.
    """
    q = (
        select(ReComplexRankingSnapshot)
        .where(
            ReComplexRankingSnapshot.period == period,
            ReComplexRankingSnapshot.snapshot_ym == snapshot_ym,
        )
        .order_by(
            ReComplexRankingSnapshot.data_status,   # 'ok' < others (알파벳순)
            ReComplexRankingSnapshot.rank.asc().nulls_last(),
        )
    )
    if gu:
        q = q.where(ReComplexRankingSnapshot.sigungu_code == gu)
    elif sido:
        q = q.where(ReComplexRankingSnapshot.sigungu_code.like(f"{sido[:2]}%"))
    if dong:
        q = q.where(ReComplexRankingSnapshot.eupmyeondong == dong)
    if top > 0:
        # ok top N + excluded 모두 반환 (excluded는 최대 5000개로 제한)
        q = q.limit(top + 5000)
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


def upsert_complex_stats_sync(session: Session, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    stmt = (
        insert(ReComplexStat)
        .values(records)
        .on_conflict_do_update(
            constraint="uq_re_complex_stat",
            set_={
                "apt_name": text("excluded.apt_name"),
                "apt_name_norm": text("excluded.apt_name_norm"),
                "median_price_per_sqm": text("excluded.median_price_per_sqm"),
                "transaction_count": text("excluded.transaction_count"),
                "updated_at": text("now()"),
            },
        )
    )
    session.execute(stmt)
    session.commit()


def upsert_complex_ranking_snapshots_sync(
    session: Session, records: list[dict[str, Any]]
) -> None:
    if not records:
        return
    stmt = (
        insert(ReComplexRankingSnapshot)
        .values(records)
        .on_conflict_do_update(
            constraint="uq_re_complex_ranking_snapshot",
            set_={
                "rank": text("excluded.rank"),
                "sigungu_name": text("excluded.sigungu_name"),
                "display_name": text("excluded.display_name"),
                "start_price": text("excluded.start_price"),
                "end_price": text("excluded.end_price"),
                "change_pct": text("excluded.change_pct"),
                "start_tx_count": text("excluded.start_tx_count"),
                "end_tx_count": text("excluded.end_tx_count"),
                "data_status": text("excluded.data_status"),
                "insufficient_reason": text("excluded.insufficient_reason"),
                "windows_overlap": text("excluded.windows_overlap"),
                "created_at": text("now()"),
            },
        )
    )
    session.execute(stmt)
    session.commit()


def get_sigungu_names_sync(session: Session) -> dict[str, str]:
    """sigungu_code → sigungu_name 맵을 반환한다 (re_transaction에서)."""
    result = session.execute(
        text("SELECT DISTINCT sigungu_code, sigungu_name FROM re_transaction")
    )
    return {row.sigungu_code: row.sigungu_name for row in result}
