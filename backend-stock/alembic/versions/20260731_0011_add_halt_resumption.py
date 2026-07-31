"""add halt_resumption to ranking_snapshot

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-31

장기 거래정지(volume=0 10거래일 이상 연속, close_adj 동결) 후 재개 첫
실거래일에는 가격제한폭이 적용되지 않아 1d 등락이 ±30%를 크게 넘을 수
있다(예: 002210 +85%). 데이터 오염이 아니라 정상 현상이므로 값은 그대로
두고, 프론트가 tooltip으로 설명할 수 있도록 플래그만 저장한다.

이번 단계는 1d period만 채운다(다른 period는 항상 False) — 컬럼명은
기간 중립(halt_resumption)으로 두어 향후 확장 여지를 남긴다.
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ranking_snapshot",
        sa.Column(
            "halt_resumption", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )


def downgrade() -> None:
    op.drop_column("ranking_snapshot", "halt_resumption")
