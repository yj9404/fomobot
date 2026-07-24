from unittest.mock import patch, MagicMock

from realestate.batch.complex_aggregate import aggregate_all_sigungu_complex


def test_aggregate_all_sigungu_complex_no_data():
    with patch("realestate.batch.complex_aggregate.SyncSessionLocal") as mock_session:
        mock_instance = mock_session.return_value.__enter__.return_value
        mock_instance.execute.return_value = []
        aggregate_all_sigungu_complex(["202310"])
        mock_instance.execute.assert_called_once()


def test_aggregate_all_sigungu_complex_with_data():
    with patch("realestate.batch.complex_aggregate.SyncSessionLocal") as mock_session:
        with patch(
            "realestate.batch.complex_aggregate.upsert_complex_stats_sync"
        ) as mock_upsert:
            # Setup mock for execute returning rows
            mock_instance = mock_session.return_value.__enter__.return_value

            row = MagicMock()
            row._mapping = {
                "sigungu_code": "11110",
                "eupmyeondong": "창신동",
                "apt_name": "창신쌍용1",
                "deal_ym": "202310",
                "deal_date": "20231001",
                "price_per_sqm": 1000.0,
            }
            mock_instance.execute.return_value = [row]

            aggregate_all_sigungu_complex(["202310"])

            mock_upsert.assert_called_once()
            args, _ = mock_upsert.call_args
            assert len(args[1]) == 1
            assert args[1][0]["sigungu_code"] == "11110"
