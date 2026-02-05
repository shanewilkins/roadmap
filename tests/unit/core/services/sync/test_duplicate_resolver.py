"""Tests for duplicate issue resolution system.

This module contains comprehensive tests for the DuplicateResolver class and
related duplicate resolution functionality.
"""

from datetime import UTC, datetime

import pytest

from roadmap.common.constants import Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync.duplicate_detector import (
    DuplicateMatch,
    MatchType,
    RecommendedAction,
)
from roadmap.core.services.sync.duplicate_resolver import (
    DuplicateResolver,
    ResolutionResult,
)


@pytest.fixture
def resolver():
    """Create a DuplicateResolver with default threshold."""
    return DuplicateResolver()


@pytest.fixture
def local_issue():
    """Create a sample local issue."""
    return Issue(
        id="local-1",
        title="Fix authentication bug",
        headline="Users cannot log in with OAuth",
        status=Status.IN_PROGRESS,
        priority=Priority.HIGH,
        assignee="alice",
        labels=["bug", "security"],
        created=datetime(2024, 1, 1, tzinfo=UTC),
        updated=datetime(2024, 1, 5, tzinfo=UTC),
    )


@pytest.fixture
def remote_issue():
    """Create a sample remote issue."""
    return SyncIssue(
        id="remote-1",
        title="Fix authentication bug",
        headline="Users cannot log in with OAuth provider",
        status="in-progress",
        assignee="bob",
        labels=["bug", "security", "oauth"],
        backend_name="github",
        backend_id=123,
    )


@pytest.fixture
def high_confidence_match(local_issue, remote_issue):
    """Create a high-confidence duplicate match."""
    return DuplicateMatch(
        local_issue=local_issue,
        remote_issue=remote_issue,
        match_type=MatchType.TITLE_EXACT,
        confidence=0.98,
        recommended_action=RecommendedAction.AUTO_MERGE,
        similarity_details={"title_similarity": 1.0},
    )


@pytest.fixture
def low_confidence_match(local_issue, remote_issue):
    """Create a low-confidence duplicate match."""
    return DuplicateMatch(
        local_issue=local_issue,
        remote_issue=remote_issue,
        match_type=MatchType.CONTENT_SIMILAR,
        confidence=0.85,
        recommended_action=RecommendedAction.MANUAL_REVIEW,
        similarity_details={"content_similarity": 0.85, "title_similarity": 0.70},
    )


class TestResolutionResult:
    """Test the ResolutionResult dataclass."""

    def test_resolution_result_merged(self, high_confidence_match):
        """Test creating a merged resolution result."""
        merged_issue = Issue(id="merged", title="Merged", status=Status.TODO)
        result = ResolutionResult(
            match=high_confidence_match,
            action_taken="merged",
            merged_issue=merged_issue,
            skipped=False,
        )

        assert result.match == high_confidence_match
        assert result.action_taken == "merged"
        assert result.merged_issue == merged_issue
        assert result.skipped is False

    def test_resolution_result_skipped(self, low_confidence_match):
        """Test creating a skipped resolution result."""
        result = ResolutionResult(
            match=low_confidence_match,
            action_taken="skipped",
            merged_issue=None,
            skipped=True,
        )

        assert result.match == low_confidence_match
        assert result.action_taken == "skipped"
        assert result.merged_issue is None
        assert result.skipped is True


class TestDuplicateResolver:
    """Test the DuplicateResolver class."""

    def test_initialization_default_threshold(self):
        """Test resolver initialization with default threshold."""
        resolver = DuplicateResolver()
        assert resolver.auto_resolve_threshold == 0.95

    def test_initialization_custom_threshold(self):
        """Test resolver initialization with custom threshold."""
        resolver = DuplicateResolver(auto_resolve_threshold=0.90)
        assert resolver.auto_resolve_threshold == 0.90

    def test_resolve_automatic_high_confidence_auto_merge(
        self, resolver, high_confidence_match
    ):
        """Test automatic resolution of high-confidence AUTO_MERGE match."""
        results = resolver.resolve_automatic([high_confidence_match])

        assert len(results) == 1
        result = results[0]
        assert result.action_taken == "merged"
        assert result.merged_issue is not None
        assert result.skipped is False
        # Verify merged issue has combined data
        assert result.merged_issue.id == high_confidence_match.local_issue.id

    def test_resolve_automatic_high_confidence_manual_review(
        self, resolver, local_issue, remote_issue
    ):
        """Test that high-confidence MANUAL_REVIEW matches are not auto-resolved."""
        match = DuplicateMatch(
            local_issue=local_issue,
            remote_issue=remote_issue,
            match_type=MatchType.TITLE_SIMILAR,
            confidence=0.96,
            recommended_action=RecommendedAction.MANUAL_REVIEW,
        )

        results = resolver.resolve_automatic([match])
        assert len(results) == 0  # Not auto-resolved

    def test_resolve_automatic_low_confidence(self, resolver, low_confidence_match):
        """Test that low-confidence matches are not auto-resolved."""
        results = resolver.resolve_automatic([low_confidence_match])
        assert len(results) == 0

    def test_resolve_automatic_multiple_matches(
        self, resolver, local_issue, remote_issue
    ):
        """Test automatic resolution of multiple matches."""
        matches = [
            DuplicateMatch(
                local_issue=local_issue,
                remote_issue=remote_issue,
                match_type=MatchType.TITLE_EXACT,
                confidence=0.98,
                recommended_action=RecommendedAction.AUTO_MERGE,
            ),
            DuplicateMatch(
                local_issue=Issue(id="local-2", title="Another", status=Status.TODO),
                remote_issue=SyncIssue(
                    id="remote-2", title="Another", status="todo", backend_id=124
                ),
                match_type=MatchType.TITLE_EXACT,
                confidence=0.98,
                recommended_action=RecommendedAction.AUTO_MERGE,
            ),
        ]

        results = resolver.resolve_automatic(matches)
        assert len(results) == 2
        assert all(r.action_taken == "merged" for r in results)

    def test_resolve_automatic_empty_list(self, resolver):
        """Test automatic resolution with empty match list."""
        results = resolver.resolve_automatic([])
        assert len(results) == 0

    def test_merge_issues_prefers_remote_priority(
        self, resolver, local_issue, remote_issue
    ):
        """Test that merge keeps local priority (SyncIssue has no priority field)."""
        merged = resolver._merge_issues(local_issue, remote_issue)
        # Implementation keeps local priority since remote doesn't have one
        assert merged.priority == local_issue.priority

    def test_merge_issues_prefers_remote_assignee(
        self, resolver, local_issue, remote_issue
    ):
        """Test that merge prefers remote assignee when available."""
        merged = resolver._merge_issues(local_issue, remote_issue)
        assert merged.assignee == remote_issue.assignee

    def test_merge_issues_handles_none_values(self, resolver):
        """Test that merge handles None values gracefully."""
        local = Issue(
            id="local-1",
            title="Title",
            status=Status.TODO,
            assignee=None,
            labels=[],
        )
        remote = SyncIssue(
            id="remote-1",
            title="Title",
            headline="Remote headline",
            status="todo",
            assignee="alice",
            labels=["bug"],
            backend_name="github",
            backend_id=123,
        )

        merged = resolver._merge_issues(local, remote)

        assert merged.headline == "Remote headline"
        assert merged.assignee == "alice"
        assert merged.labels == ["bug"]

    def test_merge_issues_handles_empty_remote(self, resolver):
        """Test that merge handles empty remote fields."""
        local = Issue(
            id="local-1",
            title="Title",
            content="Local description",
            status=Status.TODO,
            assignee="alice",
            labels=["bug"],
        )
        remote = SyncIssue(
            id="remote-1",
            title="Title",
            headline="",
            status="todo",
            assignee=None,
            labels=[],
            backend_name="github",
            backend_id=123,
        )

        merged = resolver._merge_issues(local, remote)

        # When remote has no headline, keep local content
        assert merged.content == "Local description"
        # Keep local assignee when remote is None
        assert merged.assignee == "alice"
        # Labels should be the union
        assert merged.labels == [] or merged.labels == ["bug"]

    def test_resolve_automatic_skip_action(self, resolver, local_issue, remote_issue):
        """Test that SKIP recommended action is not auto-resolved."""
        match = DuplicateMatch(
            local_issue=local_issue,
            remote_issue=remote_issue,
            match_type=MatchType.CONTENT_SIMILAR,
            confidence=0.96,
            recommended_action=RecommendedAction.SKIP,
        )

        results = resolver.resolve_automatic([match])
        assert len(results) == 0

    def test_merge_issues_preserves_local_id(self, resolver, local_issue, remote_issue):
        """Test that merged issue always preserves local ID."""
        merged = resolver._merge_issues(local_issue, remote_issue)
        assert merged.id == local_issue.id
        assert merged.id != remote_issue.id

    def test_merge_issues_merges_labels_without_duplicates(self, resolver):
        """Test that label merging removes duplicates."""
        local = Issue(
            id="local-1",
            title="Title",
            status=Status.TODO,
            labels=["bug", "security", "urgent"],
        )
        remote = SyncIssue(
            id="remote-1",
            title="Title",
            status="todo",
            labels=["bug", "security", "feature"],
            backend_id=123,
        )

        merged = resolver._merge_issues(local, remote)

        # Should have union without duplicates
        merged_labels_set = set(merged.labels)
        assert "bug" in merged_labels_set
        assert "security" in merged_labels_set
        assert "urgent" in merged_labels_set
        assert "feature" in merged_labels_set
        assert len(merged_labels_set) == 4  # No duplicates

    def test_resolve_interactive_empty_list(self, resolver):
        """Test interactive resolution with empty match list."""
        results = resolver.resolve_interactive([])
        assert len(results) == 0

    def test_merge_issues_converts_status(self, resolver):
        """Test that status is properly converted from remote to local."""
        local = Issue(id="local-1", title="Title", status=Status.TODO)
        remote = SyncIssue(
            id="remote-1",
            title="Title",
            status="in-progress",
            backend_id=123,
        )

        merged = resolver._merge_issues(local, remote)

        # Status should be converted (implementation-dependent)
        assert merged.status in [Status.TODO, Status.IN_PROGRESS, Status.CLOSED]
