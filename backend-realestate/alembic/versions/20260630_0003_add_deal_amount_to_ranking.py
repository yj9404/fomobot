"""re_complex_ranking_snapshot에 중위 거래금액 컬럼 추가

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "re_complex_ranking_snapshot",
        sa.Column("start_deal_amount", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "re_complex_ranking_snapshot",
        sa.Column("end_deal_amount", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("re_complex_ranking_snapshot", "end_deal_amount")
    op.drop_column("re_complex_ranking_snapshot", "start_deal_amount")
