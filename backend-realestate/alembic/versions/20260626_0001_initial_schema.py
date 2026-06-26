"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "re_transaction",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sigungu_code", sa.String(5), nullable=False),
        sa.Column("sigungu_name", sa.String(50), nullable=False),
        sa.Column("eupmyeondong", sa.String(50), nullable=False),
        sa.Column("apt_name", sa.String(100), nullable=False),
        sa.Column("deal_ym", sa.String(6), nullable=False),
        sa.Column("deal_day", sa.SmallInteger(), nullable=False),
        sa.Column("exclusive_area", sa.Numeric(8, 2), nullable=False),
        sa.Column("floor", sa.SmallInteger()),
        sa.Column("deal_amount", sa.BigInteger(), nullable=False),
        sa.Column("price_per_sqm", sa.Numeric(12, 2)),
        sa.Column("build_year", sa.SmallInteger()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sigungu_code", "eupmyeondong", "apt_name",
            "deal_ym", "deal_day", "exclusive_area", "floor", "deal_amount",
            name="uq_re_transaction",
        ),
    )
    op.create_index("ix_re_transaction_sigungu_ym", "re_transaction", ["sigungu_code", "deal_ym"])
    op.create_index("ix_re_transaction_dong_ym", "re_transaction", ["sigungu_code", "eupmyeondong", "deal_ym"])

    op.create_table(
        "re_monthly_stat",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sigungu_code", sa.String(5), nullable=False),
        sa.Column("eupmyeondong", sa.String(50)),
        sa.Column("deal_ym", sa.String(6), nullable=False),
        sa.Column("median_price_per_sqm", sa.Numeric(12, 2)),
        sa.Column("transaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sigungu_code", "eupmyeondong", "deal_ym", name="uq_re_monthly_stat"),
    )
    op.create_index("ix_re_monthly_stat_gu_ym", "re_monthly_stat", ["sigungu_code", "deal_ym"])
    op.create_index("ix_re_monthly_stat_dong_ym", "re_monthly_stat", ["sigungu_code", "eupmyeondong", "deal_ym"])

    op.create_table(
        "re_ranking_snapshot",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("snapshot_ym", sa.String(6), nullable=False),
        sa.Column("region_level", sa.String(4), nullable=False),
        sa.Column("period", sa.String(3), nullable=False),
        sa.Column("rank", sa.Integer()),
        sa.Column("sigungu_code", sa.String(5), nullable=False),
        sa.Column("sigungu_name", sa.String(50), nullable=False),
        sa.Column("eupmyeondong", sa.String(50)),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("start_ym", sa.String(6), nullable=False),
        sa.Column("end_ym", sa.String(6), nullable=False),
        sa.Column("start_price", sa.Numeric(12, 2)),
        sa.Column("end_price", sa.Numeric(12, 2)),
        sa.Column("change_pct", sa.Numeric(8, 2)),
        sa.Column("start_tx_count", sa.Integer()),
        sa.Column("end_tx_count", sa.Integer()),
        sa.Column("data_status", sa.String(20), nullable=False),
        sa.Column("insufficient_reason", sa.String(200)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_ym", "region_level", "period", "sigungu_code", "eupmyeondong",
            name="uq_re_ranking_snapshot",
        ),
    )
    op.create_index("ix_re_ranking_snapshot_query", "re_ranking_snapshot", ["region_level", "period", "snapshot_ym"])
    op.create_index("ix_re_ranking_snapshot_rank", "re_ranking_snapshot", ["region_level", "period", "snapshot_ym", "rank"])

    op.create_table(
        "re_collection_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sigungu_code", sa.String(5), nullable=False),
        sa.Column("deal_ym", sa.String(6), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("transaction_count", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("collected_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sigungu_code", "deal_ym", name="uq_re_collection_log"),
    )
    op.create_index("ix_re_collection_log_status", "re_collection_log", ["sigungu_code", "status"])


def downgrade() -> None:
    op.drop_table("re_collection_log")
    op.drop_table("re_ranking_snapshot")
    op.drop_table("re_monthly_stat")
    op.drop_table("re_transaction")
