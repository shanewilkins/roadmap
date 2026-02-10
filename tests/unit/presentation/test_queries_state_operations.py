"""Tests for QueryService state-checking operations (queries.py module).

Tests for state checking and progress calculations.
Covers file change detection and milestone progress tracking.
"""

from pathlib import Path
from unittest import mock

from roadmap.adapters.persistence.storage.queries import QueryService


class TestQueryServiceInitialization:
    """Test QueryService initialization and setup."""

    import pytest

    @pytest.mark.parametrize(
        "state_manager,expected",
        [
            (mock.MagicMock(), True),
            (None, False),
        ],
    )
    def test_initialization_param(self, state_manager, expected):
        service = QueryService(state_manager)
        if expected:
            assert service.state_manager == state_manager
        else:
            assert service.state_manager is None


class TestHasFileChanges:
    """Test has_file_changes method for detecting file modifications."""

    import pytest

    @pytest.mark.parametrize(
        "desc,setup_fn,expected",
        [
            ("no_roadmap_dir", lambda: (mock.MagicMock(), False), False),
            ("no_files", lambda: (mock.MagicMock(), False), False),
        ],
    )
    def test_has_file_changes_param(self, desc, setup_fn, expected):
        mock_state_manager, exists = setup_fn()
        with mock.patch.object(Path, "exists", return_value=exists):
            with mock.patch.object(Path, "parent", new_callable=mock.PropertyMock):
                service = QueryService(mock_state_manager)
                result = service.has_file_changes()
                assert result is expected

    def test_has_file_changes_with_new_file(self, mock_path_factory):
        """Test has_file_changes detects new markdown files."""
        mock_state_manager = mock.MagicMock()
        mock_roadmap_dir = Path("/test/.roadmap")
        mock_state_manager.db_path = mock_roadmap_dir / "db.sqlite"

        mock_file = mock_path_factory(name="issues/test.md", exists=True)
        mock_file.read_bytes = mock.Mock(return_value=b"file content")

        mock_conn = mock.MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None  # No stored hash

        with mock.patch("hashlib.sha256") as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "abc123"

            with mock.patch.object(Path, "exists", return_value=True):
                with mock.patch("pathlib.Path.rglob") as mock_rglob:
                    mock_rglob.return_value = [mock_file]

                    with mock.patch.object(
                        mock_state_manager, "transaction"
                    ) as mock_transaction:
                        mock_transaction.return_value.__enter__.return_value = mock_conn

                        service = QueryService(mock_state_manager)
                        result = service.has_file_changes()

                        # New file (no stored hash) means changes detected
                        assert result is True

    def test_has_file_changes_with_modified_file(self, mock_path_factory):
        """Test has_file_changes detects modified markdown files."""
        mock_state_manager = mock.MagicMock()
        mock_roadmap_dir = Path("/test/.roadmap")
        mock_state_manager.db_path = mock_roadmap_dir / "db.sqlite"

        mock_file = mock_path_factory(name="issues/test.md", exists=True)
        mock_file.read_bytes = mock.Mock(return_value=b"new content")

        mock_conn = mock.MagicMock()
        # Stored hash is different from current hash
        mock_conn.execute.return_value.fetchone.return_value = ("old_hash_value",)

        with mock.patch("hashlib.sha256") as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "new_hash_value"

            with mock.patch.object(Path, "exists", return_value=True):
                with mock.patch("pathlib.Path.rglob") as mock_rglob:
                    mock_rglob.return_value = [mock_file]

                    with mock.patch.object(
                        mock_state_manager, "transaction"
                    ) as mock_transaction:
                        mock_transaction.return_value.__enter__.return_value = mock_conn

                        service = QueryService(mock_state_manager)
                        result = service.has_file_changes()

                        # Modified file (different hash) means changes detected
                        assert result is True

    def test_has_file_changes_no_changes(self, mock_path_factory):
        """Test has_file_changes when files haven't changed."""
        mock_state_manager = mock.MagicMock()
        mock_roadmap_dir = Path("/test/.roadmap")
        mock_state_manager.db_path = mock_roadmap_dir / "db.sqlite"

        mock_file = mock_path_factory(name="issues/test.md", exists=True)
        mock_file.read_bytes = mock.Mock(return_value=b"file content")

        test_hash = "abc123def456"
        mock_conn = mock.MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (test_hash,)

        with mock.patch("hashlib.sha256") as mock_hash:
            mock_hash.return_value.hexdigest.return_value = test_hash

            with mock.patch.object(Path, "exists", return_value=True):
                with mock.patch.object(Path, "rglob") as mock_rglob:
                    mock_rglob.return_value = [mock_file]

                    with mock.patch.object(
                        mock_state_manager, "transaction"
                    ) as mock_transaction:
                        mock_transaction.return_value.__enter__.return_value = mock_conn

                        with mock.patch.object(
                            Path, "parent", new_callable=mock.PropertyMock
                        ):
                            service = QueryService(mock_state_manager)
                            result = service.has_file_changes()

                            # Same hash means no changes
                            assert result is False

    def test_has_file_changes_transaction_error(self, mock_path_factory):
        """Test has_file_changes handles transaction errors."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.db_path = Path("/test/.roadmap/db.sqlite")

        mock_file = mock_path_factory(name="issues/test.md", exists=True)
        mock_file.read_bytes = mock.Mock(return_value=b"content")

        with mock.patch.object(Path, "exists", return_value=True):
            with mock.patch("pathlib.Path.rglob") as mock_rglob:
                mock_rglob.return_value = [mock_file]

                with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
                    mock_tx.side_effect = Exception("Database error")

                    service = QueryService(mock_state_manager)
                    result = service.has_file_changes()

                    # On error, assume changes exist to be safe
                    assert result is True

    def test_has_file_changes_file_disappeared(self, mock_path_factory):
        """Test has_file_changes when file disappears during check."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.db_path = Path("/test/.roadmap/db.sqlite")

        mock_file = mock_path_factory(
            name="issues/test.md",
            exists=False,  # File disappeared
        )

        mock_conn = mock.MagicMock()

        with mock.patch.object(Path, "exists", return_value=True):
            with mock.patch.object(Path, "rglob") as mock_rglob:
                mock_rglob.return_value = [mock_file]

                with mock.patch.object(
                    mock_state_manager, "transaction"
                ) as mock_transaction:
                    mock_transaction.return_value.__enter__.return_value = mock_conn

                    with mock.patch.object(
                        Path, "parent", new_callable=mock.PropertyMock
                    ):
                        service = QueryService(mock_state_manager)
                        result = service.has_file_changes()

                        # File disappeared, continue checking
                        assert result is False


class TestGetMilestoneProgress:
    """Test get_milestone_progress method for milestone completion stats."""

    def test_get_milestone_progress_milestone_not_found(self):
        """Test get_milestone_progress when milestone doesn't exist."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_milestone_progress("NonExistent")

            assert result == {"total": 0, "completed": 0}

    def test_get_milestone_progress_no_issues(self):
        """Test get_milestone_progress when milestone has no issues."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        # First call returns milestone ID, subsequent calls return 0 counts
        mock_conn.execute.return_value.fetchone.side_effect = [("mile-1",), (0,), (0,)]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_milestone_progress("sprint-1")

            assert result == {"total": 0, "completed": 0}

    def test_get_milestone_progress_with_issues(self):
        """Test get_milestone_progress returns correct progress stats."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        # Milestone exists, has 10 total issues, 7 completed
        mock_conn.execute.return_value.fetchone.side_effect = [("mile-1",), (10,), (7,)]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_milestone_progress("Sprint 2")

            assert result == {"total": 10, "completed": 7}

    def test_get_milestone_progress_all_completed(self):
        """Test get_milestone_progress when all issues are completed."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        mock_conn.execute.return_value.fetchone.side_effect = [("mile-1",), (5,), (5,)]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_milestone_progress("Sprint 3")

            assert result["total"] == 5
            assert result["completed"] == 5
            assert result["total"] == result["completed"]

    def test_get_milestone_progress_none_completed(self):
        """Test get_milestone_progress when no issues are completed."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        mock_conn.execute.return_value.fetchone.side_effect = [("mile-1",), (8,), (0,)]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_milestone_progress("Sprint 4")

            assert result["total"] == 8
            assert result["completed"] == 0

    def test_get_milestone_progress_database_error(self):
        """Test get_milestone_progress returns zero stats on error."""
        mock_state_manager = mock.MagicMock()

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.side_effect = Exception("DB error")

            service = QueryService(mock_state_manager)
            result = service.get_milestone_progress("Sprint Error")

            assert result == {"total": 0, "completed": 0}

    def test_get_milestone_progress_null_count_result(self):
        """Test get_milestone_progress handles NULL count results."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        # Milestone exists, but count queries return None
        mock_conn.execute.return_value.fetchone.side_effect = [("mile-1",), None, None]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_milestone_progress("Sprint 5")

            assert result == {"total": 0, "completed": 0}

    def test_get_milestone_progress_large_numbers(self):
        """Test get_milestone_progress with large issue counts."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        mock_conn.execute.return_value.fetchone.side_effect = [
            ("mile-1",),
            (1000,),
            (850,),
        ]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_milestone_progress("BigSprint")

            assert result["total"] == 1000
            assert result["completed"] == 850
