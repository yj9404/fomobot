from sqlalchemy import (
    BigInteger, Column, Index, Integer, Numeric, SmallInteger,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ReTransaction(Base):
    """
    국토교통부 실거래가 API 원천 데이터.
    '해제여부' O인 취소 거래는 수집 단계에서 제외한다.
    면적 0, 금액 0 레코드도 수집 시 drop.
    """
    __tablename__ = "re_transaction"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sigungu_code = Column(String(5), nullable=False)       # 시군구 코드 (5자리)
    sigungu_name = Column(String(50), nullable=False)
    eupmyeondong = Column(String(50), nullable=False)      # 법정동
    apt_name = Column(String(100), nullable=False)
    deal_ym = Column(String(6), nullable=False)            # YYYYMM (계약 기준)
    deal_day = Column(SmallInteger, nullable=False)
    exclusive_area = Column(Numeric(8, 2), nullable=False) # 전용면적 ㎡
    floor = Column(SmallInteger)
    deal_amount = Column(BigInteger, nullable=False)       # 만원
    price_per_sqm = Column(Numeric(12, 2))                 # 만원/㎡ (수집 시 계산)
    build_year = Column(SmallInteger)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "sigungu_code", "eupmyeondong", "apt_name",
            "deal_ym", "deal_day", "exclusive_area", "floor", "deal_amount",
            name="uq_re_transaction",
        ),
        Index("ix_re_transaction_sigungu_ym", "sigungu_code", "deal_ym"),
        Index("ix_re_transaction_dong_ym", "sigungu_code", "eupmyeondong", "deal_ym"),
    )


class ReMonthlystat(Base):
    """
    월별 지역 집계 (배치가 re_transaction에서 계산해 저장).
    eupmyeondong=NULL이면 구(시군구) 전체 집계.
    거래 건수가 0인 월은 median_price_per_sqm=NULL, transaction_count=0으로 저장
    (거래 없음은 에러가 아닌 정상 상태).
    API는 이 테이블과 re_ranking_snapshot만 읽는다.
    """
    __tablename__ = "re_monthly_stat"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sigungu_code = Column(String(5), nullable=False)
    eupmyeondong = Column(String(50))                      # NULL = 구 단위
    deal_ym = Column(String(6), nullable=False)
    median_price_per_sqm = Column(Numeric(12, 2))          # NULL = 해당 월 거래 없음
    transaction_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "sigungu_code", "eupmyeondong", "deal_ym",
            name="uq_re_monthly_stat",
        ),
        Index("ix_re_monthly_stat_gu_ym", "sigungu_code", "deal_ym"),
        Index("ix_re_monthly_stat_dong_ym", "sigungu_code", "eupmyeondong", "deal_ym"),
    )


class ReRankingSnapshot(Base):
    """
    배치가 계산한 랭킹 결과 스냅샷.
    data_status = 'ok'인 항목만 rank 값을 가진다.
    API는 이 테이블을 직접 읽어 응답을 구성한다 (실시간 계산 금지).
    """
    __tablename__ = "re_ranking_snapshot"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_ym = Column(String(6), nullable=False)        # 기준 완성월 YYYYMM
    region_level = Column(String(4), nullable=False)       # 'gu' | 'dong'
    period = Column(String(3), nullable=False)             # '3m'|'6m'|'1y'|'3y'|'5y'|'10y'|'20y'
    rank = Column(Integer)                                 # NULL = 데이터 부족
    sigungu_code = Column(String(5), nullable=False)
    sigungu_name = Column(String(50), nullable=False)
    eupmyeondong = Column(String(50))                      # NULL = 구 단위
    display_name = Column(String(100), nullable=False)
    start_ym = Column(String(6), nullable=False)
    end_ym = Column(String(6), nullable=False)
    start_price = Column(Numeric(12, 2))                   # 만원/㎡ (NULL = 데이터 없음)
    end_price = Column(Numeric(12, 2))
    change_pct = Column(Numeric(8, 2))                     # 상승률 % (NULL = 계산 불가)
    start_tx_count = Column(Integer)
    end_tx_count = Column(Integer)
    # 'ok' | 'insufficient' | 'no_start' | 'no_end'
    data_status = Column(String(20), nullable=False)
    insufficient_reason = Column(String(200))
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "snapshot_ym", "region_level", "period", "sigungu_code", "eupmyeondong",
            name="uq_re_ranking_snapshot",
        ),
        Index("ix_re_ranking_snapshot_query", "region_level", "period", "snapshot_ym"),
        Index("ix_re_ranking_snapshot_rank", "region_level", "period", "snapshot_ym", "rank"),
    )


class ReCollectionLog(Base):
    """
    시군구×년월 수집 이력.
    백필 스크립트가 이 테이블을 보고 already-done 항목을 skip한다.
    status: 'success' | 'empty' (거래 0건) | 'error'
    """
    __tablename__ = "re_collection_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    sigungu_code = Column(String(5), nullable=False)
    deal_ym = Column(String(6), nullable=False)
    status = Column(String(10), nullable=False)
    transaction_count = Column(Integer, default=0)
    error_message = Column(Text)
    collected_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("sigungu_code", "deal_ym", name="uq_re_collection_log"),
        Index("ix_re_collection_log_status", "sigungu_code", "status"),
    )
