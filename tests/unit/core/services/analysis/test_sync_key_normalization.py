"""Tests for SyncStateComparator key normalization logic (Sprint 2.3).

Tests verify that the comparator correctly maps remote issue IDs to local UUIDs
using the Issue.remote_ids field, enabling proper matching between local and
remote issues even when they use different ID formats.
"""

from datetime import UTC, datetime
from typing import Any

from roadmap.common.constants import Status
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator
from tests.factories import IssueBuilder


class MockBackend:
    """Mock sync backend for testing."""

    def __init__(self, backend_name: str = "github"):
        """Initialize mock backend with a given name."""
        self.name = backend_name

    def get_backend_name(self) -> str:
        """Return the backend name."""
        return self.name


def dict_to_sync_issue(remote_id: int | str, issue_dict: dict[str, Any]) -> SyncIssue:
    """Convert a test dict to SyncIssue for testing.

    Args:
        remote_id: The remote backend ID
        issue_dict: Dict with issue data

    Returns:
        SyncIssue instance
    """
    return SyncIssue(
        id=str(issue_dict.get("id", remote_id)),
        title=issue_dict.get("title", ""),
        status=issue_dict.get("status", "open"),
        headline=issue_dict.get("description", ""),
        assignee=issue_dict.get("assignee"),
        labels=issue_dict.get("labels", []),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        backend_name="github",
        backend_id=remote_id,
        remote_ids={"github": remote_id},
    )


class TestSyncKeyNormalization:
    """Test suite for key normalization in SyncStateComparator."""

    def test_normalize_remote_keys_matches_by_remote_id(self):
        """Test that remote issues are matched to local issues by remote_ids mapping."""
        backend = MockBackend("github")
        comparator = SyncStateComparator(backend=backend)

        # Create local issue with UUID and remote ID mapping
        local_issue = (
            IssueBuilder()
            .with_id("7e99d67b")  # Local UUID
            .with_title("Test Issue")
            .with_remote_ids({"github": 42})  # Maps to GitHub issue #42
            .build()
        )

        # Create remote issue with backend ID
        remote_issue = dict_to_sync_issue(
            42,
            {
                "id": 42,
                "title": "Test Issue",
                "status": "todo",
            },
        )

        # Normalize keys
        local_dict = {"7e99d67b": local_issue}
        remote_dict: dict[str, SyncIssue] = {"42": remote_issue}

        normalized_local, normalized_remote = comparator._normalize_remote_keys(
            local_dict, remote_dict
        )

        # Remote issue should now be keyed by local UUID
        assert "7e99d67b" in normalized_remote
        assert "42" not in normalized_remote
        assert normalized_remote["7e99d67b"].id == remote_issue.id

    def test_normalize_remote_keys_unmatched_issues_get_prefix(self):
        """Test that unmatched remote issues get _remote_ prefix for new issue detection."""
        backend = MockBackend("github")
        comparator = SyncStateComparator(backend=backend)

        local_issue = (
            IssueBuilder()
            .with_id("7e99d67b")
            .with_title("Existing Issue")
            .with_remote_ids({"github": 42})
            .build()
        )

        # Remote issue that exists remotely but not linked locally
        matched_remote = dict_to_sync_issue(
            42,
            {
                "id": 42,
                "title": "Existing Issue",
                "status": "todo",
            },
        )
        unmatched_remote = dict_to_sync_issue(
            99,
            {
                "id": 99,
                "title": "New Remote Issue",
                "status": "todo",
            },
        )

        local_dict = {"7e99d67b": local_issue}
        remote_dict: dict[str, SyncIssue] = {
            "42": matched_remote,
            "99": unmatched_remote,
        }

        normalized_local, normalized_remote = comparator._normalize_remote_keys(
            local_dict, remote_dict
        )

        # Matched issue should use local UUID
        assert "7e99d67b" in normalized_remote
        assert normalized_remote["7e99d67b"].id == "42"

        # Unmatched issue should get _remote_ prefix
        assert "_remote_99" in normalized_remote
        assert normalized_remote["_remote_99"].id == "99"

    def test_normalize_remote_keys_multiple_backends(self):
        """Test normalization with multiple backend IDs in remote_ids."""
        github_backend = MockBackend("github")
        comparator = SyncStateComparator(backend=github_backend)

        # Local issue linked to both GitHub and GitLab
        local_issue = (
            IssueBuilder()
            .with_id("7e99d67b")
            .with_title("Multi-Backend Issue")
            .with_remote_ids({"github": 42, "gitlab": 99})
            .build()
        )

        # Only GitHub remote is synced
        remote_issue = dict_to_sync_issue(
            42, {"id": 42, "title": "Multi-Backend Issue"}
        )

        local_dict = {"7e99d67b": local_issue}
        remote_dict: dict[str, SyncIssue] = {"42": remote_issue}

        normalized_local, normalized_remote = comparator._normalize_remote_keys(
            local_dict, remote_dict
        )

        # Should match by GitHub ID
        assert "7e99d67b" in normalized_remote
        assert normalized_remote["7e99d67b"].id == remote_issue.id

    def test_normalize_remote_keys_no_remote_ids(self):
        """Test normalization when local issue has no remote_ids mapping."""
        backend = MockBackend("github")
        comparator = SyncStateComparator(backend=backend)

        # Local issue with no remote IDs (new, unlinked issue)
        local_issue = (
            IssueBuilder()
            .with_id("7e99d67b")
            .with_title("Unlinked Issue")
            .with_remote_ids({})  # No remote mappings
            .build()
        )

        # Remote issue
        remote_issue = dict_to_sync_issue(42, {"id": 42, "title": "Remote Issue"})

        local_dict = {"7e99d67b": local_issue}
        remote_dict: dict[str, SyncIssue] = {"42": remote_issue}

        normalized_local, normalized_remote = comparator._normalize_remote_keys(
            local_dict, remote_dict
        )

        # Local issue unchanged
        assert "7e99d67b" in normalized_local

        # Remote issue gets _remote_ prefix since no local issue matches it
        assert "_remote_42" in normalized_remote
        assert normalized_remote["_remote_42"].id == remote_issue.id

    def test_normalize_remote_keys_preserves_local_dict(self):
        """Test that normalization doesn't modify the original local dict."""
        backend = MockBackend("github")
        comparator = SyncStateComparator(backend=backend)

        local_issue = (
            IssueBuilder()
            .with_id("7e99d67b")
            .with_title("Test Issue")
            .with_remote_ids({"github": 42})
            .build()
        )

        local_dict = {"7e99d67b": local_issue}
        remote_dict: dict[str, SyncIssue] = {
            "42": dict_to_sync_issue(42, {"id": 42, "title": "Test Issue"})
        }

        # Keep original for comparison
        original_local_keys = set(local_dict.keys())

        normalized_local, normalized_remote = comparator._normalize_remote_keys(
            local_dict, remote_dict
        )

        # Original dict unchanged
        assert set(local_dict.keys()) == original_local_keys
        assert list(local_dict.keys()) == ["7e99d67b"]

    def test_analyze_three_way_with_normalized_keys(self):
        """Integration test: analyze_three_way uses normalized keys for matching."""
        backend = MockBackend("github")
        comparator = SyncStateComparator(backend=backend)

        # Local issue
        local_issue = (
            IssueBuilder()
            .with_id("7e99d67b")
            .with_title("Test Issue")
            .with_status(Status.IN_PROGRESS)
            .with_remote_ids({"github": 42})
            .build()
        )

        # Remote issue with same GitHub ID
        remote_issue = dict_to_sync_issue(
            42,
            {
                "id": 42,
                "title": "Test Issue",
                "status": "in_progress",
            },
        )

        # Baseline state
        from roadmap.core.services.sync.sync_state import IssueBaseState

        baseline = IssueBaseState(
            id="7e99d67b",
            status=Status.IN_PROGRESS,
            title="Test Issue",
            description="test",
            assignee=None,
            labels=[],
            updated_at=datetime.now(UTC),
        )

        # Analyze - should recognize these as the same issue
        changes = comparator.analyze_three_way(
            local={"7e99d67b": local_issue},
            remote={"42": remote_issue},
            baseline={"7e99d67b": baseline},
        )

        # Should have one change (the matched issue)
        assert len(changes) == 1
        change = changes[0]

        # The important thing is it matched by UUID, not created duplicates
        assert change.issue_id == "7e99d67b"
        assert change.baseline_state is not None

    def test_analyze_three_way_unmatched_remote_creates_new(self):
        """Integration test: unmatched remote issues are detected as new."""
        backend = MockBackend("github")
        comparator = SyncStateComparator(backend=backend)

        # Local issue with GitHub ID 42
        local_issue = (
            IssueBuilder()
            .with_id("7e99d67b")
            .with_title("Existing Issue")
            .with_remote_ids({"github": 42})
            .build()
        )

        # Remote has both 42 (matched) and 99 (new)
        remote_issues: dict[str, SyncIssue] = {
            "42": dict_to_sync_issue(
                42, {"id": 42, "title": "Existing Issue", "status": "todo"}
            ),
            "99": dict_to_sync_issue(
                99, {"id": 99, "title": "New Remote Issue", "status": "todo"}
            ),
        }

        from roadmap.core.services.sync.sync_state import IssueBaseState

        baseline = {
            "7e99d67b": IssueBaseState(
                id="7e99d67b",
                status=Status.TODO,
                title="Existing Issue",
                description="test",
                assignee=None,
                labels=[],
                updated_at=datetime.now(UTC),
            )
        }

        changes = comparator.analyze_three_way(
            local={"7e99d67b": local_issue},
            remote=remote_issues,
            baseline=baseline,
        )

        # Should have 2 changes: matched issue + new remote issue
        assert len(changes) == 2

        # Find the new issue change (it gets _remote_ prefix)
        new_issue_change = next(
            (c for c in changes if c.issue_id == "_remote_99"), None
        )
        assert new_issue_change is not None
        # It's a "remote_only" conflict since it only exists remotely
        assert new_issue_change.conflict_type == "remote_only"

    def test_different_backend_name_does_not_match(self):
        """Test that wrong backend name in remote_ids prevents matching."""
        github_backend = MockBackend("github")
        comparator = SyncStateComparator(backend=github_backend)

        # Local issue has GitLab ID but no GitHub ID
        local_issue = (
            IssueBuilder()
            .with_id("7e99d67b")
            .with_title("Test Issue")
            .with_remote_ids({"gitlab": 99})  # Only GitLab ID!
            .build()
        )

        # Remote issue from GitHub
        remote_issue = dict_to_sync_issue(42, {"id": 42, "title": "Test Issue"})

        local_dict = {"7e99d67b": local_issue}
        remote_dict: dict[str, SyncIssue] = {"42": remote_issue}

        normalized_local, normalized_remote = comparator._normalize_remote_keys(
            local_dict, remote_dict
        )

        # Remote should NOT match local (wrong backend)
        assert "7e99d67b" not in normalized_remote
        # Remote gets _remote_ prefix instead
        assert "_remote_42" in normalized_remote
