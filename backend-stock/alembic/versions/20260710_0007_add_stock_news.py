"""add stock_news

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_news",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("link", sa.String(1000), nullable=False),
        sa.Column("published_at", sa.Date(), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "link", name="uq_stock_news"),
    )
    op.create_index("ix_stock_news_ticker", "stock_news", ["ticker"])


def downgrade() -> None:
    op.drop_index("ix_stock_news_ticker", table_name="stock_news")
    op.drop_table("stock_news")
