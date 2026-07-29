"""add corporate_action_flag

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-29

액면분할·병합·감자 등 corporate action으로 close_adj가 오염된 종목을
랭킹 계산에서 제외하기 위한 격리 목록 테이블. "랭킹에서 뺄 종목"의
단일 진실 소스 — 종목당 활성 레코드 1개(ticker unique).
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corporate_action_flag",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("market", sa.String(10), nullable=False),
        sa.Column("flag_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(20), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("detected_signal", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", name="uq_corporate_action_flag_ticker"),
        sa.CheckConstraint(
            "reason IN ('split','merge','capital_reduction','new_issuance','halted','manual')",
            name="ck_corporate_action_flag_reason",
        ),
        sa.CheckConstraint(
            "status IN ('excluded','pending','resolved')",
            name="ck_corporate_action_flag_status",
        ),
    )
    op.create_index(
        "ix_corporate_action_flag_status", "corporate_action_flag", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_corporate_action_flag_status", table_name="corporate_action_flag")
    op.drop_table("corporate_action_flag")
