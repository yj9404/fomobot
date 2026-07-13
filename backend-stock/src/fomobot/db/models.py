from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Float, Integer, String,
    UniqueConstraint, Index, text,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class PriceDaily(Base):
    """
    일별 수정주가 및 시장 데이터.
    close_adj 는 반드시 수정주가(adjusted close)여야 한다.
    액면분할·배당 미반영 시 장기 수익률 계산 전체가 오염되므로
    수집 시점에 검증 후 저장한다 (test_adjusted_close.py 참조).
    """
    __tablename__ = "price_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    market = Column(String(10), nullable=False)     # "kospi" | "nasdaq"
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close_adj = Column(Float, nullable=False)
    volume = Column(BigInteger)
    market_cap = Column(BigInteger)                 # 원화(KOSPI) 또는 USD(NASDAQ)

    __table_args__ = (
        UniqueConstraint("ticker", "market", "date", name="uq_price_daily"),
        Index("ix_price_daily_market_date", "market", "date"),
        Index("ix_price_daily_ticker_date", "ticker", "date"),
    )


class MarketBreadthDaily(Base):
    """
    시장 breadth(상승/하락/보합 종목 수) 일별 집계.

    배치가 계산 후 upsert하며, API는 이 테이블만 조회한다(실시간 계산 금지).
    excluded: date에는 있으나 전일 종가가 없어 등락 판정에서 제외된 종목 수(신규상장 등).
    halted: 거래량 0 종목 수 — 참고용이며 advancers/decliners/unchanged와 배타적이지 않음.
    total: advancers + decliners + unchanged + excluded (NASDAQ은 SPAC 부속증권류 제외 후 기준).
    """
    __tablename__ = "market_breadth_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    advancers = Column(Integer, nullable=False)
    decliners = Column(Integer, nullable=False)
    unchanged = Column(Integer, nullable=False)
    excluded = Column(Integer, nullable=False)
    halted = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("market", "date", name="uq_market_breadth_daily"),
        Index("ix_market_breadth_daily_market_date", "market", "date"),
    )


class IndexDaily(Base):
    """지수 일별 데이터 (KOSPI지수·QQQ). 초과수익 계산에 사용."""
    __tablename__ = "index_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    index_code = Column(String(20), nullable=False)  # "KOSPI" | "QQQ"
    date = Column(Date, nullable=False)
    close_adj = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("index_code", "date", name="uq_index_daily"),
        Index("ix_index_daily_code_date", "index_code", "date"),
    )


class RankingSnapshot(Base):
    """
    배치가 계산한 랭킹 결과 스냅샷.
    API는 이 테이블만 조회한다 (요청 시 실시간 계산 금지).
    """
    __tablename__ = "ranking_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False)
    market = Column(String(10), nullable=False)
    period = Column(String(10), nullable=False)      # "1d"|"7d"|"30d"|"90d"|"365d"|"1825d"
    rank = Column(Integer, nullable=False)
    ticker = Column(String(20), nullable=False)
    name = Column(String(200))
    return_pct = Column(Float, nullable=False)
    mdd_pct = Column(Float)
    volatility_annualized_pct = Column(Float)
    excess_return_pct = Column(Float)
    # 스냅샷 날짜 기준 수정종가 — 백테스트에서 price_daily 과거분 없이 as_of 주가를 참조하기 위해 저장.
    # backfill 완료 전 또는 수집 실패 종목은 NULL 허용.
    close_price_at_snapshot = Column(Float, nullable=True)
    # 시총(KRW for KOSPI, USD for NASDAQ). cap_tier 필터링에 사용.
    # NASDAQ는 랭킹 계산 후 yfinance에서 별도 조회하므로 NULL 가능.
    market_cap = Column(BigInteger, nullable=True)
    # 정렬 방향: 'desc'=상승률 상위(rank 1=최고 상승), 'asc'=하락률 상위(rank 1=최고 하락).
    # 저장 시 양방향 각각 전체 순위를 부여해 저장하므로 조회 시 필터로만 사용.
    order_dir = Column(String(4), nullable=False, server_default=text("'desc'"))

    __table_args__ = (
        UniqueConstraint(
            "snapshot_date", "market", "period", "order_dir", "rank",
            name="uq_ranking_snapshot",
        ),
        Index("ix_ranking_snapshot_market_period_date", "market", "period", "snapshot_date"),
    )


class StockNews(Base):
    """
    종목별 관련 뉴스 TTL 캐시.

    영구 저장소가 아니다 — 다음 배치 갱신까지만 유효한 표시용 캐시이며,
    만료분은 배치가 DELETE한다(네이버 오픈API 이용약관의 "검색결과를
    별도 DB로 무기한 축적" 금지 취지를 존중하기 위함).
    배치가 종목별로 기존 행을 DELETE 후 새로 INSERT하는 방식으로 갱신한다.
    """
    __tablename__ = "stock_news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    link = Column(String(1000), nullable=False)
    published_at = Column(Date, nullable=False)
    collected_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("ticker", "link", name="uq_stock_news"),
        Index("ix_stock_news_ticker", "ticker"),
    )


class SecuritiesMaster(Base):
    """
    종목 마스터 테이블. 티커↔종목명 매핑 및 상장 여부 관리.
    수집 배치가 upsert, 검색 API가 조회한다.
    """
    __tablename__ = "securities_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    market = Column(String(10), nullable=False)   # "kospi" | "nasdaq"
    name = Column(String(200))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    updated_at = Column(DateTime(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("ticker", "market", name="uq_securities_master"),
        Index("ix_securities_master_market_name", "market", "name"),
    )
