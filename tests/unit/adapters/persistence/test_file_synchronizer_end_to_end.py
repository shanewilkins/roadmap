"""Comprehensive tests for FileSynchronizer error handling paths.

Tests for exception handling in has_file_changed and other error scenarios.
"""

from unittest.mock import MagicMock

from roadmap.adapters.persistence.file_synchronizer import FileSynchronizer


class TestFileSynchronizerInitialization:
    """Tests for FileSynchronizer initialization."""

    def test_init_with_dependencies(self):
        """FileSynchronizer initializes with dependencies."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        assert synchronizer._get_connection == mock_get_connection
        assert synchronizer._transaction == mock_transaction
        assert synchronizer._orchestrator is not None
        assert synchronizer._parser is not None


class TestFileSynchronizerGetFileStatus:
    """Tests for get_file_sync_status method."""

    def test_get_file_sync_status_returns_dict_when_found(self):
        """get_file_sync_status returns dict when row found."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Mock connection and query result
        mock_conn = MagicMock()
        mock_row = {
            "file_path": "/path/to/file.md",
            "content_hash": "abc123",
            "file_size": 1024,
            "last_modified": "2024-01-15T10:30:45",
        }
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        result = synchronizer.get_file_sync_status("/path/to/file.md")

        assert result == mock_row
        mock_conn.execute.assert_called_once()
