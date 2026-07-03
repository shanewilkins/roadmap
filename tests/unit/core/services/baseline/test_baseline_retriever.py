"""Tests for BaselineRetriever fallback behavior."""

from unittest.mock import MagicMock

from roadmap.core.services.baseline.baseline_retriever import BaselineRetriever


def test_get_current_baseline_prefers_core_db():
    """Retriever should use core.db baseline when available."""
    core = MagicMock()
    core.db.get_sync_baseline.return_value = {"a": 1}
    db_session = MagicMock()

    result = BaselineRetriever.get_current_baseline(core=core, db_session=db_session)

    assert result == {"a": 1}
    core.db.get_sync_baseline.assert_called_once()
    db_session.get_sync_baseline.assert_not_called()


def test_get_current_baseline_core_db_exception_returns_empty_dict():
    """Core DB exception currently short-circuits to empty baseline."""
    core = MagicMock()
    core.db.get_sync_baseline.side_effect = RuntimeError("boom")
    db_session = MagicMock()
    db_session.get_sync_baseline.return_value = {"from_session": True}

    result = BaselineRetriever.get_current_baseline(core=core, db_session=db_session)

    assert result == {}
    core.db.get_sync_baseline.assert_called_once()
    db_session.get_sync_baseline.assert_not_called()


def test_get_current_baseline_uses_db_session_when_core_unavailable():
    """Retriever should fallback to db_session when core source missing."""
    db_session = MagicMock()
    db_session.get_sync_baseline.return_value = {"cached": "yes"}

    result = BaselineRetriever.get_current_baseline(core=None, db_session=db_session)

    assert result == {"cached": "yes"}
    db_session.get_sync_baseline.assert_called_once()


def test_get_current_baseline_db_session_exception_returns_empty_dict():
    """db_session failures should degrade to empty baseline."""
    db_session = MagicMock()
    db_session.get_sync_baseline.side_effect = RuntimeError("db down")

    result = BaselineRetriever.get_current_baseline(core=None, db_session=db_session)

    assert result == {}


def test_get_current_baseline_none_results_normalized_to_empty_dict():
    """Falsy baseline payloads should normalize to empty dict."""
    core = MagicMock()
    core.db.get_sync_baseline.return_value = None

    result = BaselineRetriever.get_current_baseline(core=core, db_session=None)

    assert result == {}
