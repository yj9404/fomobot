"""add first_valid_date and start_validity to ranking_snapshot

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-18

장기 거래정지·신규상장 등으로 기간 윈도우 시작 부분에 데이터가 없거나
실거래가 아닌(volume=0 동결) 경우, "N일 수익률"이 실제로는 훨씬 긴 기간
대비인데도 그대로 표시되는 문제 대응(002210이 halt 중 조용한 basis
변경으로 30d/90d/365d가 전부 동일한 +73.48%로 표시된 사고).

return_pct 등 기존 계산값은 전혀 건드리지 않는다 — 이 계산에 실제로
쓰인 첫 유효 가격의 날짜(first_valid_date)와 그 사유(start_validity:
"gap"=데이터 자체 없음 / "halted"=데이터는 있으나 비거래일)만 표시용
메타데이터로 추가한다. 정상(윈도우 전체 실거래)이면 둘 다 NULL.
halt_resumption과 달리 1d 전용이 아니라 전 period 대상.
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ranking_snapshot",
        sa.Column("first_valid_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "ranking_snapshot",
        sa.Column("start_validity", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ranking_snapshot", "start_validity")
    op.drop_column("ranking_snapshot", "first_valid_date")
