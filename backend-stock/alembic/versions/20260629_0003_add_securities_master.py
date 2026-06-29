"""add securities_master

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "securities_master",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("market", sa.String(10), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", "market", name="uq_securities_master"),
    )
    op.create_index(
        "ix_securities_master_market_name",
        "securities_master",
        ["market", "name"],
    )


def downgrade() -> None:
    op.drop_index("ix_securities_master_market_name", table_name="securities_master")
    op.drop_table("securities_master")
