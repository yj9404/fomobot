"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "price_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("market", sa.String(10), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float()),
        sa.Column("high", sa.Float()),
        sa.Column("low", sa.Float()),
        sa.Column("close_adj", sa.Float(), nullable=False),
        sa.Column("volume", sa.BigInteger()),
        sa.Column("market_cap", sa.BigInteger()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "market", "date", name="uq_price_daily"),
    )
    op.create_index("ix_price_daily_market_date", "price_daily", ["market", "date"])
    op.create_index("ix_price_daily_ticker_date", "price_daily", ["ticker", "date"])

    op.create_table(
        "index_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("index_code", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("close_adj", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("index_code", "date", name="uq_index_daily"),
    )
    op.create_index("ix_index_daily_code_date", "index_daily", ["index_code", "date"])

    op.create_table(
        "ranking_snapshot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("market", sa.String(10), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100)),
        sa.Column("return_pct", sa.Float(), nullable=False),
        sa.Column("mdd_pct", sa.Float()),
        sa.Column("volatility_annualized_pct", sa.Float()),
        sa.Column("excess_return_pct", sa.Float()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_date", "market", "period", "rank", name="uq_ranking_snapshot"
        ),
    )
    op.create_index(
        "ix_ranking_snapshot_market_period_date",
        "ranking_snapshot",
        ["market", "period", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_table("ranking_snapshot")
    op.drop_table("index_daily")
    op.drop_table("price_daily")
