from sqlalchemy import (
    BigInteger, Boolean, Column, Index, Integer, Numeric, SmallInteger,
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


class ReComplexStat(Base):
    """
    단지 월별 집계 (배치가 re_transaction에서 계산해 저장).

    complex_key = SHA1(sigungu_code|eupmyeondong|apt_name_norm)
    랭킹 계산은 re_transaction을 직접 읽으므로 이 테이블은
    단지 메타데이터 캐시 및 향후 단지 상세 API용으로 사용된다.
    """
    __tablename__ = "re_complex_stat"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    complex_key = Column(String(64), nullable=False)       # SHA1 hex (40자)
    sigungu_code = Column(String(5), nullable=False)
    eupmyeondong = Column(String(100), nullable=False)
    apt_name = Column(String(200), nullable=False)         # 표시용 원본명 (최근 표기)
    apt_name_norm = Column(String(200), nullable=False)    # 정규화된 이름
    deal_ym = Column(String(6), nullable=False)            # YYYYMM
    median_price_per_sqm = Column(Numeric(12, 2))          # NULL = 해당 월 거래 없음
    transaction_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("complex_key", "deal_ym", name="uq_re_complex_stat"),
        Index("ix_re_complex_stat_sigungu_ym", "sigungu_code", "deal_ym"),
        Index("ix_re_complex_stat_key_ym", "complex_key", "deal_ym"),
    )


class ReComplexRankingSnapshot(Base):
    """
    배치가 계산한 단지 단위 랭킹 스냅샷.

    data_status = 'ok'인 항목만 rank 값을 가진다.
    API는 이 테이블을 직접 읽어 응답을 구성한다 (실시간 계산 금지).

    3m 구간은 시작 앵커가 과거 방향만([start-N, start])이므로
    종료 앵커([end-N, end])와 1개월 겹칠 수 있다 → windows_overlap=True.
    """
    __tablename__ = "re_complex_ranking_snapshot"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_ym = Column(String(6), nullable=False)        # 기준 완성월 YYYYMM
    period = Column(String(5), nullable=False)             # '3m'|'6m'|'1y'|'3y'|'5y'|'10y'|'20y'
    rank = Column(Integer)                                 # NULL = 데이터 부족
    # 단지 식별
    complex_key = Column(String(64), nullable=False)
    sigungu_code = Column(String(5), nullable=False)
    sigungu_name = Column(String(100), nullable=False)
    eupmyeondong = Column(String(100), nullable=False)
    apt_name = Column(String(200), nullable=False)
    display_name = Column(String(400), nullable=False)     # "서울 강남구 개포동 래미안개포1단지"
    # 가격
    start_ym = Column(String(6), nullable=False)
    end_ym = Column(String(6), nullable=False)
    start_price = Column(Numeric(12, 2))                   # 만원/㎡ (NULL = 데이터 없음)
    end_price = Column(Numeric(12, 2))
    start_deal_amount = Column(BigInteger)                 # 만원, 중위 거래금액 (NULL = 데이터 없음)
    end_deal_amount = Column(BigInteger)
    change_pct = Column(Numeric(8, 2))                     # 상승률 % (NULL = 계산 불가)
    start_tx_count = Column(Integer)
    end_tx_count = Column(Integer)
    # 상태
    data_status = Column(String(20), nullable=False)       # 'ok'|'insufficient'|'no_start'|'no_end'
    insufficient_reason = Column(Text)
    windows_overlap = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "snapshot_ym", "period", "complex_key",
            name="uq_re_complex_ranking_snapshot",
        ),
        Index("ix_re_complex_rank_period_ym_rank", "period", "snapshot_ym", "rank"),
        Index("ix_re_complex_rank_sigungu", "sigungu_code", "period", "snapshot_ym"),
        Index("ix_re_complex_rank_dong", "sigungu_code", "eupmyeondong", "period", "snapshot_ym"),
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
