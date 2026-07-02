"""add market_cap to ranking_snapshot

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-02

ranking_snapshot에 시총(market_cap)을 저장해 cap_tier 필터링 시
price_daily 조인 없이 RankingSnapshot 단독으로 필터링할 수 있도록 한다.
KOSPI: 랭킹 계산 시 price_daily의 market_cap 사용
NASDAQ: 랭킹 계산 후 yfinance fast_info에서 상위 종목 시총 조회
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ranking_snapshot",
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ranking_snapshot", "market_cap")
