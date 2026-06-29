"""
국토교통부 실거래가 API 수집 배치.

PublicDataReader의 TransactionPrice를 사용해 시군구×년월 단위로 수집한다.
수집 결과는 re_transaction에 UPSERT, 이력은 re_collection_log에 기록한다.

API 컬럼명이 PublicDataReader 버전에 따라 다를 수 있으므로 방어적으로 처리한다.
"""

import logging
import time
from decimal import Decimal, InvalidOperation

import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from realestate.config import settings
from realestate.db.crud import upsert_collection_log_sync, upsert_transactions_sync
from realestate.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)

# PublicDataReader 1.1.0+ 아파트 매매 컬럼명 (현행 우선, 구버전/한글 폴백)
_COL_CANDIDATES = {
    "apt_name": ["aptNm", "아파트", "단지명"],
    "eupmyeondong": ["umdNm", "법정동", "legalDong"],
    "deal_amount_raw": ["dealAmount", "거래금액"],
    "exclusive_area": ["excluUseAr", "전용면적", "exclusiveArea"],
    "deal_year": ["dealYear", "년", "계약년도"],
    "deal_month": ["dealMonth", "월", "계약월"],
    "deal_day": ["dealDay", "일", "계약일"],
    "floor": ["floor", "층"],
    "build_year": ["buildYear", "건축년도"],
    "cancel_type": ["cdealType", "해제여부", "cancelDealType"],
    "cancel_date": ["cdealDay", "해제사유발생일", "cancelDealDay"],
    "sigungu_code_col": ["sggCd", "지역코드", "regionalCD"],
}


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _parse_amount(val) -> int | None:
    """'5,000' → 5000 (만원 단위). 파싱 불가 시 None."""
    if pd.isna(val):
        return None
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_decimal(val) -> Decimal | None:
    if pd.isna(val):
        return None
    try:
        return Decimal(str(val).strip())
    except (InvalidOperation, TypeError):
        return None


def _parse_int(val) -> int | None:
    if pd.isna(val):
        return None
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def _clean_df(raw: pd.DataFrame, sigungu_code: str, sigungu_name: str, deal_ym: str) -> list[dict]:
    """API 응답 DataFrame을 정제해 insert용 dict 목록으로 변환한다."""
    if raw is None or raw.empty:
        return []

    df = raw.copy()

    # 취소 거래 제거 (해제여부='O' 또는 해제사유발생일 존재)
    cancel_type_col = _pick_col(df, _COL_CANDIDATES["cancel_type"])
    cancel_date_col = _pick_col(df, _COL_CANDIDATES["cancel_date"])
    if cancel_type_col:
        df = df[df[cancel_type_col].isna() | (df[cancel_type_col].astype(str).str.strip() == "")]
    if cancel_date_col:
        df = df[df[cancel_date_col].isna() | (df[cancel_date_col].astype(str).str.strip() == "")]

    if df.empty:
        return []

    apt_col = _pick_col(df, _COL_CANDIDATES["apt_name"])
    dong_col = _pick_col(df, _COL_CANDIDATES["eupmyeondong"])
    amount_col = _pick_col(df, _COL_CANDIDATES["deal_amount_raw"])
    area_col = _pick_col(df, _COL_CANDIDATES["exclusive_area"])
    year_col = _pick_col(df, _COL_CANDIDATES["deal_year"])
    month_col = _pick_col(df, _COL_CANDIDATES["deal_month"])
    day_col = _pick_col(df, _COL_CANDIDATES["deal_day"])
    floor_col = _pick_col(df, _COL_CANDIDATES["floor"])
    build_col = _pick_col(df, _COL_CANDIDATES["build_year"])

    required = [apt_col, dong_col, amount_col, area_col, day_col]
    if any(c is None for c in required):
        missing = [k for k, c in zip(["apt", "dong", "amount", "area", "day"], required) if c is None]
        logger.warning("%s %s: 필수 컬럼 없음 %s (보유: %s)", sigungu_code, deal_ym, missing, list(df.columns))
        return []

    col_list = list(df.columns)
    apt_idx = col_list.index(apt_col) if apt_col else None
    dong_idx = col_list.index(dong_col) if dong_col else None
    amount_idx = col_list.index(amount_col)
    area_idx = col_list.index(area_col)
    day_idx = col_list.index(day_col)
    floor_idx = col_list.index(floor_col) if floor_col else None
    build_idx = col_list.index(build_col) if build_col else None

    records = []
    for row in df.itertuples(index=False, name=None):
        apt_name = str(row[apt_idx]).strip()[:100] if apt_col else ""
        eupmyeondong = str(row[dong_idx]).strip()[:50] if dong_col else ""
        deal_amount = _parse_amount(row[amount_idx])
        exclusive_area = _parse_decimal(row[area_idx])
        deal_day = _parse_int(row[day_idx])
        floor = _parse_int(row[floor_idx]) if floor_col else None
        build_year = _parse_int(row[build_idx]) if build_col else None

        # 이상치 필터: 면적·금액이 0 이하면 skip
        if not deal_amount or deal_amount <= 0:
            continue
        if not exclusive_area or exclusive_area <= 0:
            continue
        if not deal_day:
            continue

        try:
            price_per_sqm = Decimal(str(deal_amount)) / exclusive_area
        except (InvalidOperation, ZeroDivisionError):
            continue

        # deal_ym은 파라미터에서 직접 사용 (API 응답의 년/월보다 파라미터가 더 신뢰성 높음)
        records.append({
            "sigungu_code": sigungu_code,
            "sigungu_name": sigungu_name,
            "eupmyeondong": eupmyeondong,
            "apt_name": apt_name,
            "deal_ym": deal_ym,
            "deal_day": deal_day,
            "exclusive_area": exclusive_area,
            "floor": floor,
            "deal_amount": deal_amount,
            "price_per_sqm": round(price_per_sqm, 2),
            "build_year": build_year,
        })

    return records


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _fetch_from_api(api, sigungu_code: str, deal_ym: str) -> pd.DataFrame:
    df = api.get_data(
        property_type="아파트",
        trade_type="매매",
        sigungu_code=sigungu_code,
        year_month=deal_ym,
    )
    return df if df is not None else pd.DataFrame()


def collect_sigungu_month(
    sigungu_code: str,
    sigungu_name: str,
    deal_ym: str,
) -> int:
    """
    특정 시군구×년월의 거래 데이터를 수집해 DB에 저장한다.

    Returns
    -------
    int : 저장된(신규) 거래 건수
    """
    import PublicDataReader as pdr

    if not settings.molit_api_key:
        raise RuntimeError("MOLIT_API_KEY 환경변수가 설정되지 않았습니다.")

    api = pdr.TransactionPrice(service_key=settings.molit_api_key)

    try:
        raw_df = _fetch_from_api(api, sigungu_code, deal_ym)
    except Exception as e:
        logger.error("%s %s 수집 실패: %s", sigungu_code, deal_ym, e)
        with SyncSessionLocal() as session:
            upsert_collection_log_sync(
                session, sigungu_code, deal_ym, "error", error_message=str(e)
            )
        return 0

    records = _clean_df(raw_df, sigungu_code, sigungu_name, deal_ym)

    with SyncSessionLocal() as session:
        if records:
            inserted = upsert_transactions_sync(session, records)
            status = "success"
        else:
            inserted = 0
            status = "empty"

        upsert_collection_log_sync(
            session, sigungu_code, deal_ym, status, transaction_count=len(records)
        )

    logger.info(
        "%s (%s) %s: %d건 수집, %d건 신규 저장",
        sigungu_name, sigungu_code, deal_ym, len(records), inserted,
    )
    return inserted
