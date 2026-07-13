"""region news (단지 단위 -> 동/구 지역 단위 전환)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_re_complex_news_key", table_name="re_complex_news")
    op.drop_table("re_complex_news")

    op.create_table(
        "re_region_news",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("region_key", sa.String(64), nullable=False),
        sa.Column("region_label", sa.String(100), nullable=False),
        sa.Column("granularity", sa.String(10), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("link", sa.String(1000), nullable=False),
        sa.Column("published_at", sa.Date(), nullable=False),
        sa.Column(
            "collected_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("region_key", "link", name="uq_re_region_news"),
    )
    op.create_index("ix_re_region_news_key", "re_region_news", ["region_key"])


def downgrade() -> None:
    op.drop_index("ix_re_region_news_key", table_name="re_region_news")
    op.drop_table("re_region_news")

    op.create_table(
        "re_complex_news",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("complex_key", sa.String(64), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("link", sa.String(1000), nullable=False),
        sa.Column("published_at", sa.Date(), nullable=False),
        sa.Column(
            "collected_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("complex_key", "link", name="uq_re_complex_news"),
    )
    op.create_index("ix_re_complex_news_key", "re_complex_news", ["complex_key"])
