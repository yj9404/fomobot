"""add negative_price to corporate_action_flag reason

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-30

detect_nasdaq_negative()가 close_adj<=0(음수/0 가격, auto_adjust 아티팩트나
센티널 데이터)을 발견 시 corporate_action_flag에 reason=negative_price로
자동 격리하기 위해 CHECK CONSTRAINT에 값을 추가한다. 음수는 명백한 데이터
오류라(오탐 여지 없음) split/merge류와 달리 자동 insert 대상이다.
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_OLD_VALUES = "'split','merge','capital_reduction','new_issuance','halted','manual'"
_NEW_VALUES = _OLD_VALUES + ",'negative_price'"


def upgrade() -> None:
    op.execute("ALTER TABLE corporate_action_flag DROP CONSTRAINT IF EXISTS ck_corporate_action_flag_reason")
    op.execute(
        f"ALTER TABLE corporate_action_flag ADD CONSTRAINT ck_corporate_action_flag_reason "
        f"CHECK (reason IN ({_NEW_VALUES}))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE corporate_action_flag DROP CONSTRAINT IF EXISTS ck_corporate_action_flag_reason")
    op.execute(
        f"ALTER TABLE corporate_action_flag ADD CONSTRAINT ck_corporate_action_flag_reason "
        f"CHECK (reason IN ({_OLD_VALUES}))"
    )
