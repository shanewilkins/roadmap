"""Unit tests for SyncBackendInterface definition and contract.

These tests validate that the interface is properly defined and can be
used as a protocol for implementing backends.
"""

from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import (
    SyncBackendInterface,
    SyncConflict,
    SyncReport,
)


class TestSyncBackendInterface:
    """Test SyncBackendInterface protocol definition."""

    def test_interface_has_required_methods(self):
        """Test that interface defines all required methods."""
        required_methods = [
            "authenticate",
            "get_issues",
            "push_issue",
            "push_issues",
            "pull_issues",
            "get_conflict_resolution_options",
            "resolve_conflict",
        ]

        for method in required_methods:
            assert hasattr(
                SyncBackendInterface, method
            ), f"SyncBackendInterface missing required method: {method}"

    def test_sync_conflict_creation(self):
        """Test SyncConflict can be created with proper fields."""
        issue = Issue(title="Test Issue")

        conflict = SyncConflict(
            issue_id="test123",
            local_version=issue,
            remote_version={"id": "test123", "title": "Remote Issue"},
            conflict_type="both_modified",
        )

        assert conflict.issue_id == "test123"
        assert conflict.local_version == issue
        assert conflict.remote_version is not None
        assert conflict.remote_version["title"] == "Remote Issue"
        assert conflict.conflict_type == "both_modified"

    def test_sync_conflict_with_none_versions(self):
        """Test SyncConflict handles None versions (deleted remotely/locally)."""
        conflict = SyncConflict(
            issue_id="test123",
            local_version=None,
            remote_version=None,
            conflict_type="deleted_remotely",
        )

        assert conflict.local_version is None
        assert conflict.remote_version is None

    def test_sync_report_creation(self):
        """Test SyncReport can be created and populated."""
        report = SyncReport()

        assert report.pushed == []
        assert report.pulled == []
        assert report.conflicts == []
        assert report.errors == {}

    def test_sync_report_populating(self):
        """Test SyncReport can be populated with results."""
        report = SyncReport()

        # Add pushed issues
        report.pushed.append("issue123")
        report.pushed.append("issue456")

        # Add pulled issues
        report.pulled.append("issue789")

        # Add conflict
        conflict = SyncConflict(
            issue_id="conflict123",
            local_version=Issue(title="Local"),
            remote_version={"title": "Remote"},
            conflict_type="both_modified",
        )
        report.conflicts.append(conflict)

        # Add error
        report.errors["error123"] = "Authentication failed"

        assert len(report.pushed) == 2
        assert len(report.pulled) == 1
        assert len(report.conflicts) == 1
        assert len(report.errors) == 1


class MockSyncBackend:
    """Mock implementation of SyncBackendInterface for testing."""

    def authenticate(self) -> bool:
        """Mock authenticate."""
        return True

    def get_issues(self) -> dict:
        """Mock get_issues."""
        return {}

    def push_issue(self, local_issue: Issue) -> bool:
        """Mock push_issue."""
        return True

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """Mock push_issues."""
        report = SyncReport()
        report.pushed = [issue.id for issue in local_issues]
        return report

    def pull_issues(self) -> SyncReport:
        """Mock pull_issues."""
        return SyncReport()

    def get_conflict_resolution_options(self, conflict: SyncConflict) -> list[str]:
        """Mock get_conflict_resolution_options."""
        return ["use_local", "use_remote"]

    def resolve_conflict(self, conflict: SyncConflict, resolution: str) -> bool:
        """Mock resolve_conflict."""
        return True


class TestSyncBackendImplementation:
    """Test that mock backend properly implements the interface."""

    def test_mock_backend_implements_interface(self):
        """Test that MockSyncBackend implements all interface methods."""
        backend = MockSyncBackend()

        # Should be usable as SyncBackendInterface
        assert hasattr(backend, "authenticate")
        assert hasattr(backend, "get_issues")
        assert hasattr(backend, "push_issue")
        assert hasattr(backend, "push_issues")
        assert hasattr(backend, "pull_issues")
        assert hasattr(backend, "get_conflict_resolution_options")
        assert hasattr(backend, "resolve_conflict")

    def test_mock_backend_methods_callable(self):
        """Test that mock backend methods are callable."""
        backend = MockSyncBackend()

        assert callable(backend.authenticate)
        assert callable(backend.get_issues)
        assert callable(backend.push_issue)
        assert callable(backend.push_issues)
        assert callable(backend.pull_issues)
        assert callable(backend.get_conflict_resolution_options)
        assert callable(backend.resolve_conflict)

    def test_mock_backend_authentication(self):
        """Test mock backend can authenticate."""
        backend = MockSyncBackend()
        assert backend.authenticate() is True

    def test_mock_backend_get_issues(self):
        """Test mock backend can get issues."""
        backend = MockSyncBackend()
        issues = backend.get_issues()
        assert isinstance(issues, dict)

    def test_mock_backend_push_issue(self):
        """Test mock backend can push single issue."""
        backend = MockSyncBackend()
        issue = Issue(title="Test")
        assert backend.push_issue(issue) is True

    def test_mock_backend_push_issues(self):
        """Test mock backend can push multiple issues."""
        backend = MockSyncBackend()
        issues = [Issue(title="Issue 1"), Issue(title="Issue 2")]
        report = backend.push_issues(issues)

        assert isinstance(report, SyncReport)
        assert len(report.pushed) == 2

    def test_mock_backend_pull_issues(self):
        """Test mock backend can pull issues."""
        backend = MockSyncBackend()
        report = backend.pull_issues()
        assert isinstance(report, SyncReport)

    def test_mock_backend_conflict_resolution(self):
        """Test mock backend can resolve conflicts."""
        backend = MockSyncBackend()
        conflict = SyncConflict(
            issue_id="test",
            local_version=Issue(title="Local"),
            remote_version={"title": "Remote"},
            conflict_type="both_modified",
        )

        options = backend.get_conflict_resolution_options(conflict)
        assert isinstance(options, list)
        assert "use_local" in options
        assert "use_remote" in options

        resolved = backend.resolve_conflict(conflict, "use_local")
        assert resolved is True
