"""
KOSPI 가격 데이터 수집 배치.

- 데이터 소스: KRX 정보데이터시스템 전종목 시세(MDCSTAT01501)를 거래일마다 1회 호출.
  KRX 로그인 필요(_ensure_krx_auth). 거래일 달력은 KOSPI 지수 일봉(KRX) 날짜.
- 저장값:     시가·고가·저가·종가·거래량·시가총액 모두 KRX 원값. close_adj에는 수집일의
  원 종가를 넣는다 — 최신일은 소급 보정의 기준점이라 원값 = 수정값이다.
- 소급 보정:  거래일마다 kospi_price_adjust가 KRX 기준가(종가 − 전일대비)로 분할·병합·
  감자·증자 권리락을 찾아 그 이전 이력을 조정한다. 같은 날 저장과 한 트랜잭션.
- 재수집 없음: 과거 날짜에 KRX 원값을 다시 쓰면 그사이 적용된 보정이 원값으로 덮인다.
  그래서 DB 최신일 이후 거래일만, 날짜 오름차순으로 하루씩 "수집 → 보정"한다.
- 스케줄:     매일 18:00 KST (장 마감 15:30 + 여유 2.5h)
- 재시도:     tenacity exponential backoff (max 3회)

2026-10 이전에는 pykrx get_market_ohlcv_by_date(adjusted=True)로 받았는데, 이 함수는
내부에서 네이버 fchart를 쓴다. 네이버 일봉 종가가 2026-09-14부터 KRX 공식 종가와
달라져(NXT 통합 시세로 추정) 교체했다. 초기 적재용 run_kospi_full_history와
_fetch_ohlcv/_fetch_market_cap(scripts/init_history.py, restore_history.py가 사용)은
아직 이전 방식이다 — 빈 DB를 처음 채울 때만 쓸 것.
"""

import logging
import time
from datetime import date

import pandas as pd
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from fomobot.db.crud import (
    get_close_on_date_sync,
    get_last_trading_day_sync,
    upsert_price_daily_sync,
    upsert_index_daily_sync,
    upsert_securities_master_sync,
)
from fomobot.db.session import SyncSessionLocal

logger = logging.getLogger(__name__)

MARKET = "kospi"
INDEX_CODE = "KOSPI"
# KOSPI 지수 티커 (pykrx)
KOSPI_INDEX_TICKER = "1001"

# KRX 로그인이 이 프로세스에서 한 번이라도 실패했는지 — _ensure_krx_auth 참고
_krx_login_failed = False


def _ensure_krx_auth() -> None:
    """
    pykrx의 KRX 로그인 성공 여부를 확인하고, 실패면 예외로 배치를 중단한다.

    pykrx는 로그인 실패(비밀번호 만료 CD010, 자격 증명 오류 등)를 print()로만
    알리고 비인증 상태로 계속 진행한다. 이 경우 조회가 빈 결과로 끝나 배치가
    '정상 완료'처럼 보이고 Sentry에도 아무것도 가지 않으므로 여기서 명시적으로 막는다.
    또한 세션이 None이면 pykrx가 매 요청마다 재로그인을 시도하므로, 계정 잠금을
    피하기 위해서도 조기 중단이 필요하다.

    로그인 시도는 실행당 최대 1회여야 한다(2026-10-20 로그인 횟수 초과로 계정이 잠겼다).
    - get_auth_session()은 세션이 없으면 그 자리에서 다시 로그인하므로 쓰지 않고,
      pykrx 내부 변수로 import 시점 로그인 결과만 확인한다.
    - 상주 프로세스(ENABLE_SCHEDULER의 APScheduler)에서는 import가 한 번뿐이라 다음 날엔
      세션이 만료돼 있다. 그때는 여기서 refresh를 1회만 시도한다. 수집은 수 초 안에 끝나므로
      실행 도중 만료(pykrx의 요청별 자동 재로그인)에 걸리지 않는다.
    - 한 번이라도 실패하면 _krx_login_failed를 세워, 같은 프로세스에서는 프로세스가 다시
      뜰 때까지 로그인을 더 시도하지 않는다. Railway cron은 실행마다 새 프로세스라 영향 없음.
    """
    global _krx_login_failed
    if _krx_login_failed:
        raise RuntimeError("KRX 로그인이 이 프로세스에서 이미 실패함 — 재시도하지 않음(계정 잠금 방지)")

    import os

    import pykrx.website.comm.auth as krx_auth
    from pykrx import stock  # noqa: F401 — 첫 import 시점에 pykrx가 로그인을 1회 수행

    session = krx_auth._auth_session
    ok = session is not None
    if ok and not session.is_valid():
        ok = session.refresh(os.getenv("KRX_ID", ""), os.getenv("KRX_PW", ""))
    if not ok:
        _krx_login_failed = True
        raise RuntimeError(
            "KRX 로그인 실패 — KRX_ID/KRX_PW 확인 또는 krx.co.kr 비밀번호 변경 필요 "
            "(상세 원인은 직전 pykrx stdout 로그 참고). 재시도하지 않음(계정 잠금 방지)"
        )


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_ohlcv(start: str, end: str, ticker: str, adjusted: bool = True) -> pd.DataFrame:
    from pykrx import stock
    return stock.get_market_ohlcv_by_date(start, end, ticker, adjusted=adjusted)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_market_cap(start: str, end: str, ticker: str) -> pd.DataFrame:
    from pykrx import stock
    return stock.get_market_cap_by_date(start, end, ticker)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_ticker_list(date: str = "") -> list[str]:
    from pykrx import stock
    return stock.get_market_ticker_list(date, market="KOSPI")


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_ticker_name(ticker: str) -> str:
    from pykrx import stock
    return stock.get_market_ticker_name(ticker)


def _fetch_ticker_name_safe(ticker: str) -> str | None:
    """재시도 없이 종목명 1회 조회. 실패 시 None 반환."""
    try:
        from pykrx import stock
        return stock.get_market_ticker_name(ticker)
    except Exception:
        return None


def _fetch_kospi_index(start: str, end: str) -> pd.DataFrame:
    """KOSPI 지수 일봉 조회(KRX). 날짜 인덱스가 KOSPI 거래일 달력 역할도 한다."""
    from pykrx import stock
    df = stock.get_index_ohlcv_by_date(start, end, KOSPI_INDEX_TICKER)
    return df


def _to_number(value) -> float:
    """KRX 응답 문자열("1,234", "-5", "-", "")을 숫자로. 값 없음("-", "")은 0."""
    s = str(value).replace(",", "").strip()
    if s in ("", "-"):
        return 0.0
    return float(s)


def parse_day_snapshot(raw: pd.DataFrame) -> pd.DataFrame:
    """
    KRX 전종목시세(MDCSTAT01501) 원 응답 → 티커 인덱스 DataFrame.

    columns: name, open, high, low, close, volume, cmpprevdd, market_cap, list_shrs
    - cmpprevdd(전일대비)는 부호 포함. 기준가 = close − cmpprevdd.
    - 시가·고가·저가가 0이면(거래정지 등 체결 없음) None.
    - 종가가 0 이하인 행은 버린다.
    """
    if raw.empty:
        return pd.DataFrame(
            columns=["name", "open", "high", "low", "close", "volume", "cmpprevdd", "market_cap", "list_shrs"]
        )
    df = pd.DataFrame({
        "name": raw["ISU_ABBRV"].astype(str).str.strip(),
        "open": raw["TDD_OPNPRC"].map(_to_number),
        "high": raw["TDD_HGPRC"].map(_to_number),
        "low": raw["TDD_LWPRC"].map(_to_number),
        "close": raw["TDD_CLSPRC"].map(_to_number),
        "volume": raw["ACC_TRDVOL"].map(_to_number).astype("int64"),
        "cmpprevdd": raw["CMPPREVDD_PRC"].map(_to_number),
        "market_cap": raw["MKTCAP"].map(_to_number).astype("int64"),
        "list_shrs": raw["LIST_SHRS"].map(_to_number).astype("int64"),
    })
    df.index = raw["ISU_SRT_CD"].astype(str).str.strip()
    df.index.name = "ticker"
    for col in ("open", "high", "low"):
        # float 열에 None을 넣으면 NaN이 되므로 object로 바꿔 None을 유지한다(DB엔 NULL).
        df[col] = df[col].astype(object).where(df[col] > 0, None)
    return df[df["close"] > 0]


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _fetch_day_snapshot(d: date) -> pd.DataFrame:
    """
    KRX 전종목시세 하루치(KOSPI). pykrx 공개 래퍼(get_market_ohlcv_by_ticker)는
    CMPPREVDD_PRC·LIST_SHRS를 버리므로 내부 클래스를 직접 호출한다.
    """
    from pykrx.website.krx.market.core import 전종목시세
    raw = 전종목시세().fetch(d.strftime("%Y%m%d"), "STK")
    return parse_day_snapshot(raw)


def missing_trading_days(calendar: list[date], db_last: date) -> list[date]:
    """DB 최신일 이후의 거래일만 오름차순으로. 그 이전 날짜는 다시 쓰지 않는다."""
    return sorted(d for d in set(calendar) if d > db_last)


def _store_day(d: date, d_prev: date, snapshot: pd.DataFrame, prev_shares: dict[str, int]) -> list:
    """
    D일 하나를 "보정 → 저장" 한 트랜잭션으로 처리한다.

    1. DB의 D-1 거래일 close_adj와 KRX D일 기준가를 비교해 기준 변동을 찾는다.
    2. 자동 분류된 이벤트는 D 이전 이력을 소급 조정한다(kospi_price_adjust).
    3. D일 KRX 원값을 저장한다 — D 행은 조정 대상이 아니므로 순서와 무관.
    커밋 후 이벤트를 Sentry로 보고하고, 이벤트 목록을 반환한다.
    """
    from fomobot.batch.kospi_price_adjust import (
        apply_price_basis_events,
        detect_price_basis_events,
        report_price_basis_events,
    )

    snap_rows = snapshot[["close", "cmpprevdd", "list_shrs"]].to_dict("index")
    records = [
        {
            "ticker": ticker,
            "market": MARKET,
            "date": d,
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close_adj": float(row["close"]),
            "volume": int(row["volume"]),
            "market_cap": int(row["market_cap"]) or None,
        }
        for ticker, row in snapshot.iterrows()
    ]

    with SyncSessionLocal() as session:
        prev_close = get_close_on_date_sync(session, MARKET, d_prev)
        events = detect_price_basis_events(d, snap_rows, prev_close, prev_shares)
        apply_price_basis_events(session, MARKET, d, events)
        upsert_price_daily_sync(session, records, commit=False)
        session.commit()

    report_price_basis_events(MARKET, events)
    logger.info(
        "KOSPI %s 저장 %d종목, 기준 변동 %d건(자동 %d / 보류 %d)",
        d, len(records), len(events),
        sum(1 for e in events if e.is_auto), sum(1 for e in events if not e.is_auto),
    )
    return events


def run_kospi_collection(target_date: date | None = None) -> list[date]:
    """
    DB 최신일 이후 target_date까지의 KOSPI 거래일을 하루씩 "수집 → 보정"한다.

    여러 날이 비어 있으면(수집 장애 등) 반드시 날짜 오름차순으로 처리한다. D일 보정은
    DB의 D-1 종가를 기준으로 하므로, D-1이 먼저 저장·보정돼 있어야 한다. DB 최신일
    이전의 빈 날짜는 메우지 않는다 — 그 사이 적용된 소급 보정 위에 KRX 원값을 쓰면
    기준이 다시 어긋난다(별도 재적재 스크립트로 처리).

    Returns: 이번 실행에서 저장한 거래일 목록
    """
    today = target_date or date.today()
    _ensure_krx_auth()

    with SyncSessionLocal() as session:
        db_last = get_last_trading_day_sync(session, MARKET, as_of=today)
    if db_last is None:
        raise RuntimeError("price_daily에 KOSPI 데이터가 없음 — 초기 적재(scripts/init_history.py)를 먼저 실행")

    # 지수 일봉 = 거래일 달력. 달력 없이는 휴장일과 장애를 구분할 수 없으므로 실패하면 중단한다.
    idx_df = _fetch_kospi_index(db_last.strftime("%Y%m%d"), today.strftime("%Y%m%d"))
    if idx_df.empty:
        raise RuntimeError(f"KOSPI 지수 조회 결과 없음({db_last}~{today}) — 거래일 판정 불가")
    close_col = "종가" if "종가" in idx_df.columns else idx_df.columns[3]
    index_records = [
        {"index_code": INDEX_CODE, "date": ts.date(), "close_adj": float(v)}
        for ts, v in idx_df[close_col].items()
    ]
    with SyncSessionLocal() as session:
        upsert_index_daily_sync(session, index_records)

    calendar = [r["date"] for r in index_records]
    days = missing_trading_days(calendar, db_last)
    if not days:
        logger.info("KOSPI 수집할 거래일 없음 (DB 최신일 %s, 기준일 %s)", db_last, today)
        return []
    logger.info("KOSPI 수집 대상 거래일 %d개: %s", len(days), [d.isoformat() for d in days])

    # D-1 상장주식수는 KRX에서 받는다 — DB에는 주식 수 컬럼이 없다.
    prev_snapshot = _fetch_day_snapshot(db_last)
    prev_shares = prev_snapshot["list_shrs"].to_dict()

    d_prev = db_last
    last_snapshot = prev_snapshot
    for d in days:
        snapshot = _fetch_day_snapshot(d)
        if snapshot.empty:
            raise RuntimeError(f"KOSPI {d} 전종목 시세가 비어 있음(지수 달력상 거래일) — 수집 중단")
        _store_day(d, d_prev, snapshot, prev_shares)
        prev_shares = snapshot["list_shrs"].to_dict()
        d_prev = d
        last_snapshot = snapshot

    master_records = [
        {"ticker": t, "market": MARKET, "name": name or None, "is_active": True}
        for t, name in last_snapshot["name"].items()
    ]
    with SyncSessionLocal() as session:
        upsert_securities_master_sync(session, master_records)

    logger.info("KOSPI 수집 완료: %s", [d.isoformat() for d in days])
    return days


def _get_covered_tickers(market: str, start_date: date, end_date: date, min_rows: int = 100) -> set[str]:
    """DB에 min_rows 이상의 데이터가 있는 티커를 반환한다."""
    from sqlalchemy import text
    with SyncSessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT ticker FROM price_daily "
                "WHERE market = :market AND date BETWEEN :start AND :end "
                "GROUP BY ticker HAVING COUNT(*) >= :min_rows"
            ),
            {"market": market, "start": start_date, "end": end_date, "min_rows": min_rows},
        ).fetchall()
    return {r[0] for r in rows}


def run_kospi_full_history(start_date: date, end_date: date) -> None:
    """
    초기 풀 히스토리 수집 (CLI로 1회 실행). 이미 데이터가 있는 티커는 스킵.

    ⚠️ 아직 이전 방식(네이버 수정주가, _fetch_ohlcv)이다. 일일 수집(run_kospi_collection)은
    KRX 원 종가 + 자체 소급 보정이므로, 운영 중인 DB에 이 함수로 행을 추가하면 두 방식이
    섞인다. 빈 DB 초기 적재 전용.
    """
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    logger.info("KOSPI 풀 히스토리 수집: %s ~ %s", start_str, end_str)

    _ensure_krx_auth()

    try:
        all_tickers = _fetch_ticker_list(end_str)
    except Exception:
        logger.exception("KOSPI 티커 목록 조회 실패")
        return

    covered = _get_covered_tickers(MARKET, start_date, end_date)
    tickers = [t for t in all_tickers if t not in covered]
    logger.info(
        "KOSPI: 전체 %d개 중 %d개 스킵(기존 데이터), %d개 수집 예정",
        len(all_tickers), len(covered), len(tickers),
    )

    if not tickers:
        logger.info("모든 KOSPI 티커의 데이터가 이미 존재합니다.")
        return

    price_records: list[dict] = []
    master_records: list[dict] = []
    index_records: list[dict] = []

    for i, ticker in enumerate(tickers):
        try:
            ohlcv = _fetch_ohlcv(start_str, end_str, ticker, adjusted=True)
            cap_df = _fetch_market_cap(start_str, end_str, ticker)

            if ohlcv.empty:
                continue

            master_records.append({
                "ticker": ticker,
                "market": MARKET,
                "name": _fetch_ticker_name_safe(ticker),
                "is_active": True,
            })

            close_col = "종가" if "종가" in ohlcv.columns else ohlcv.columns[3]
            open_col = "시가" if "시가" in ohlcv.columns else ohlcv.columns[0]
            high_col = "고가" if "고가" in ohlcv.columns else ohlcv.columns[1]
            low_col = "저가" if "저가" in ohlcv.columns else ohlcv.columns[2]
            vol_col = "거래량" if "거래량" in ohlcv.columns else ohlcv.columns[4]

            close_idx = ohlcv.columns.get_loc(close_col) + 1
            open_idx = ohlcv.columns.get_loc(open_col) + 1
            high_idx = ohlcv.columns.get_loc(high_col) + 1
            low_idx = ohlcv.columns.get_loc(low_col) + 1
            vol_idx = ohlcv.columns.get_loc(vol_col) + 1
            cap_col = "시가총액" if "시가총액" in cap_df.columns else (cap_df.columns[0] if not cap_df.empty else None)

            for row in ohlcv.itertuples(index=True, name=None):
                idx_date = row[0]
                cap_val = None
                if cap_col and not cap_df.empty and idx_date in cap_df.index:
                    cap_val = int(cap_df.loc[idx_date, cap_col])

                price_records.append({
                    "ticker": ticker,
                    "market": MARKET,
                    "date": idx_date.date(),
                    "open": float(row[open_idx]) if pd.notna(row[open_idx]) else None,
                    "high": float(row[high_idx]) if pd.notna(row[high_idx]) else None,
                    "low": float(row[low_idx]) if pd.notna(row[low_idx]) else None,
                    "close_adj": float(row[close_idx]),
                    "volume": int(row[vol_idx]) if pd.notna(row[vol_idx]) else None,
                    "market_cap": cap_val,
                })

            if (i + 1) % 50 == 0:
                time.sleep(1.0)
                logger.info("KOSPI 풀 수집 %d/%d...", i + 1, len(tickers))

            # 배치 단위로 DB 저장 (메모리 절약)
            if len(price_records) >= 10_000:
                with SyncSessionLocal() as session:
                    upsert_price_daily_sync(session, price_records)
                logger.info("중간 저장: %d건", len(price_records))
                price_records.clear()

        except Exception:
            logger.warning("종목 %s 수집 실패, 스킵", ticker)
            continue

    # 지수
    try:
        idx_df = _fetch_kospi_index(start_str, end_str)
        close_col = "종가" if "종가" in idx_df.columns else idx_df.columns[3]
        close_idx = idx_df.columns.get_loc(close_col) + 1
        for row in idx_df.itertuples(index=True, name=None):
            idx_date = row[0]
            index_records.append({
                "index_code": INDEX_CODE,
                "date": idx_date.date(),
                "close_adj": float(row[close_idx]),
            })
    except Exception:
        logger.warning("KOSPI 지수 풀 수집 실패")

    with SyncSessionLocal() as session:
        if price_records:
            upsert_price_daily_sync(session, price_records)
        if index_records:
            upsert_index_daily_sync(session, index_records)
        if master_records:
            upsert_securities_master_sync(session, master_records)
            logger.info("KOSPI securities_master %d건 저장 완료", len(master_records))

    logger.info("KOSPI 풀 히스토리 수집 완료")
