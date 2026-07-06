"""add order_dir to ranking_snapshot

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. order_dir 컬럼 추가 (기존 행은 모두 'desc' 로 초기화)
    op.add_column(
        "ranking_snapshot",
        sa.Column(
            "order_dir",
            sa.String(4),
            nullable=False,
            server_default="desc",
        ),
    )

    # 2. 기존 unique constraint 제거 (snapshot_date, market, period, rank)
    op.drop_constraint("uq_ranking_snapshot", "ranking_snapshot", type_="unique")

    # 3. 새 unique constraint 생성 (order_dir 포함 5컬럼)
    op.create_unique_constraint(
        "uq_ranking_snapshot",
        "ranking_snapshot",
        ["snapshot_date", "market", "period", "order_dir", "rank"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_ranking_snapshot", "ranking_snapshot", type_="unique")
    op.create_unique_constraint(
        "uq_ranking_snapshot",
        "ranking_snapshot",
        ["snapshot_date", "market", "period", "rank"],
    )
    op.drop_column("ranking_snapshot", "order_dir")
