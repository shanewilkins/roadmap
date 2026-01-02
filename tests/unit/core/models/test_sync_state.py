"""Tests for SyncState model."""

from datetime import datetime

from roadmap.core.models import IssueBaseState, SyncState


class TestIssueBaseState:
    """Test IssueBaseState dataclass."""

    def test_create_issue_base_state(self):
        """Test creating an issue base state."""
        state = IssueBaseState(
            id="issue-1",
            status="in-progress",
            assignee="alice",
            milestone="v1.0",
            description="Fix the bug",
            labels=["bug", "urgent"],
        )

        assert state.id == "issue-1"
        assert state.status == "in-progress"
        assert state.assignee == "alice"
        assert state.milestone == "v1.0"
        assert state.description == "Fix the bug"
        assert state.labels == ["bug", "urgent"]

    def test_issue_base_state_optional_fields(self):
        """Test that assignee and milestone are optional."""
        state = IssueBaseState(
            id="issue-2",
            status="todo",
            description="New issue",
        )

        assert state.assignee is None
        assert state.milestone is None

    def test_issue_base_state_to_dict(self):
        """Test serialization to dict."""
        now = datetime(2026, 1, 1, 12, 0, 0)
        state = IssueBaseState(
            id="issue-1",
            status="closed",
            assignee="bob",
            description="Done",
            updated_at=now,
        )

        result = state.to_dict()

        assert result["id"] == "issue-1"
        assert result["status"] == "closed"
        assert result["assignee"] == "bob"
        assert result["updated_at"] == "2026-01-01T12:00:00"

    def test_issue_base_state_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "id": "issue-3",
            "status": "review",
            "assignee": "charlie",
            "milestone": None,
            "description": "Under review",
            "labels": [],
            "updated_at": "2026-01-01T10:00:00",
        }

        state = IssueBaseState.from_dict(data)

        assert state.id == "issue-3"
        assert state.status == "review"
        assert state.assignee == "charlie"
        assert isinstance(state.updated_at, datetime)


class TestSyncState:
    """Test SyncState dataclass."""

    def test_create_sync_state(self):
        """Test creating sync state."""
        now = datetime(2026, 1, 1, 12, 0, 0)
        state = SyncState(last_sync=now, backend="github")

        assert state.last_sync == now
        assert state.backend == "github"
        assert state.issues == {}

    def test_add_issue_to_sync_state(self):
        """Test adding issues to sync state."""
        sync_state = SyncState(last_sync=datetime.now(), backend="github")
        issue_state = IssueBaseState(id="issue-1", status="todo", description="Test")

        sync_state.add_issue("issue-1", issue_state)

        assert "issue-1" in sync_state.issues
        assert sync_state.issues["issue-1"].status == "todo"

    def test_update_issue_in_sync_state(self):
        """Test updating an issue in sync state."""
        sync_state = SyncState(last_sync=datetime.now(), backend="github")
        issue_state = IssueBaseState(id="issue-1", status="todo", description="Test")
        sync_state.add_issue("issue-1", issue_state)

        updated_state = IssueBaseState(
            id="issue-1", status="closed", description="Done"
        )
        sync_state.update_issue("issue-1", updated_state)

        assert sync_state.issues["issue-1"].status == "closed"

    def test_remove_issue_from_sync_state(self):
        """Test removing an issue from sync state."""
        sync_state = SyncState(last_sync=datetime.now(), backend="github")
        issue_state = IssueBaseState(id="issue-1", status="todo", description="Test")
        sync_state.add_issue("issue-1", issue_state)

        sync_state.remove_issue("issue-1")

        assert "issue-1" not in sync_state.issues

    def test_sync_state_to_dict(self):
        """Test serialization to dict."""
        now = datetime(2026, 1, 1, 12, 0, 0)
        sync_state = SyncState(last_sync=now, backend="github")

        issue_state = IssueBaseState(
            id="issue-1",
            status="in-progress",
            assignee="alice",
            description="Working on it",
            updated_at=now,
        )
        sync_state.add_issue("issue-1", issue_state)

        result = sync_state.to_dict()

        assert result["last_sync"] == "2026-01-01T12:00:00"
        assert result["backend"] == "github"
        assert "issue-1" in result["issues"]
        assert result["issues"]["issue-1"]["status"] == "in-progress"

    def test_sync_state_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "last_sync": "2026-01-01T12:00:00",
            "backend": "github",
            "issues": {
                "issue-1": {
                    "id": "issue-1",
                    "status": "closed",
                    "assignee": "bob",
                    "milestone": None,
                    "description": "Fixed",
                    "labels": ["fixed"],
                    "updated_at": "2026-01-01T11:00:00",
                }
            },
        }

        sync_state = SyncState.from_dict(data)

        assert sync_state.backend == "github"
        assert "issue-1" in sync_state.issues
        assert sync_state.issues["issue-1"].status == "closed"
        assert isinstance(sync_state.last_sync, datetime)

    def test_sync_state_roundtrip(self):
        """Test that serialize/deserialize preserves data."""
        now = datetime(2026, 1, 1, 12, 0, 0)
        original = SyncState(last_sync=now, backend="git")

        issue1 = IssueBaseState(
            id="issue-1",
            status="todo",
            assignee=None,
            description="First",
            updated_at=now,
        )
        issue2 = IssueBaseState(
            id="issue-2",
            status="closed",
            assignee="alice",
            milestone="v1.0",
            description="Second",
            labels=["bug"],
            updated_at=now,
        )

        original.add_issue("issue-1", issue1)
        original.add_issue("issue-2", issue2)

        # Serialize and deserialize
        data = original.to_dict()
        restored = SyncState.from_dict(data)

        # Verify
        assert restored.backend == original.backend
        assert len(restored.issues) == 2
        assert restored.issues["issue-1"].status == "todo"
        assert restored.issues["issue-2"].assignee == "alice"
        assert restored.issues["issue-2"].milestone == "v1.0"
