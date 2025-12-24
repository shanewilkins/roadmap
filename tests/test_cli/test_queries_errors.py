"""Error path tests for QueryService (queries.py module).

Tests cover database operation failures, JSON parsing errors, missing data,
transaction failures, and edge cases in query execution.
"""

import json
from pathlib import Path
from unittest import mock

from roadmap.adapters.persistence.storage.queries import QueryService


class TestQueryServiceInitialization:
    """Test QueryService initialization and setup."""

    def test_initialization_with_state_manager(self):
        """Test QueryService initializes with state manager reference."""
        mock_state_manager = mock.MagicMock()
        service = QueryService(mock_state_manager)
        assert service.state_manager == mock_state_manager

    def test_initialization_stores_reference(self):
        """Test initialization stores the provided state manager."""
        mock_state_manager = mock.MagicMock()
        service = QueryService(mock_state_manager)
        assert service.state_manager is mock_state_manager

    def test_initialization_accepts_none_state_manager(self):
        """Test QueryService handles None state manager gracefully."""
        service = QueryService(None)
        assert service.state_manager is None


class TestHasFileChanges:
    """Test has_file_changes method for detecting file modifications."""

    def test_has_file_changes_no_roadmap_dir(self):
        """Test has_file_changes when roadmap directory doesn't exist."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.db_path = Path("/nonexistent/path/db.sqlite")

        service = QueryService(mock_state_manager)
        result = service.has_file_changes()

        # When no directory exists, should return False (no files to check)
        assert result is False

    def test_has_file_changes_no_files(self):
        """Test has_file_changes when no markdown files exist."""
        mock_state_manager = mock.MagicMock()

        with mock.patch.object(Path, "exists", return_value=False):
            with mock.patch.object(
                Path, "parent", new_callable=mock.PropertyMock
            ) as mock_parent:
                mock_parent.return_value = Path("/roadmap")
                mock_state_manager.db_path = Path("/roadmap/.roadmap/db.sqlite")

                service = QueryService(mock_state_manager)
                result = service.has_file_changes()

                # No markdown files means no changes
                assert result is False

    def test_has_file_changes_with_new_file(self):
        """Test has_file_changes detects new markdown files."""
        mock_state_manager = mock.MagicMock()
        mock_roadmap_dir = Path("/test/.roadmap")
        mock_state_manager.db_path = mock_roadmap_dir / "db.sqlite"

        mock_file = mock.MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.read_bytes.return_value = b"file content"
        mock_file.relative_to.return_value = Path("issues/test.md")

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

    def test_has_file_changes_with_modified_file(self):
        """Test has_file_changes detects modified markdown files."""
        mock_state_manager = mock.MagicMock()
        mock_roadmap_dir = Path("/test/.roadmap")
        mock_state_manager.db_path = mock_roadmap_dir / "db.sqlite"

        mock_file = mock.MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.read_bytes.return_value = b"new content"
        mock_file.relative_to.return_value = Path("issues/test.md")

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

    def test_has_file_changes_no_changes(self):
        """Test has_file_changes when files haven't changed."""
        mock_state_manager = mock.MagicMock()
        mock_roadmap_dir = Path("/test/.roadmap")
        mock_state_manager.db_path = mock_roadmap_dir / "db.sqlite"

        mock_file = mock.MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.read_bytes.return_value = b"file content"
        mock_file.relative_to.return_value = Path("issues/test.md")

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

    def test_has_file_changes_transaction_error(self):
        """Test has_file_changes handles transaction errors."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.db_path = Path("/test/.roadmap/db.sqlite")

        mock_file = mock.MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.read_bytes.return_value = b"content"

        with mock.patch.object(Path, "exists", return_value=True):
            with mock.patch("pathlib.Path.rglob") as mock_rglob:
                mock_rglob.return_value = [mock_file]

                with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
                    mock_tx.side_effect = Exception("Database error")

                    service = QueryService(mock_state_manager)
                    result = service.has_file_changes()

                    # On error, assume changes exist to be safe
                    assert result is True

    def test_has_file_changes_file_disappeared(self):
        """Test has_file_changes when file disappears during check."""
        mock_state_manager = mock.MagicMock()
        mock_state_manager.db_path = Path("/test/.roadmap/db.sqlite")

        mock_file = mock.MagicMock(spec=Path)
        mock_file.exists.return_value = False  # File disappeared
        mock_file.relative_to.return_value = Path("issues/test.md")

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


class TestGetAllIssues:
    """Test get_all_issues method for retrieving all issues."""

    def test_get_all_issues_empty_database(self):
        """Test get_all_issues when database has no issues."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_issues()

            assert result == []

    def test_get_all_issues_single_issue(self):
        """Test get_all_issues returns correctly formatted issue."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        issue_row = (
            "issue-1",  # id
            "Test Issue",  # title
            "open",  # status
            "high",  # priority
            "bug",  # type
            "alice",  # assignee
            8.5,  # estimate_hours
            "2024-12-31",  # due_date
            "proj-1",  # project_id
            "mile-1",  # milestone_id
            None,  # metadata
            "Sprint 1",  # milestone_name
            "Project A",  # project_name
        )

        mock_conn.execute.return_value.fetchall.return_value = [issue_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_issues()

            assert len(result) == 1
            assert result[0]["id"] == "issue-1"
            assert result[0]["title"] == "Test Issue"
            assert result[0]["status"] == "open"
            assert result[0]["priority"] == "high"
            assert result[0]["type"] == "bug"
            assert result[0]["assignee"] == "alice"
            assert result[0]["estimate_hours"] == 8.5
            assert result[0]["milestone_name"] == "Sprint 1"

    def test_get_all_issues_with_metadata(self):
        """Test get_all_issues parses and merges metadata."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        metadata_json = json.dumps(
            {"tags": ["urgent", "backend"], "custom_field": "value"}
        )
        issue_row = (
            "issue-2",
            "Complex Issue",
            "in-progress",
            "medium",
            "feature",
            "bob",
            16.0,
            "2024-11-15",
            "proj-2",
            "mile-2",
            metadata_json,  # Valid JSON metadata
            "Sprint 2",
            "Project B",
        )

        mock_conn.execute.return_value.fetchall.return_value = [issue_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_issues()

            assert len(result) == 1
            assert result[0]["tags"] == ["urgent", "backend"]
            assert result[0]["custom_field"] == "value"

    def test_get_all_issues_invalid_metadata(self):
        """Test get_all_issues skips invalid JSON metadata."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        issue_row = (
            "issue-3",
            "Bad Metadata Issue",
            "closed",
            "low",
            "chore",
            "charlie",
            2.0,
            None,
            "proj-3",
            None,
            "{invalid json}",  # Invalid JSON
            None,
            "Project C",
        )

        mock_conn.execute.return_value.fetchall.return_value = [issue_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_issues()

            # Should continue despite invalid JSON
            assert len(result) == 1
            assert result[0]["id"] == "issue-3"
            assert "tags" not in result[0]  # Metadata not added

    def test_get_all_issues_multiple_issues(self):
        """Test get_all_issues with multiple issues."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        issue_rows = [
            (
                "i-1",
                "Issue 1",
                "open",
                "high",
                "bug",
                "user1",
                5,
                "2024-12-01",
                "p1",
                "m1",
                None,
                "Sprint A",
                "Proj A",
            ),
            (
                "i-2",
                "Issue 2",
                "in-progress",
                "med",
                "feature",
                "user2",
                10,
                "2024-11-01",
                "p2",
                "m2",
                None,
                "Sprint B",
                "Proj B",
            ),
            (
                "i-3",
                "Issue 3",
                "closed",
                "low",
                "doc",
                "user3",
                2,
                None,
                "p3",
                None,
                None,
                None,
                "Proj C",
            ),
        ]

        mock_conn.execute.return_value.fetchall.return_value = issue_rows

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_issues()

            assert len(result) == 3
            assert result[0]["title"] == "Issue 1"
            assert result[1]["title"] == "Issue 2"
            assert result[2]["title"] == "Issue 3"

    def test_get_all_issues_database_error(self):
        """Test get_all_issues returns empty list on database error."""
        mock_state_manager = mock.MagicMock()

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.side_effect = Exception(
                "DB connection failed"
            )

            service = QueryService(mock_state_manager)
            result = service.get_all_issues()

            # Should return empty list on error
            assert result == []

    def test_get_all_issues_with_null_values(self):
        """Test get_all_issues handles NULL values in optional fields."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        issue_row = (
            "issue-null",
            "Minimal Issue",
            "open",
            None,  # NULL priority
            "bug",
            None,  # NULL assignee
            None,  # NULL estimate
            None,  # NULL due_date
            None,  # NULL project_id
            None,  # NULL milestone_id
            None,  # NULL metadata
            None,  # NULL milestone_name
            None,  # NULL project_name
        )

        mock_conn.execute.return_value.fetchall.return_value = [issue_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_issues()

            assert len(result) == 1
            assert result[0]["priority"] is None
            assert result[0]["assignee"] is None
            assert result[0]["estimate_hours"] is None


class TestGetAllMilestones:
    """Test get_all_milestones method for retrieving all milestones."""

    def test_get_all_milestones_empty_database(self):
        """Test get_all_milestones when database has no milestones."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_milestones()

            assert result == []

    def test_get_all_milestones_single_milestone(self):
        """Test get_all_milestones returns correctly formatted milestone."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        milestone_row = (
            "mile-1",  # id
            "Sprint 1",  # title
            "Q1 Development",  # description
            "active",  # status
            "2024-12-31",  # due_date
            75,  # progress_percentage
            "proj-1",  # project_id
            None,  # metadata
            "Project A",  # project_name
        )

        mock_conn.execute.return_value.fetchall.return_value = [milestone_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_milestones()

            assert len(result) == 1
            assert result[0]["id"] == "mile-1"
            assert result[0]["name"] == "Sprint 1"
            assert result[0]["title"] == "Sprint 1"
            assert result[0]["status"] == "active"
            assert result[0]["progress_percentage"] == 75

    def test_get_all_milestones_with_metadata(self):
        """Test get_all_milestones parses and merges metadata."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        metadata_json = json.dumps({"theme": "backend", "team": ["alice", "bob"]})
        milestone_row = (
            "mile-2",
            "Sprint 2",
            "Phase 2",
            "planning",
            "2025-01-31",
            0,
            "proj-2",
            metadata_json,
            "Project B",
        )

        mock_conn.execute.return_value.fetchall.return_value = [milestone_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_milestones()

            assert len(result) == 1
            assert result[0]["theme"] == "backend"
            assert result[0]["team"] == ["alice", "bob"]

    def test_get_all_milestones_invalid_metadata(self):
        """Test get_all_milestones skips invalid JSON metadata."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        milestone_row = (
            "mile-3",
            "Sprint 3",
            "Description",
            "completed",
            "2024-09-30",
            100,
            "proj-3",
            "not valid json at all",  # Invalid JSON
            "Project C",
        )

        mock_conn.execute.return_value.fetchall.return_value = [milestone_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_milestones()

            assert len(result) == 1
            assert result[0]["id"] == "mile-3"

    def test_get_all_milestones_multiple_milestones(self):
        """Test get_all_milestones with multiple milestones."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        milestone_rows = [
            (
                "m1",
                "Q1",
                "First quarter",
                "active",
                "2024-03-31",
                50,
                "p1",
                None,
                "ProjectA",
            ),
            (
                "m2",
                "Q2",
                "Second quarter",
                "planning",
                "2024-06-30",
                0,
                "p2",
                None,
                "ProjectB",
            ),
            (
                "m3",
                "Q3",
                "Third quarter",
                "completed",
                "2024-09-30",
                100,
                "p1",
                None,
                "ProjectA",
            ),
        ]

        mock_conn.execute.return_value.fetchall.return_value = milestone_rows

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_milestones()

            assert len(result) == 3
            assert result[0]["title"] == "Q1"
            assert result[1]["title"] == "Q2"
            assert result[2]["title"] == "Q3"

    def test_get_all_milestones_database_error(self):
        """Test get_all_milestones returns empty list on database error."""
        mock_state_manager = mock.MagicMock()

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.side_effect = Exception("Connection lost")

            service = QueryService(mock_state_manager)
            result = service.get_all_milestones()

            assert result == []

    def test_get_all_milestones_with_null_values(self):
        """Test get_all_milestones handles NULL values."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        milestone_row = (
            "m-null",
            "Unnamed",
            None,  # NULL description
            "active",
            None,  # NULL due_date
            None,  # NULL progress
            None,  # NULL project_id
            None,  # NULL metadata
            None,  # NULL project_name
        )

        mock_conn.execute.return_value.fetchall.return_value = [milestone_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_milestones()

            assert len(result) == 1
            assert result[0]["description"] is None
            assert result[0]["due_date"] is None
            assert result[0]["progress_percentage"] is None


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
            result = service.get_milestone_progress("Sprint 1")

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


class TestGetIssuesByStatus:
    """Test get_issues_by_status method for status distribution."""

    def test_get_issues_by_status_empty_database(self):
        """Test get_issues_by_status with no issues."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result == {}

    def test_get_issues_by_status_single_status(self):
        """Test get_issues_by_status with single status."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("open", 5)]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result == {"open": 5}

    def test_get_issues_by_status_multiple_statuses(self):
        """Test get_issues_by_status with multiple statuses."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        status_rows = [
            ("backlog", 12),
            ("closed", 45),
            ("in-progress", 8),
            ("open", 23),
        ]

        mock_conn.execute.return_value.fetchall.return_value = status_rows

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result == {
                "backlog": 12,
                "closed": 45,
                "in-progress": 8,
                "open": 23,
            }
            assert sum(result.values()) == 88

    def test_get_issues_by_status_database_error(self):
        """Test get_issues_by_status returns empty dict on error."""
        mock_state_manager = mock.MagicMock()

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.side_effect = Exception("Query failed")

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result == {}

    def test_get_issues_by_status_zero_counts(self):
        """Test get_issues_by_status includes statuses with zero issues."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        status_rows = [
            ("backlog", 0),
            ("closed", 10),
            ("in-progress", 0),
            ("open", 5),
        ]

        mock_conn.execute.return_value.fetchall.return_value = status_rows

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result["backlog"] == 0
            assert result["in-progress"] == 0


class TestQueryServiceIntegration:
    """Integration tests for QueryService operations."""

    def test_multiple_queries_same_transaction(self):
        """Test multiple query methods can share transaction context."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        # Setup different return values for different queries
        mock_conn.execute.return_value.fetchall.side_effect = [
            [],  # get_all_issues returns empty
            [],  # get_all_milestones returns empty
        ]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            issues = service.get_all_issues()
            milestones = service.get_all_milestones()

            assert issues == []
            assert milestones == []

    def test_query_service_with_metadata_consistency(self):
        """Test QueryService maintains consistency when parsing metadata."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        # Create test data with metadata
        test_metadata = {"priority": "urgent", "custom": 123}
        metadata_json = json.dumps(test_metadata)

        issue_row = (
            "i-1",
            "Title",
            "open",
            "high",
            "bug",
            "user",
            5,
            "2024-12-01",
            "p1",
            "m1",
            metadata_json,
            "Milestone",
            "Project",
        )

        mock_conn.execute.return_value.fetchall.return_value = [issue_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_issues()

            # Metadata should be merged into result
            assert result[0]["priority"] == "urgent"
            assert result[0]["custom"] == 123
