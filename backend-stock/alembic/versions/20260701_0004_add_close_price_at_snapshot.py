"""add close_price_at_snapshot to ranking_snapshot

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-01

as_of 시점의 실제 수정종가를 ranking_snapshot에 저장해
백테스트가 price_daily 과거분에 의존하지 않도록 한다.
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ranking_snapshot",
        sa.Column("close_price_at_snapshot", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ranking_snapshot", "close_price_at_snapshot")
