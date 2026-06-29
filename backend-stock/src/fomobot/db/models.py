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

    __table_args__ = (
        UniqueConstraint(
            "snapshot_date", "market", "period", "rank",
            name="uq_ranking_snapshot",
        ),
        Index("ix_ranking_snapshot_market_period_date", "market", "period", "snapshot_date"),
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
