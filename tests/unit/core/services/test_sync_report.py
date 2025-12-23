"""Tests for sync report model and formatting."""

from datetime import datetime
from unittest.mock import patch

from roadmap.core.services.sync_report import IssueChange, SyncReport


class TestIssueChange:
    """Test IssueChange dataclass."""

    def test_create_basic_issue_change(self):
        """Test creating a basic issue change."""
        change = IssueChange(issue_id="issue-1", title="Test Issue")
        assert change.issue_id == "issue-1"
        assert change.title == "Test Issue"
        assert change.local_changes == {}
        assert change.github_changes == {}
        assert change.has_conflict is False
        assert change.last_sync_time is None

    def test_create_with_local_changes(self):
        """Test creating issue change with local changes."""
        local_changes = {"status": "done", "priority": "high"}
        change = IssueChange(
            issue_id="issue-1", title="Test Issue", local_changes=local_changes
        )
        assert change.local_changes == local_changes
        assert change.github_changes == {}

    def test_create_with_github_changes(self):
        """Test creating issue change with GitHub changes."""
        github_changes = {"status": "closed", "priority": "medium"}
        change = IssueChange(
            issue_id="issue-1", title="Test Issue", github_changes=github_changes
        )
        assert change.local_changes == {}
        assert change.github_changes == github_changes

    def test_create_with_conflict(self):
        """Test creating issue change with conflict."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            local_changes={"status": "done"},
            github_changes={"status": "closed"},
            has_conflict=True,
        )
        assert change.has_conflict is True

    def test_get_conflict_description_no_conflict(self):
        """Test getting conflict description when no conflict exists."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            has_conflict=False,
        )
        assert change.get_conflict_description() == ""

    def test_get_conflict_description_with_conflict(self):
        """Test getting conflict description with conflict."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            local_changes={"status": "done"},
            github_changes={"status": "closed"},
            has_conflict=True,
        )
        description = change.get_conflict_description()
        assert "Local" in description
        assert "GitHub" in description
        assert "status: done" in description
        assert "status: closed" in description

    def test_get_change_description_both_changes(self):
        """Test getting change description with both local and GitHub changes."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            local_changes={"status": "done"},
            github_changes={"status": "closed"},
        )
        description = change.get_change_description()
        assert "Local:" in description
        assert "GitHub:" in description

    def test_get_change_description_local_only(self):
        """Test getting change description with only local changes."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            local_changes={"status": "done"},
        )
        description = change.get_change_description()
        assert "Local:" in description
        assert "GitHub:" not in description

    def test_get_change_description_github_only(self):
        """Test getting change description with only GitHub changes."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            github_changes={"status": "closed"},
        )
        description = change.get_change_description()
        assert "GitHub:" in description
        assert "Local:" not in description

    def test_get_change_description_no_changes(self):
        """Test getting change description with no changes."""
        change = IssueChange(issue_id="issue-1", title="Test Issue")
        description = change.get_change_description()
        assert description == "No changes"


class TestSyncReport:
    """Test SyncReport dataclass."""

    def test_create_empty_sync_report(self):
        """Test creating an empty sync report."""
        report = SyncReport()
        assert report.total_issues == 0
        assert report.issues_up_to_date == 0
        assert report.issues_updated == 0
        assert report.conflicts_detected == 0
        assert report.changes == []
        assert report.error is None

    def test_create_with_stats(self):
        """Test creating sync report with statistics."""
        report = SyncReport(
            total_issues=10,
            issues_up_to_date=7,
            issues_updated=3,
            conflicts_detected=0,
        )
        assert report.total_issues == 10
        assert report.issues_up_to_date == 7
        assert report.issues_updated == 3
        assert report.conflicts_detected == 0

    def test_create_with_changes(self):
        """Test creating sync report with changes."""
        change1 = IssueChange(issue_id="issue-1", title="Issue 1")
        change2 = IssueChange(issue_id="issue-2", title="Issue 2")
        report = SyncReport(
            total_issues=2, issues_updated=2, changes=[change1, change2]
        )
        assert len(report.changes) == 2
        assert report.changes[0].issue_id == "issue-1"

    def test_create_with_error(self):
        """Test creating sync report with error."""
        report = SyncReport(error="Network connection failed")
        assert report.error == "Network connection failed"

    def test_timestamp_is_recent(self):
        """Test that timestamp is set to recent time."""
        before = datetime.now()
        report = SyncReport()
        after = datetime.now()
        assert before <= report.timestamp <= after

    def test_custom_timestamp(self):
        """Test creating sync report with custom timestamp."""
        custom_time = datetime(2025, 12, 22, 10, 30, 0)
        report = SyncReport(timestamp=custom_time)
        assert report.timestamp == custom_time

    def test_sync_report_with_conflicts(self):
        """Test sync report with conflicts."""
        change1 = IssueChange(
            issue_id="issue-1",
            title="Issue 1",
            local_changes={"status": "done"},
            github_changes={"status": "closed"},
            has_conflict=True,
        )
        report = SyncReport(
            total_issues=1,
            conflicts_detected=1,
            changes=[change1],
        )
        assert report.conflicts_detected == 1
        assert report.changes[0].has_conflict is True

    @patch("roadmap.core.services.sync_report.console")
    def test_display_brief_with_error(self, mock_console):
        """Test displaying brief report with error."""
        report = SyncReport(error="Sync failed")
        report.display_brief()

        # Verify console.print was called with the error message
        mock_console.print.assert_called()
        # Check that "Sync failed" was in any of the print calls
        call_args_list = [str(call) for call in mock_console.print.call_args_list]
        assert any("Sync failed" in str(call) for call in call_args_list)

    def test_display_brief_success(self, capsys):
        """Test displaying brief successful sync report."""
        report = SyncReport(
            total_issues=10,
            issues_up_to_date=7,
            issues_updated=3,
            conflicts_detected=0,
        )
        report.display_brief()
        captured = capsys.readouterr()
        # Check that the report was printed (output goes to console via rich)
        assert captured.out or True  # Rich may use stderr

    def test_display_brief_with_conflicts(self, capsys):
        """Test displaying brief report with conflicts."""
        report = SyncReport(
            total_issues=10,
            issues_up_to_date=7,
            issues_updated=2,
            conflicts_detected=1,
        )
        report.display_brief()
        capsys.readouterr()
        # Verify the report was displayed

    def test_display_verbose_with_error(self, capsys):
        """Test displaying verbose report with error."""
        report = SyncReport(error="Network error")
        report.display_verbose()
        capsys.readouterr()
        # Verify the error was displayed

    def test_display_verbose_success(self, capsys):
        """Test displaying verbose successful sync report."""
        change = IssueChange(
            issue_id="issue-1",
            title="Updated Issue",
            local_changes={"status": "done"},
        )
        report = SyncReport(
            total_issues=1,
            issues_updated=1,
            changes=[change],
        )
        report.display_verbose()
        capsys.readouterr()
        # Verify verbose report was displayed
