from typing import Any, Sequence

from sqlalchemy import Row, func, or_, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from realestate.db.models import (
    ReCollectionLog,
    ReComplexNews,
    ReComplexRankingSnapshot,
    ReComplexStat,
    ReTransaction,
)


# ── 비동기 (API용) ─────────────────────────────────────────────────────

async def get_region_monthly_stats_async(
    session: AsyncSession,
    sigungu_code: str,
    eupmyeondong: str | None,
    start_ym: str,
    end_ym: str,
):
    filters = [
        ReTransaction.sigungu_code == sigungu_code,
        ReTransaction.deal_ym >= start_ym,
        ReTransaction.deal_ym <= end_ym,
        ReTransaction.price_per_sqm.isnot(None),
    ]
    if eupmyeondong:
        filters.append(ReTransaction.eupmyeondong == eupmyeondong)

    q = (
        select(
            ReTransaction.deal_ym,
            func.percentile_cont(0.5)
            .within_group(ReTransaction.price_per_sqm.asc())
            .label("median_price_per_sqm"),
            func.count().label("transaction_count"),
        )
        .where(*filters)
        .group_by(ReTransaction.deal_ym)
        .order_by(ReTransaction.deal_ym.asc())
    )
    result = await session.execute(q)
    return result.all()


async def get_latest_snapshot_ym(
    session: AsyncSession,
    _region_level: str,
    period: str,
) -> str | None:
    """헬스체크용. region_level은 무시하고 complex 스냅샷 기준으로 최신 ym 반환."""
    return await get_latest_complex_snapshot_ym(session, period)


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
    seg: list[tuple[str, str]] | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    order: str = "desc",
) -> list[ReComplexRankingSnapshot]:
    """
    단지 랭킹 조회.

    seg(세그먼트)가 지정되면 sido/gu/dong은 무시하고 seg 내 법정동 집합만 적용.
    seg 미지정 시 필터 우선순위: gu > sido > 수도권 전체, dong은 독립 추가 필터.
    seg는 [(sigungu_code, eupmyeondong), ...] 튜플 목록.

    min_price/max_price: 억 단위. 종료 시점 84㎡ 환산 금액(end_price * 84 만원) 기준
    이상(≥)/이하(≤) 필터. 각각 독립 선택적. 지정 시 end_price가 NULL인 단지 제외.
    """
    rank_sort = (
        ReComplexRankingSnapshot.change_pct.asc().nulls_last()
        if order == "asc"
        else ReComplexRankingSnapshot.rank.asc().nulls_last()
    )
    q = (
        select(ReComplexRankingSnapshot)
        .where(
            ReComplexRankingSnapshot.period == period,
            ReComplexRankingSnapshot.snapshot_ym == snapshot_ym,
        )
        .order_by(
            # ok를 앞에, 나머지(insufficient/no_end/no_start)를 뒤에
            # 'ok' > 'i'/'n' 이므로 desc()를 써야 ok가 먼저 온다
            ReComplexRankingSnapshot.data_status.desc(),
            rank_sort,
        )
    )
    if seg:
        q = q.where(
            tuple_(
                ReComplexRankingSnapshot.sigungu_code,
                ReComplexRankingSnapshot.eupmyeondong,
            ).in_(seg)
        )
    else:
        if gu:
            q = q.where(ReComplexRankingSnapshot.sigungu_code == gu)
        elif sido:
            q = q.where(ReComplexRankingSnapshot.sigungu_code.like(f"{sido[:2]}%"))
        if dong:
            q = q.where(ReComplexRankingSnapshot.eupmyeondong == dong)
    if min_price is not None:
        # 억 → 만원: × 10000. end_price(만원/㎡) × 84 ≥ min_price × 10000
        min_man = min_price * 10000
        q = q.where(
            ReComplexRankingSnapshot.end_price.isnot(None),
            ReComplexRankingSnapshot.end_price * 84 >= min_man,
        )
    if max_price is not None:
        max_man = max_price * 10000
        q = q.where(
            ReComplexRankingSnapshot.end_price.isnot(None),
            ReComplexRankingSnapshot.end_price * 84 <= max_man,
        )
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
                "start_deal_amount": text("excluded.start_deal_amount"),
                "end_deal_amount": text("excluded.end_deal_amount"),
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


# ── 검색 (비동기) ───────────────────────────────────────────────────────

async def get_latest_any_snapshot_ym(session: AsyncSession) -> str | None:
    """모든 period를 통틀어 가장 최신 snapshot_ym을 반환한다."""
    result = await session.execute(
        select(func.max(ReComplexRankingSnapshot.snapshot_ym))
    )
    return result.scalar_one_or_none()


async def search_regions_async(
    session: AsyncSession,
    q: str,
    limit: int = 50,
) -> list[Row]:
    """
    시군구명 또는 법정동명 부분일치 검색.
    최신 스냅샷 기준 DISTINCT (sigungu_code, sigungu_name, eupmyeondong) 반환.
    """
    latest_ym = await get_latest_any_snapshot_ym(session)
    if latest_ym is None:
        return []
    q_pct = f"%{q}%"
    stmt = (
        select(
            ReComplexRankingSnapshot.sigungu_code,
            ReComplexRankingSnapshot.sigungu_name,
            ReComplexRankingSnapshot.eupmyeondong,
        )
        .where(
            ReComplexRankingSnapshot.snapshot_ym == latest_ym,
            or_(
                ReComplexRankingSnapshot.sigungu_name.ilike(q_pct),
                ReComplexRankingSnapshot.eupmyeondong.ilike(q_pct),
            ),
        )
        .distinct()
        .order_by(
            ReComplexRankingSnapshot.sigungu_code,
            ReComplexRankingSnapshot.eupmyeondong,
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.all()


async def search_complexes_async(
    session: AsyncSession,
    q_norm: str,
    period: str,
    snapshot_ym: str,
    sido: str | None = None,
    gu: str | None = None,
    dong: str | None = None,
    limit: int = 50,
) -> tuple[list[Row], list[ReComplexRankingSnapshot]]:
    """
    apt_name_norm 부분일치로 단지를 검색하고, 해당 period 스냅샷을 함께 반환한다.

    Returns
    -------
    stat_rows : complex_key별 최신 apt_name을 가진 ReComplexStat 행 (중복 제거)
    snap_rows : stat_rows의 complex_key에 매칭된 ReComplexRankingSnapshot 행
               스냅샷이 없는 단지는 여기에 포함되지 않음 → 호출자가 "no_snapshot" 처리
    """
    stat_filters = [ReComplexStat.apt_name_norm.ilike(f"%{q_norm}%")]
    if gu:
        stat_filters.append(ReComplexStat.sigungu_code == gu)
    elif sido:
        stat_filters.append(ReComplexStat.sigungu_code.like(f"{sido[:2]}%"))
    if dong:
        stat_filters.append(ReComplexStat.eupmyeondong.ilike(f"%{dong}%"))

    # complex_key별 최신 apt_name 취득 — ORDER BY deal_ym DESC, Python에서 첫 번째만 유지
    stat_stmt = (
        select(
            ReComplexStat.complex_key,
            ReComplexStat.sigungu_code,
            ReComplexStat.eupmyeondong,
            ReComplexStat.apt_name,
        )
        .where(*stat_filters)
        .order_by(ReComplexStat.complex_key, ReComplexStat.deal_ym.desc())
    )
    raw = await session.execute(stat_stmt)
    seen: set[str] = set()
    stat_rows: list[Row] = []
    for row in raw.all():
        if row.complex_key not in seen:
            seen.add(row.complex_key)
            stat_rows.append(row)
            if len(stat_rows) >= limit:
                break

    if not stat_rows:
        return [], []

    complex_keys = [r.complex_key for r in stat_rows]
    snap_result = await session.execute(
        select(ReComplexRankingSnapshot).where(
            ReComplexRankingSnapshot.complex_key.in_(complex_keys),
            ReComplexRankingSnapshot.period == period,
            ReComplexRankingSnapshot.snapshot_ym == snapshot_ym,
        )
    )
    snap_rows = list(snap_result.scalars().all())

    return stat_rows, snap_rows


async def get_sigungu_name_map_async(
    session: AsyncSession,
    sigungu_codes: list[str],
) -> dict[str, str]:
    """sigungu_code → sigungu_name 맵 (ReComplexRankingSnapshot 기준)."""
    if not sigungu_codes:
        return {}
    result = await session.execute(
        select(
            ReComplexRankingSnapshot.sigungu_code,
            ReComplexRankingSnapshot.sigungu_name,
        )
        .where(ReComplexRankingSnapshot.sigungu_code.in_(sigungu_codes))
        .distinct()
    )
    return {row.sigungu_code: row.sigungu_name for row in result.all()}


async def get_complex_meta_async(
    session: AsyncSession,
    complex_key: str,
) -> Row | None:
    """
    단지 헤더 메타 (apt_name, sigungu_code, sigungu_name, eupmyeondong, display_name).
    스냅샷이 있으면 스냅샷 기준, 없으면 ReComplexStat 기준으로 반환한다.
    존재하지 않는 complex_key면 None 반환.
    """
    snap_stmt = (
        select(
            ReComplexRankingSnapshot.apt_name,
            ReComplexRankingSnapshot.sigungu_code,
            ReComplexRankingSnapshot.sigungu_name,
            ReComplexRankingSnapshot.eupmyeondong,
            ReComplexRankingSnapshot.display_name,
        )
        .where(ReComplexRankingSnapshot.complex_key == complex_key)
        .order_by(ReComplexRankingSnapshot.snapshot_ym.desc())
        .limit(1)
    )
    snap_result = await session.execute(snap_stmt)
    row = snap_result.one_or_none()
    if row:
        return row

    stat_stmt = (
        select(
            ReComplexStat.apt_name,
            ReComplexStat.sigungu_code,
            ReComplexStat.eupmyeondong,
        )
        .where(ReComplexStat.complex_key == complex_key)
        .order_by(ReComplexStat.deal_ym.desc())
        .limit(1)
    )
    stat_result = await session.execute(stat_stmt)
    return stat_result.one_or_none()


async def get_complex_monthly_async(
    session: AsyncSession,
    complex_key: str,
    start_ym: str,
    end_ym: str,
) -> list[Row]:
    """단지 월별 중위가·거래건수 시계열 반환."""
    result = await session.execute(
        select(
            ReComplexStat.deal_ym,
            ReComplexStat.median_price_per_sqm,
            ReComplexStat.transaction_count,
        )
        .where(
            ReComplexStat.complex_key == complex_key,
            ReComplexStat.deal_ym >= start_ym,
            ReComplexStat.deal_ym <= end_ym,
        )
        .order_by(ReComplexStat.deal_ym.asc())
    )
    return result.all()


# ── ReComplexNews (뉴스 링크 TTL 캐시) ────────────────────────────────────

def get_latest_complex_snapshot_ym_sync(session: Session, period: str) -> str | None:
    """get_latest_complex_snapshot_ym(async, API용)의 sync 버전 — 배치용.

    MAX(snapshot_ym)이므로 월초 신규 스냅샷 생성 전에 배치가 돌아도
    가장 최근에 실제로 존재하는 스냅샷을 정상적으로 반환한다.
    """
    stmt = (
        select(ReComplexRankingSnapshot.snapshot_ym)
        .where(ReComplexRankingSnapshot.period == period)
        .order_by(ReComplexRankingSnapshot.snapshot_ym.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def get_complex_news_targets_sync(
    session: Session, period: str, snapshot_ym: str, top: int = 20,
) -> list[dict]:
    """
    해당 period+snapshot_ym의 상승 top N(rank<=N) + 하락 top N(change_pct 오름차순)
    단지를 합쳐 complex_key 기준 dedup 후 반환한다.

    반환: [{"complex_key", "apt_name", "sigungu_name", "eupmyeondong"}, ...]
    """
    base_filters = [
        ReComplexRankingSnapshot.period == period,
        ReComplexRankingSnapshot.snapshot_ym == snapshot_ym,
        ReComplexRankingSnapshot.data_status == "ok",
    ]
    cols = (
        ReComplexRankingSnapshot.complex_key,
        ReComplexRankingSnapshot.apt_name,
        ReComplexRankingSnapshot.sigungu_name,
        ReComplexRankingSnapshot.eupmyeondong,
    )
    gainers = session.execute(
        select(*cols)
        .where(*base_filters, ReComplexRankingSnapshot.rank <= top)
        .order_by(ReComplexRankingSnapshot.rank.asc())
    ).all()
    losers = session.execute(
        select(*cols)
        .where(*base_filters)
        .order_by(ReComplexRankingSnapshot.change_pct.asc().nulls_last())
        .limit(top)
    ).all()

    dedup: dict[str, dict] = {}
    for row in [*gainers, *losers]:
        dedup.setdefault(row.complex_key, {
            "complex_key": row.complex_key,
            "apt_name": row.apt_name,
            "sigungu_name": row.sigungu_name,
            "eupmyeondong": row.eupmyeondong,
        })
    return list(dedup.values())


def replace_complex_news_sync(session: Session, complex_key: str, articles: list[dict]) -> None:
    """해당 단지의 기존 뉴스 캐시를 지우고 새 결과로 교체한다(빈 리스트면 삭제만)."""
    session.execute(
        ReComplexNews.__table__.delete().where(ReComplexNews.complex_key == complex_key)
    )
    if articles:
        session.execute(
            ReComplexNews.__table__.insert(),
            [
                {
                    "complex_key": complex_key,
                    "title": a["title"][:500],
                    "link": a["link"][:1000],
                    "published_at": a["published_at"],
                }
                for a in articles
            ],
        )
    session.commit()


def delete_expired_complex_news_sync(session: Session, ttl_days: int) -> int:
    """TTL 지난 뉴스 캐시를 삭제한다(약관 취지: 무기한 축적 금지)."""
    result = session.execute(
        text("DELETE FROM re_complex_news WHERE collected_at < NOW() - (:ttl_days * INTERVAL '1 day')"),
        {"ttl_days": ttl_days},
    )
    session.commit()
    return result.rowcount


async def get_complex_news_async(
    session: AsyncSession, complex_key: str, ttl_days: int,
) -> Sequence[ReComplexNews]:
    """TTL 이내에 수집된 뉴스만 반환한다(만료분은 정리 배치 전이라도 조회에서 제외)."""
    stmt = (
        select(ReComplexNews)
        .where(
            ReComplexNews.complex_key == complex_key,
            ReComplexNews.collected_at >= text("NOW() - (:ttl_days * INTERVAL '1 day')"),
        )
        .order_by(ReComplexNews.published_at.desc())
        .params(ttl_days=ttl_days)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_has_news_complex_keys_async(
    session: AsyncSession, complex_keys: list[str], ttl_days: int,
) -> set[str]:
    """주어진 단지 중 TTL 이내 유효한 뉴스 캐시가 있는 complex_key 집합을 반환한다."""
    if not complex_keys:
        return set()
    stmt = (
        select(ReComplexNews.complex_key)
        .distinct()
        .where(
            ReComplexNews.complex_key.in_(complex_keys),
            ReComplexNews.collected_at >= text("NOW() - (:ttl_days * INTERVAL '1 day')"),
        )
        .params(ttl_days=ttl_days)
    )
    result = await session.execute(stmt)
    return set(result.scalars().all())
