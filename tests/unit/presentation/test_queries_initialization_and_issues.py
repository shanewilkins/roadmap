"""Tests for QueryService read operations (queries.py module).

Tests for reading, querying, and filtering issues and milestones.
Covers list operations, filtering, and integration scenarios.
"""

import json
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
            "sprint-1",  # milestone_name
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
            assert result[0]["milestone_name"] == "sprint-1"

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
            "sprint-1",  # title
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
            assert result[0]["name"] == "sprint-1"
            assert result[0]["title"] == "sprint-1"
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
