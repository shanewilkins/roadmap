"""Comprehensive tests for FileSynchronizer error handling paths.

Tests for exception handling in has_file_changed and other error scenarios.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_get_file_sync_status_returns_none_when_not_found(self):
        """get_file_sync_status returns None when row not found."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Mock connection and query result (no row)
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        result = synchronizer.get_file_sync_status("/path/to/missing.md")

        assert result is None


class TestFileSynchronizerUpdateFileStatus:
    """Tests for update_file_sync_status method."""

    def test_update_file_sync_status_executes_insert(self):
        """update_file_sync_status executes INSERT OR REPLACE."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Mock transaction context manager
        mock_conn = MagicMock()
        mock_transaction.return_value.__enter__.return_value = mock_conn
        mock_transaction.return_value.__exit__.return_value = None

        synchronizer.update_file_sync_status(
            "/path/to/file.md", "abc123", 1024, "2024-01-15T10:30:45"
        )

        # Should have called execute on the connection
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        # Check that it's an INSERT OR REPLACE statement
        assert "INSERT OR REPLACE" in call_args[0][0]


class TestFileSynchronizerHasFileChangedSuccess:
    """Tests for has_file_changed successful cases."""

    def test_has_file_changed_returns_true_when_file_missing(self):
        """has_file_changed returns True when file doesn't exist."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Use a path that definitely doesn't exist
        missing_path = Path("/nonexistent/definitely/missing.md")

        result = synchronizer.has_file_changed(missing_path)

        assert result is True

    def test_has_file_changed_returns_true_when_no_sync_status(self, tmp_path):
        """has_file_changed returns True when sync status not found."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Create a real file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Mock get_file_sync_status to return None
        with patch.object(synchronizer, "get_file_sync_status", return_value=None):
            result = synchronizer.has_file_changed(test_file)

        assert result is True

    def test_has_file_changed_returns_false_when_hash_matches(self, tmp_path):
        """has_file_changed returns False when hash matches."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Create a real file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Calculate the actual hash
        actual_hash = synchronizer._parser.calculate_file_hash(test_file)

        # Mock get_file_sync_status to return matching hash
        sync_status = {
            "file_path": str(test_file),
            "content_hash": actual_hash,
            "file_size": test_file.stat().st_size,
            "last_modified": "2024-01-15T10:30:45",
        }

        with patch.object(
            synchronizer, "get_file_sync_status", return_value=sync_status
        ):
            result = synchronizer.has_file_changed(test_file)

        assert result is False

    def test_has_file_changed_returns_true_when_hash_differs(self, tmp_path):
        """has_file_changed returns True when hash differs."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Create a real file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Mock get_file_sync_status with different hash
        sync_status = {
            "file_path": str(test_file),
            "content_hash": "different_hash_entirely",
            "file_size": 999,
            "last_modified": "2024-01-15T10:30:45",
        }

        with patch.object(
            synchronizer, "get_file_sync_status", return_value=sync_status
        ):
            result = synchronizer.has_file_changed(test_file)

        assert result is True


class TestFileSynchronizerHasFileChangedErrors:
    """Tests for has_file_changed error handling."""

    def test_has_file_changed_returns_true_on_exception(self, tmp_path):
        """has_file_changed returns True when exception occurs."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Create a real file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Mock calculate_file_hash to raise exception
        with patch.object(
            synchronizer._parser,
            "calculate_file_hash",
            side_effect=Exception("Hash calculation failed"),
        ):
            result = synchronizer.has_file_changed(test_file)

        # Should return True (conservative: treat as changed)
        assert result is True

    def test_has_file_changed_logs_error_on_exception(self, tmp_path):
        """has_file_changed logs error when exception occurs."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Create a real file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Mock calculate_file_hash to raise exception
        with patch.object(
            synchronizer._parser,
            "calculate_file_hash",
            side_effect=Exception("Hash calculation failed"),
        ):
            with patch(
                "roadmap.adapters.persistence.file_synchronizer.logger"
            ) as mock_logger:
                synchronizer.has_file_changed(test_file)

                # Logger.error should have been called
                mock_logger.error.assert_called_once()
                call_args = mock_logger.error.call_args
                assert "failed_to_check_file_changes" in call_args[0][0]


class TestFileSynchronizerDelegation:
    """Tests for delegation to orchestrator."""

    def test_sync_directory_incremental_delegates_to_orchestrator(self):
        """sync_directory_incremental delegates to orchestrator."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.sync_directory_incremental.return_value = {"synced": 5}
        synchronizer._orchestrator = mock_orchestrator

        test_dir = Path("/path/to/roadmap")
        result = synchronizer.sync_directory_incremental(test_dir)

        assert result == {"synced": 5}
        mock_orchestrator.sync_directory_incremental.assert_called_once_with(test_dir)

    def test_full_rebuild_from_git_delegates_to_orchestrator(self):
        """full_rebuild_from_git delegates to orchestrator."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.full_rebuild_from_git.return_value = {"rebuilt": 10}
        synchronizer._orchestrator = mock_orchestrator

        test_dir = Path("/path/to/roadmap")
        result = synchronizer.full_rebuild_from_git(test_dir)

        assert result == {"rebuilt": 10}
        mock_orchestrator.full_rebuild_from_git.assert_called_once_with(test_dir)

    def test_should_do_full_rebuild_delegates_to_orchestrator(self):
        """should_do_full_rebuild delegates to orchestrator."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.should_do_full_rebuild.return_value = True
        synchronizer._orchestrator = mock_orchestrator

        test_dir = Path("/path/to/roadmap")
        result = synchronizer.should_do_full_rebuild(test_dir, threshold=50)

        assert result is True
        mock_orchestrator.should_do_full_rebuild.assert_called_once_with(test_dir, 50)

    def test_should_do_full_rebuild_uses_default_threshold(self):
        """should_do_full_rebuild uses default threshold."""
        mock_get_connection = MagicMock()
        mock_transaction = MagicMock()

        synchronizer = FileSynchronizer(mock_get_connection, mock_transaction)

        # Mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.should_do_full_rebuild.return_value = False
        synchronizer._orchestrator = mock_orchestrator

        test_dir = Path("/path/to/roadmap")
        synchronizer.should_do_full_rebuild(test_dir)

        # Should use default 50% threshold
        mock_orchestrator.should_do_full_rebuild.assert_called_once_with(test_dir, 50)
