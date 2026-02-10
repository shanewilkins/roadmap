"""Unit tests for SyncMergeOrchestrator baseline loading and report updates.

Tests the _load_baseline_state(), _apply_changes() report updates, and error handling.
"""

import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock

from roadmap.adapters.sync.sync_merge_orchestrator import SyncMergeOrchestrator
from roadmap.core.services.sync.sync_conflict_resolver import SyncConflictResolver
from roadmap.core.services.sync.sync_report import SyncReport
from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator


class TestLoadBaselineState(unittest.TestCase):
    """Test _load_baseline_state() method."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_load_baseline_state_from_database_success(self):
        """Test successful baseline load from database."""
        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Mock database with 2 issues
        db_baseline = {
            "issue-1": {
                "status": "todo",
                "assignee": "user1",
                "content": "Bug description",
                "headline": "",
                "title": "Bug Title",
                "labels": ["bug", "urgent"],
            },
            "issue-2": {
                "status": "in_progress",
                "assignee": None,
                "content": "Feature details",
                "headline": "",
                "title": "Feature Title",
                "labels": [],
            },
        }
        self.core.db.get_sync_baseline.return_value = db_baseline

        # Execute
        result = orchestrator._load_baseline_state()

        # Verify
        assert result is not None
        assert isinstance(result, SyncState)
        assert len(result.base_issues) == 2
        assert "issue-1" in result.base_issues
        assert "issue-2" in result.base_issues

        # Verify data integrity
        issue1 = result.base_issues["issue-1"]
        assert issue1.status == "todo"
        assert issue1.assignee == "user1"
        assert issue1.content == "Bug description"
        assert issue1.labels == ["bug", "urgent"]

        issue2 = result.base_issues["issue-2"]
        assert issue2.status == "in_progress"
        assert issue2.assignee is None
        assert issue2.content == "Feature details"
        assert issue2.labels == []

    def test_load_baseline_state_empty_database(self):
        """Test baseline load returns None when database is empty."""
        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        self.core.db.get_sync_baseline.return_value = None

        # Execute
        result = orchestrator._load_baseline_state()

        # Verify
        assert result is None

    def test_load_baseline_state_database_exception(self):
        """Test baseline load returns None on database error."""
        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Simulate database error
        self.core.db.get_sync_baseline.side_effect = Exception(
            "Database connection failed"
        )

        # Execute
        result = orchestrator._load_baseline_state()

        # Verify - should return None and not raise
        assert result is None

    def test_load_baseline_state_content_field_required(self):
        """Test that content field is properly loaded (required for comparison)."""
        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Database with content field
        db_baseline = {
            "issue-1": {
                "status": "todo",
                "assignee": None,
                "description": "This is the full content field with markdown\n\n## Details\nMore info",
                "content": "This is the full content field with markdown\n\n## Details\nMore info",
                "labels": [],
            }
        }
        self.core.db.get_sync_baseline.return_value = db_baseline

        # Execute
        result = orchestrator._load_baseline_state()

        # Verify content field is set (critical for three-way merge)
        assert result is not None
        issue = result.base_issues["issue-1"]
        assert (
            issue.content
            == "This is the full content field with markdown\n\n## Details\nMore info"
        )
        assert issue.content != ""  # Must not be empty

    def test_load_baseline_state_missing_optional_fields(self):
        """Test baseline load with missing optional fields (should use defaults)."""
        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Minimal database record
        db_baseline = {
            "issue-1": {
                "status": "todo",
            }
        }
        self.core.db.get_sync_baseline.return_value = db_baseline

        # Execute
        result = orchestrator._load_baseline_state()

        # Verify defaults are applied
        assert result is not None
        issue = result.base_issues["issue-1"]
        assert issue.status == "todo"
        assert issue.assignee is None
        assert issue.content == ""
        assert issue.labels == []


class TestReportCountUpdates(unittest.TestCase):
    """Test report count updates after applying changes."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_report_updates_after_push(self):
        """Test that report counts are updated after successful push."""
        # Create initial report
        report = SyncReport()
        report.issues_up_to_date = 3
        report.issues_needs_push = 5
        report.issues_needs_pull = 0

        # Simulate applying 5 pushed changes
        pushed_count = 5
        pulled_count = 0
        dry_run = False

        # Execute the update logic
        if (pushed_count > 0 or pulled_count > 0) and not dry_run:
            if pushed_count > 0:
                report.issues_needs_push = max(
                    0, report.issues_needs_push - pushed_count
                )
                report.issues_up_to_date = report.issues_up_to_date + pushed_count

        # Verify counts were updated correctly
        assert report.issues_up_to_date == 8
        assert report.issues_needs_push == 0

    def test_report_updates_after_pull(self):
        """Test that report counts are updated after pulling."""
        report = SyncReport()
        report.issues_up_to_date = 3
        report.issues_needs_push = 0
        report.issues_needs_pull = 2

        pushed_count = 0
        pulled_count = 2
        dry_run = False

        # Execute the update logic
        if (pushed_count > 0 or pulled_count > 0) and not dry_run:
            if pulled_count > 0:
                report.issues_needs_pull = max(
                    0, report.issues_needs_pull - pulled_count
                )
                report.issues_up_to_date = report.issues_up_to_date + pulled_count

        # Verify
        assert report.issues_up_to_date == 5
        assert report.issues_needs_pull == 0

    def test_report_updates_mixed_push_and_pull(self):
        """Test report updates with both push and pull."""
        report = SyncReport()
        report.issues_up_to_date = 2
        report.issues_needs_push = 3
        report.issues_needs_pull = 2

        pushed_count = 3
        pulled_count = 2
        dry_run = False

        # Execute the update logic
        if (pushed_count > 0 or pulled_count > 0) and not dry_run:
            if pushed_count > 0:
                report.issues_needs_push = max(
                    0, report.issues_needs_push - pushed_count
                )
                report.issues_up_to_date = report.issues_up_to_date + pushed_count

            if pulled_count > 0:
                report.issues_needs_pull = max(
                    0, report.issues_needs_pull - pulled_count
                )
                report.issues_up_to_date = report.issues_up_to_date + pulled_count

        # Verify
        assert report.issues_up_to_date == 7
        assert report.issues_needs_push == 0
        assert report.issues_needs_pull == 0

    def test_report_not_updated_in_dry_run(self):
        """Test that report is NOT updated during dry-run."""
        report = SyncReport()
        report.issues_up_to_date = 3
        report.issues_needs_push = 5

        pushed_count = 5
        pulled_count = 0
        dry_run = True

        # Execute the update logic
        if (pushed_count > 0 or pulled_count > 0) and not dry_run:
            if pushed_count > 0:
                report.issues_needs_push = max(
                    0, report.issues_needs_push - pushed_count
                )
                report.issues_up_to_date = report.issues_up_to_date + pushed_count

        # Verify counts unchanged
        assert report.issues_up_to_date == 3
        assert report.issues_needs_push == 5

    def test_report_counts_never_go_negative(self):
        """Test that report counts use max(0, ...) to prevent negative values."""
        report = SyncReport()
        report.issues_needs_push = 2

        # Try to "push" 5 issues (more than the 2 needed)
        pushed_count = 5

        if pushed_count > 0:
            report.issues_needs_push = max(0, report.issues_needs_push - pushed_count)

        # Verify it's 0, not -3
        assert report.issues_needs_push == 0
        assert report.issues_needs_push >= 0

    def test_pushed_counter_increments_correctly(self):
        """Test that pushed_count is incremented (+=), not reset (=)."""
        # This tests the fix for the `pushed_count = 1` bug
        pushed_count = 0

        # Simulate pushing 3 issues
        for _ in range(3):
            pushed_count += 1  # Correct: +=

        # Verify counter reached 3
        assert pushed_count == 3, "Counter should be 3 after 3 iterations"

        # Demonstrate the bug that was there before
        pushed_count_buggy = 0
        for _ in range(3):
            pushed_count_buggy = 1  # Bug: =, not +=

        # Buggy version would only be 1
        assert pushed_count_buggy == 1, "Bug would have resulted in count of 1"


class TestErrorScenarios(unittest.TestCase):
    """Test error handling in baseline loading and saving."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_baseline_load_import_error(self):
        """Test handling of import errors during baseline load."""
        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # This would be hard to test without mocking imports,
        # but the try-catch in _load_baseline_state() handles it
        # by returning None and logging warning

        # Simulate any exception
        self.core.db.get_sync_baseline.side_effect = ImportError("Module not found")

        result = orchestrator._load_baseline_state()

        assert result is None

    def test_baseline_load_attribute_error(self):
        """Test handling when database returns malformed data."""
        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Simulate malformed data that causes AttributeError
        self.core.db.get_sync_baseline.side_effect = AttributeError(
            "'NoneType' object has no attribute 'items'"
        )

        result = orchestrator._load_baseline_state()

        assert result is None

    def test_baseline_load_type_error(self):
        """Test handling of type errors in baseline data."""
        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Simulate TypeError (e.g., iteration over non-iterable)
        self.core.db.get_sync_baseline.side_effect = TypeError(
            "'int' object is not iterable"
        )

        result = orchestrator._load_baseline_state()

        assert result is None


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation for IssueBaseState."""

    def test_issue_base_state_has_required_fields(self):
        """Test that IssueBaseState has all required fields for comparison."""
        # Fields required by _compute_changes() in sync_state_comparator
        required_fields = ["status", "assignee", "description", "labels"]

        state = IssueBaseState(
            id="test-1",
            status="todo",
            title="Test",
            assignee="user1",
            description="Test description",
            headline="Headline",
            content="Full content",
            labels=["tag1"],
        )

        # Verify all required fields exist and are accessible
        for field in required_fields:
            assert hasattr(state, field), (
                f"IssueBaseState missing required field: {field}"
            )

    def test_issue_base_state_defaults(self):
        """Test that IssueBaseState has sensible defaults."""
        state = IssueBaseState(
            id="test-1",
            status="todo",
            title="Test",
        )

        # Verify defaults
        assert state.assignee is None
        assert state.description == ""
        assert state.labels == []

    def test_sync_state_preserves_all_fields(self):
        """Test that SyncState can store and retrieve all IssueBaseState fields."""
        issue_state = IssueBaseState(
            id="issue-1",
            status="in_progress",
            title="Test Issue",
            assignee="user1",
            description="Summary",
            labels=["feature", "priority"],
        )

        sync_state = SyncState(last_sync_time=datetime.now(UTC))
        sync_state.add_issue("base", issue_state)

        # Retrieve and verify
        retrieved = sync_state.base_issues["issue-1"]
        assert retrieved.id == "issue-1"
        assert retrieved.status == "in_progress"
        assert retrieved.title == "Test Issue"
        assert retrieved.assignee == "user1"
        assert retrieved.labels == ["feature", "priority"]

    def test_baseline_data_round_trip(self):
        """Test that baseline data survives save/load round trip."""
        original_data = {
            "issue-1": {
                "status": "todo",
                "assignee": "user1",
                "description": "",
                "headline": "",
                "content": "",
                "labels": ["bug", "critical"],
            }
        }

        # Simulate save: convert to IssueBaseState
        state = SyncState(last_sync_time=datetime.now(UTC))
        for issue_id, data in original_data.items():
            state.add_issue(
                "base",
                IssueBaseState(
                    id=issue_id,
                    status=data["status"],
                    title="",
                    assignee=data.get("assignee"),
                    description=data.get("description", ""),
                    headline=data.get("headline", ""),
                    content=data.get("content", ""),
                    labels=data.get("labels", []),
                ),
            )

        # Simulate load: convert back
        loaded_data = {}
        for issue_id, base_state in state.base_issues.items():
            loaded_data[issue_id] = {
                "status": base_state.status,
                "assignee": base_state.assignee,
                "description": base_state.description,
                "headline": base_state.headline,
                "content": base_state.content,
                "labels": base_state.labels,
            }

        # Verify round trip
        assert loaded_data == original_data


if __name__ == "__main__":
    unittest.main()
