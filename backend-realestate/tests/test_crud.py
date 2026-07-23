import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from realestate.db.crud import upsert_transactions_sync


class TestUpsertTransactionsSync:
    """upsert_transactions_sync 함수 테스트 (Session 모킹)."""

    def test_empty_records(self):
        """빈 레코드 리스트가 주어지면 0을 반환하고 쿼리를 실행하지 않음."""
        session = MagicMock(spec=Session)

        result = upsert_transactions_sync(session, [])

        assert result == 0
        session.execute.assert_not_called()
        session.commit.assert_not_called()

    def test_inserts_records(self):
        """정상적인 레코드가 주어지면 insert문을 구성하여 실행함."""
        session = MagicMock(spec=Session)
        mock_result = MagicMock()
        mock_result.rowcount = 2
        session.execute.return_value = mock_result

        # ReTransaction 모델의 컬럼에 맞는 필드 사용
        records = [
            {
                "sigungu_code": "11680",
                "sigungu_name": "강남구",
                "eupmyeondong": "대치동",
                "apt_name": "은마",
                "deal_ym": "202401",
                "deal_day": 10,
                "exclusive_area": 84.0,
                "deal_amount": 100000,
            },
            {
                "sigungu_code": "11680",
                "sigungu_name": "강남구",
                "eupmyeondong": "대치동",
                "apt_name": "은마",
                "deal_ym": "202401",
                "deal_day": 15,
                "exclusive_area": 76.0,
                "deal_amount": 90000,
            },
        ]

        result = upsert_transactions_sync(session, records)

        # 결과 및 세션 호출 검증
        assert result == 2
        session.execute.assert_called_once()
        session.commit.assert_called_once()

        # 실행된 쿼리가 의도한 형태인지 검증
        executed_stmt = session.execute.call_args[0][0]

        # SQL 구문에 'ON CONFLICT DO NOTHING'이 포함되었는지 문자열 비교로 검증
        stmt_str = str(executed_stmt).upper()
        assert "INSERT" in stmt_str
        assert "DO NOTHING" in stmt_str
