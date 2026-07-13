"""add market_breadth_daily

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_breadth_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("market", sa.String(10), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("advancers", sa.Integer(), nullable=False),
        sa.Column("decliners", sa.Integer(), nullable=False),
        sa.Column("unchanged", sa.Integer(), nullable=False),
        sa.Column("excluded", sa.Integer(), nullable=False),
        sa.Column("halted", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("market", "date", name="uq_market_breadth_daily"),
    )
    op.create_index(
        "ix_market_breadth_daily_market_date", "market_breadth_daily", ["market", "date"]
    )


def downgrade() -> None:
    op.drop_index("ix_market_breadth_daily_market_date", table_name="market_breadth_daily")
    op.drop_table("market_breadth_daily")
