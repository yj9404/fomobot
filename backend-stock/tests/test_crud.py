from unittest.mock import MagicMock

from fomobot.db.crud import (
    upsert_price_daily_sync,
    upsert_index_daily_sync,
    upsert_ranking_snapshots_sync,
    upsert_securities_master_sync,
    upsert_market_breadth_daily_sync,
)
from fomobot.db.models import (
    PriceDaily,
    IndexDaily,
    RankingSnapshot,
    SecuritiesMaster,
    MarketBreadthDaily,
)


def test_upsert_price_daily_sync_empty(monkeypatch):
    mock_insert = MagicMock()
    monkeypatch.setattr("sqlalchemy.dialects.postgresql.insert", mock_insert)
    session = MagicMock()

    upsert_price_daily_sync(session, [])

    mock_insert.assert_not_called()
    session.execute.assert_not_called()
    session.commit.assert_not_called()


def test_upsert_price_daily_sync_with_records(monkeypatch):
    mock_insert = MagicMock()
    mock_stmt = MagicMock()
    mock_insert.return_value.values.return_value = mock_stmt
    mock_stmt.on_conflict_do_update.return_value = "final_stmt"

    # Mock stmt.excluded
    mock_excluded = MagicMock()
    mock_excluded.open = "ex_open"
    mock_excluded.high = "ex_high"
    mock_excluded.low = "ex_low"
    mock_excluded.close_adj = "ex_close_adj"
    mock_excluded.volume = "ex_volume"
    mock_excluded.market_cap = "ex_market_cap"
    mock_stmt.excluded = mock_excluded

    monkeypatch.setattr("sqlalchemy.dialects.postgresql.insert", mock_insert)
    session = MagicMock()

    records = [{"ticker": "AAPL"}]
    upsert_price_daily_sync(session, records)

    mock_insert.assert_called_once_with(PriceDaily)
    mock_insert.return_value.values.assert_called_once_with(records)
    mock_stmt.on_conflict_do_update.assert_called_once_with(
        constraint="uq_price_daily",
        set_={
            "open": "ex_open",
            "high": "ex_high",
            "low": "ex_low",
            "close_adj": "ex_close_adj",
            "volume": "ex_volume",
            "market_cap": "ex_market_cap",
        },
    )
    session.execute.assert_called_once_with("final_stmt")
    session.commit.assert_called_once()


def test_upsert_index_daily_sync_empty(monkeypatch):
    mock_insert = MagicMock()
    monkeypatch.setattr("sqlalchemy.dialects.postgresql.insert", mock_insert)
    session = MagicMock()

    upsert_index_daily_sync(session, [])

    mock_insert.assert_not_called()
    session.execute.assert_not_called()
    session.commit.assert_not_called()


def test_upsert_index_daily_sync_with_records(monkeypatch):
    mock_insert = MagicMock()
    mock_stmt = MagicMock()
    mock_insert.return_value.values.return_value = mock_stmt
    mock_stmt.on_conflict_do_update.return_value = "final_stmt"

    mock_excluded = MagicMock()
    mock_excluded.close_adj = "ex_close_adj"
    mock_stmt.excluded = mock_excluded

    monkeypatch.setattr("sqlalchemy.dialects.postgresql.insert", mock_insert)
    session = MagicMock()

    records = [{"ticker": "SPY"}]
    upsert_index_daily_sync(session, records)

    mock_insert.assert_called_once_with(IndexDaily)
    mock_insert.return_value.values.assert_called_once_with(records)
    mock_stmt.on_conflict_do_update.assert_called_once_with(
        constraint="uq_index_daily",
        set_={"close_adj": "ex_close_adj"},
    )
    session.execute.assert_called_once_with("final_stmt")
    session.commit.assert_called_once()


def test_upsert_ranking_snapshots_sync_empty(monkeypatch):
    mock_insert = MagicMock()
    monkeypatch.setattr("sqlalchemy.dialects.postgresql.insert", mock_insert)
    session = MagicMock()

    upsert_ranking_snapshots_sync(session, [])

    mock_insert.assert_not_called()
    session.execute.assert_not_called()
    session.commit.assert_not_called()


def test_upsert_ranking_snapshots_sync_with_records(monkeypatch):
    mock_insert = MagicMock()
    mock_stmt = MagicMock()
    mock_insert.return_value.values.return_value = mock_stmt
    mock_stmt.on_conflict_do_update.return_value = "final_stmt"

    mock_excluded = MagicMock()
    mock_excluded.ticker = "ex_ticker"
    mock_excluded.name = "ex_name"
    mock_excluded.return_pct = "ex_return_pct"
    mock_excluded.mdd_pct = "ex_mdd_pct"
    mock_excluded.volatility_annualized_pct = "ex_volatility"
    mock_excluded.excess_return_pct = "ex_excess_return"
    mock_excluded.close_price_at_snapshot = "ex_close"
    mock_stmt.excluded = mock_excluded

    mock_coalesce = MagicMock(return_value="mocked_coalesce")
    monkeypatch.setattr("fomobot.db.crud.func.coalesce", mock_coalesce)
    monkeypatch.setattr("sqlalchemy.dialects.postgresql.insert", mock_insert)
    session = MagicMock()

    records = [{"ticker": "AAPL"}]
    upsert_ranking_snapshots_sync(session, records)

    mock_insert.assert_called_once_with(RankingSnapshot)
    mock_insert.return_value.values.assert_called_once_with(records)

    assert mock_coalesce.call_count == 2
    mock_coalesce.assert_any_call(
        "ex_close",
        RankingSnapshot.close_price_at_snapshot,
    )
    mock_coalesce.assert_any_call(
        mock_stmt.excluded.market_cap,
        RankingSnapshot.market_cap,
    )

    mock_stmt.on_conflict_do_update.assert_called_once_with(
        constraint="uq_ranking_snapshot",
        set_={
            "ticker": "ex_ticker",
            "name": "ex_name",
            "return_pct": "ex_return_pct",
            "mdd_pct": "ex_mdd_pct",
            "volatility_annualized_pct": "ex_volatility",
            "excess_return_pct": "ex_excess_return",
            "close_price_at_snapshot": "mocked_coalesce",
            "market_cap": "mocked_coalesce",
        },
    )
    session.execute.assert_called_once_with("final_stmt")
    session.commit.assert_called_once()


def test_upsert_securities_master_sync_empty(monkeypatch):
    mock_insert = MagicMock()
    monkeypatch.setattr("sqlalchemy.dialects.postgresql.insert", mock_insert)
    session = MagicMock()

    upsert_securities_master_sync(session, [])

    mock_insert.assert_not_called()
    session.execute.assert_not_called()
    session.commit.assert_not_called()


def test_upsert_securities_master_sync_with_records(monkeypatch):
    mock_insert = MagicMock()
    mock_stmt = MagicMock()
    mock_insert.return_value.values.return_value = mock_stmt
    mock_stmt.on_conflict_do_update.return_value = "final_stmt"

    mock_excluded = MagicMock()
    mock_excluded.name = "ex_name"
    mock_excluded.is_active = "ex_is_active"
    mock_stmt.excluded = mock_excluded

    mock_coalesce = MagicMock(return_value="mocked_coalesce")
    mock_now = MagicMock(return_value="mocked_now")
    monkeypatch.setattr("fomobot.db.crud.func.coalesce", mock_coalesce)
    monkeypatch.setattr("fomobot.db.crud.func.now", mock_now)
    monkeypatch.setattr("sqlalchemy.dialects.postgresql.insert", mock_insert)
    session = MagicMock()

    records = [{"ticker": "AAPL"}]
    upsert_securities_master_sync(session, records)

    mock_insert.assert_called_once_with(SecuritiesMaster)
    mock_insert.return_value.values.assert_called_once_with(records)

    mock_coalesce.assert_called_once_with(
        "ex_name",
        SecuritiesMaster.name,
    )
    mock_now.assert_called_once()

    mock_stmt.on_conflict_do_update.assert_called_once_with(
        constraint="uq_securities_master",
        set_={
            "name": "mocked_coalesce",
            "is_active": "ex_is_active",
            "updated_at": "mocked_now",
        },
    )
    session.execute.assert_called_once_with("final_stmt")
    session.commit.assert_called_once()


def test_upsert_market_breadth_daily_sync(monkeypatch):
    mock_insert = MagicMock()
    mock_stmt = MagicMock()
    mock_insert.return_value.values.return_value = mock_stmt
    mock_stmt.on_conflict_do_update.return_value = "final_stmt"

    mock_excluded = MagicMock()
    mock_excluded.advancers = "ex_advancers"
    mock_excluded.decliners = "ex_decliners"
    mock_excluded.unchanged = "ex_unchanged"
    mock_excluded.excluded = "ex_excluded"
    mock_excluded.halted = "ex_halted"
    mock_excluded.total = "ex_total"
    mock_stmt.excluded = mock_excluded

    monkeypatch.setattr("sqlalchemy.dialects.postgresql.insert", mock_insert)
    session = MagicMock()

    record = {"market": "nasdaq"}
    upsert_market_breadth_daily_sync(session, record)

    mock_insert.assert_called_once_with(MarketBreadthDaily)
    mock_insert.return_value.values.assert_called_once_with(**record)

    mock_stmt.on_conflict_do_update.assert_called_once_with(
        constraint="uq_market_breadth_daily",
        set_={
            "advancers": "ex_advancers",
            "decliners": "ex_decliners",
            "unchanged": "ex_unchanged",
            "excluded": "ex_excluded",
            "halted": "ex_halted",
            "total": "ex_total",
        },
    )
    session.execute.assert_called_once_with("final_stmt")
    session.commit.assert_called_once()
