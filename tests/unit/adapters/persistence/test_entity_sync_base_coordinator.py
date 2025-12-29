"""Tests for base entity sync coordinator."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.persistence.entity_sync_coordinators import (
    EntitySyncCoordinator,
)


class TestEntitySyncCoordinator:
    """Test EntitySyncCoordinator base class."""

    @pytest.fixture
    def mock_connection(self):
        """Create mock database connection."""
        return MagicMock()

    @pytest.fixture
    def mock_transaction(self):
        """Create mock transaction context manager."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=MagicMock())
        ctx.__exit__ = MagicMock(return_value=None)
        return ctx

    @pytest.fixture
    def coordinator(self, mock_connection, mock_transaction):
        """Create coordinator with mocks."""

        def get_conn():
            return mock_connection

        def trans_ctx():
            return mock_transaction

        return EntitySyncCoordinator(get_conn, trans_ctx)

    def test_init(self, mock_connection, mock_transaction):
        """Test coordinator initialization."""

        def get_conn():
            return mock_connection

        def trans_ctx():
            return mock_transaction

        coordinator = EntitySyncCoordinator(get_conn, trans_ctx)
        assert coordinator._get_connection == get_conn
        assert coordinator._transaction == trans_ctx
        assert coordinator._parser is not None

    @pytest.mark.parametrize(
        "return_value,expect_result",
        [
            (("proj-123",), "proj-123"),
            (None, None),
        ],
    )
    def test_get_default_project_id(
        self, coordinator, mock_transaction, return_value, expect_result
    ):
        """Test getting default project ID with various outcomes."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = return_value
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_default_project_id()
        assert result == expect_result

    def test_get_default_project_id_exception(self, coordinator, mock_transaction):
        """Test getting default project ID handles exceptions."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB Error")
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_default_project_id()
        assert result is None

    @pytest.mark.parametrize(
        "return_value,expect_result",
        [
            (("m-456",), "m-456"),
            (None, None),
        ],
    )
    def test_get_milestone_id_by_name(
        self, coordinator, mock_transaction, return_value, expect_result
    ):
        """Test getting milestone ID by name with various outcomes."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = return_value
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_milestone_id_by_name("Q1 2024")
        assert result == expect_result

    def test_get_milestone_id_by_name_exception(self, coordinator, mock_transaction):
        """Test exception handling in milestone lookup."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB Error")
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_milestone_id_by_name("Q1 2024")
        assert result is None

    @pytest.mark.parametrize(
        "input_value,expected_result",
        [
            (None, None),
            ("", None),
            ("2024-01-15", "valid_date"),
            ("invalid-date", None),
        ],
    )
    def test_normalize_date(self, coordinator, input_value, expected_result):
        """Test normalizing dates with various inputs."""
        result = coordinator._normalize_date(input_value)
        if expected_result == "valid_date":
            assert result is not None
        else:
            assert result is None

    def test_normalize_date_already_date(self, coordinator):
        """Test date object is returned as-is."""
        date_obj = datetime(2024, 1, 15).date()
        result = coordinator._normalize_date(date_obj)
        assert result == date_obj

    @pytest.mark.parametrize(
        "data,known_fields,should_have_metadata",
        [
            (
                {
                    "id": "123",
                    "title": "Test",
                    "custom_field": "value",
                    "extra": "data",
                },
                ["id", "title"],
                True,
            ),
            ({"id": "123", "title": "Test"}, ["id", "title"], False),
            ({}, [], False),
        ],
    )
    def test_extract_metadata(
        self, coordinator, data, known_fields, should_have_metadata
    ):
        """Test extracting metadata from data."""
        result = coordinator._extract_metadata(data, known_fields)
        if should_have_metadata:
            assert result is not None
            import json

            parsed = json.loads(result)
            assert "custom_field" in parsed
        else:
            assert result is None

    def test_update_sync_status_success(self, coordinator, mock_transaction):
        """Test updating sync status for a file."""
        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        with patch.object(coordinator._parser, "extract_file_metadata") as mock_extract:
            mock_extract.return_value = {
                "hash": "abc123",
                "size": 1024,
                "modified_time": "2024-01-15T10:00:00",
            }

            coordinator._update_sync_status(Path("test.md"))

            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            assert "file_sync_state" in call_args[0][0]

    def test_update_sync_status_no_metadata(self, coordinator):
        """Test updating sync status with no metadata."""
        with patch.object(
            coordinator._parser, "extract_file_metadata", return_value=None
        ):
            # Should not raise, just return silently
            coordinator._update_sync_status(Path("test.md"))
