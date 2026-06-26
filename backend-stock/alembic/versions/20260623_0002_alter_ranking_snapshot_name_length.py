"""alter ranking_snapshot name length

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "ranking_snapshot",
        "name",
        existing_type=sa.String(100),
        type_=sa.String(200),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "ranking_snapshot",
        "name",
        existing_type=sa.String(200),
        type_=sa.String(100),
        existing_nullable=True,
    )
