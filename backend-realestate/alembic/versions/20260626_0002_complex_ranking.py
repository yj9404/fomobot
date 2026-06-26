"""단지 단위 집계·랭킹 테이블 교체

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 기존 동/구 단위 테이블 제거
    op.drop_table("re_ranking_snapshot")
    op.drop_table("re_monthly_stat")

    # 단지 월별 집계
    op.create_table(
        "re_complex_stat",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("complex_key", sa.String(64), nullable=False),
        sa.Column("sigungu_code", sa.String(5), nullable=False),
        sa.Column("eupmyeondong", sa.String(100), nullable=False),
        sa.Column("apt_name", sa.String(200), nullable=False),
        sa.Column("apt_name_norm", sa.String(200), nullable=False),
        sa.Column("deal_ym", sa.String(6), nullable=False),
        sa.Column("median_price_per_sqm", sa.Numeric(12, 2)),
        sa.Column("transaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("complex_key", "deal_ym", name="uq_re_complex_stat"),
    )
    op.create_index("ix_re_complex_stat_sigungu_ym", "re_complex_stat", ["sigungu_code", "deal_ym"])
    op.create_index("ix_re_complex_stat_key_ym", "re_complex_stat", ["complex_key", "deal_ym"])

    # 단지 랭킹 스냅샷
    op.create_table(
        "re_complex_ranking_snapshot",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("snapshot_ym", sa.String(6), nullable=False),
        sa.Column("period", sa.String(5), nullable=False),
        sa.Column("rank", sa.Integer()),
        sa.Column("complex_key", sa.String(64), nullable=False),
        sa.Column("sigungu_code", sa.String(5), nullable=False),
        sa.Column("sigungu_name", sa.String(100), nullable=False),
        sa.Column("eupmyeondong", sa.String(100), nullable=False),
        sa.Column("apt_name", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(400), nullable=False),
        sa.Column("start_ym", sa.String(6), nullable=False),
        sa.Column("end_ym", sa.String(6), nullable=False),
        sa.Column("start_price", sa.Numeric(12, 2)),
        sa.Column("end_price", sa.Numeric(12, 2)),
        sa.Column("change_pct", sa.Numeric(8, 2)),
        sa.Column("start_tx_count", sa.Integer()),
        sa.Column("end_tx_count", sa.Integer()),
        sa.Column("data_status", sa.String(20), nullable=False),
        sa.Column("insufficient_reason", sa.Text()),
        sa.Column("windows_overlap", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_ym", "period", "complex_key",
            name="uq_re_complex_ranking_snapshot",
        ),
    )
    op.create_index("ix_re_complex_rank_period_ym_rank", "re_complex_ranking_snapshot", ["period", "snapshot_ym", "rank"])
    op.create_index("ix_re_complex_rank_sigungu", "re_complex_ranking_snapshot", ["sigungu_code", "period", "snapshot_ym"])
    op.create_index("ix_re_complex_rank_dong", "re_complex_ranking_snapshot", ["sigungu_code", "eupmyeondong", "period", "snapshot_ym"])


def downgrade() -> None:
    op.drop_table("re_complex_ranking_snapshot")
    op.drop_table("re_complex_stat")

    # 기존 테이블 복원
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
