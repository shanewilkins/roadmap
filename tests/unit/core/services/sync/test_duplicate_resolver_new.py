"""Tests for duplicate issue resolution with persistence.

This module contains comprehensive tests for the updated DuplicateResolver class
that uses Result<T,E> types and integrates with IssueService for persistence.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock

import pytest

from roadmap.common.constants import Priority, Status
from roadmap.common.result import Ok, Err
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync.duplicate_detector import (
    DuplicateMatch,
    MatchType,
    RecommendedAction,
)
from roadmap.core.services.sync.duplicate_resolver import (
    DuplicateResolver,
    ResolutionAction,
)


@pytest.fixture
def mock_issue_service():
    """Create a mock IssueService."""
    service = MagicMock()
    # By default, operations succeed
    service.merge_issues.return_value = Ok(Issue(id="canonical-1", title="Merged"))
    service.delete_issue.return_value = True
    service.archive_issue.return_value = Ok(Issue(id="dup-1", title="Archived"))
    return service


@pytest.fixture
def resolver(mock_issue_service):
    """Create a DuplicateResolver with mocked issue service."""
    return DuplicateResolver(
        issue_service=mock_issue_service,
        auto_resolve_threshold=0.95
    )


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
        id="gh-123",
        title="Fix authentication bug",  # Same title
        headline="Users cannot log in with OAuth",
        status="in-progress",
        backend_name="github",
        backend_id="123",
        assignee="bob",
        labels=["bug"],
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
    )


@pytest.fixture
def high_confidence_match(local_issue, remote_issue):
    """Create a high-confidence AUTO_MERGE match."""
    return DuplicateMatch(
        local_issue=local_issue,
        remote_issue=remote_issue,
        match_type=MatchType.TITLE_EXACT,
        confidence=1.0,
        recommended_action=RecommendedAction.AUTO_MERGE,
        similarity_details={"title_similarity": 1.0},
    )


@pytest.fixture
def low_confidence_match(local_issue, remote_issue):
    """Create a low-confidence MANUAL_REVIEW match."""
    return DuplicateMatch(
        local_issue=local_issue,
        remote_issue=remote_issue,
        match_type=MatchType.TITLE_SIMILAR,
        confidence=0.85,
        recommended_action=RecommendedAction.MANUAL_REVIEW,
        similarity_details={"title_similarity": 0.85},
    )


class TestDuplicateResolverInitialization:
    """Test DuplicateResolver initialization."""

    def test_initialization_default_threshold(self, mock_issue_service):
        """Test resolver initializes with default threshold."""
        resolver = DuplicateResolver(issue_service=mock_issue_service)
        assert resolver.auto_resolve_threshold == 0.95

    def test_initialization_custom_threshold(self, mock_issue_service):
        """Test resolver initializes with custom threshold."""
        resolver = DuplicateResolver(
            issue_service=mock_issue_service,
            auto_resolve_threshold=0.80
        )
        assert resolver.auto_resolve_threshold == 0.80


class TestResolveAutomatic:
    """Test automatic duplicate resolution."""

    def test_resolve_automatic_high_confidence_auto_merge(
        self, resolver, high_confidence_match
    ):
        """Test automatic resolution of high-confidence AUTO_MERGE match."""
        result = resolver.resolve_automatic([high_confidence_match])
        
        assert result.is_ok()
        actions = result.unwrap()
        
        assert len(actions) == 1
        action = actions[0]
        assert action.action_type in ["delete", "archive"]
        assert action.error is None
        assert action.match == high_confidence_match

    def test_resolve_automatic_skips_manual_review(
        self, resolver, low_confidence_match
    ):
        """Test that manual review matches are skipped."""
        result = resolver.resolve_automatic([low_confidence_match])
        
        assert result.is_ok()
        actions = result.unwrap()
        
        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == "skip"

    def test_resolve_automatic_empty_list(self, resolver):
        """Test resolution with empty match list."""
        result = resolver.resolve_automatic([])
        
        assert result.is_ok()
        actions = result.unwrap()
        assert len(actions) == 0

    def test_resolve_automatic_calls_merge(
        self, resolver, mock_issue_service, high_confidence_match
    ):
        """Test that resolution calls merge_issues."""
        resolver.resolve_automatic([high_confidence_match])
        
        mock_issue_service.merge_issues.assert_called_with(
            high_confidence_match.local_issue.id,
            high_confidence_match.remote_issue.id
        )

    def test_resolve_automatic_merge_failure_skips(
        self, resolver, mock_issue_service, high_confidence_match
    ):
        """Test that merge failure causes resolution to be skipped."""
        mock_issue_service.merge_issues.return_value = Err("Merge failed")
        
        result = resolver.resolve_automatic([high_confidence_match])
        
        assert result.is_ok()
        actions = result.unwrap()
        assert len(actions) == 1
        assert actions[0].action_type == "skip"
        assert actions[0].error is not None

    def test_resolve_automatic_confidence_1_0_triggers_delete(
        self, resolver, mock_issue_service, high_confidence_match
    ):
        """Test that confidence=1.0 (ID collision) triggers deletion."""
        high_confidence_match.confidence = 1.0
        resolver.resolve_automatic([high_confidence_match])
        
        # Should call delete_issue
        mock_issue_service.delete_issue.assert_called()

    def test_resolve_automatic_confidence_less_than_1_0_archives(
        self, resolver, mock_issue_service, high_confidence_match
    ):
        """Test that confidence<1.0 triggers archiving."""
        high_confidence_match.confidence = 0.99
        resolver.resolve_automatic([high_confidence_match])
        
        # Should call archive_issue
        mock_issue_service.archive_issue.assert_called()

    def test_resolve_automatic_archive_includes_metadata(
        self, resolver, mock_issue_service, high_confidence_match
    ):
        """Test that archive includes duplicate metadata."""
        high_confidence_match.confidence = 0.95
        resolver.resolve_automatic([high_confidence_match])
        
        # Check archive was called with metadata
        mock_issue_service.archive_issue.assert_called()
        call_args = mock_issue_service.archive_issue.call_args
        assert call_args[1]["duplicate_of_id"] == high_confidence_match.local_issue.id

    def test_resolve_automatic_multiple_matches(
        self, resolver, mock_issue_service, high_confidence_match, low_confidence_match
    ):
        """Test resolution of multiple matches (auto + skip)."""
        result = resolver.resolve_automatic([high_confidence_match, low_confidence_match])
        
        assert result.is_ok()
        actions = result.unwrap()
        
        # Should have 2 actions: 1 auto-resolved, 1 skipped
        assert len(actions) == 2
        assert any(a.action_type != "skip" for a in actions)
        assert any(a.action_type == "skip" for a in actions)

    def test_resolve_automatic_returns_result_type(self, resolver, high_confidence_match):
        """Test that resolve_automatic returns Result type."""
        result = resolver.resolve_automatic([high_confidence_match])
        
        assert hasattr(result, "is_ok")
        assert hasattr(result, "is_err")
        assert result.is_ok()


class TestResolveInteractive:
    """Test interactive duplicate resolution."""

    def test_resolve_interactive_empty_list(self, resolver):
        """Test interactive resolution with empty list."""
        actions = resolver.resolve_interactive([])
        assert len(actions) == 0

    def test_resolve_interactive_skips_without_rich(
        self, resolver, high_confidence_match, monkeypatch
    ):
        """Test that resolution is skipped if Rich is not available."""
        # Mock Rich import to fail
        import builtins
        original_import = builtins.__import__
        
        def mock_import(name, *args, **kwargs):
            if name == "rich.console" or name == "rich.prompt":
                raise ImportError("No module named 'rich'")
            return original_import(name, *args, **kwargs)
        
        monkeypatch.setattr(builtins, "__import__", mock_import)
        
        actions = resolver.resolve_interactive([high_confidence_match])
        
        # All matches should be skipped
        assert len(actions) == 1
        assert actions[0].action_type == "skip"


class TestResolutionAction:
    """Test ResolutionAction dataclass."""

    def test_action_attributes(self, high_confidence_match):
        """Test that ResolutionAction has required attributes."""
        action = ResolutionAction(
            match=high_confidence_match,
            action_type="delete",
            canonical_issue=Issue(id="can-1", title="Canonical"),
            duplicate_issue_id="dup-1",
            confidence=1.0,
        )
        
        assert action.match == high_confidence_match
        assert action.action_type == "delete"
        assert action.canonical_issue is not None
        assert action.canonical_issue.id == "can-1"
        assert action.duplicate_issue_id == "dup-1"
        assert action.confidence == 1.0
        assert action.error is None

    def test_action_with_error(self, high_confidence_match):
        """Test ResolutionAction with error message."""
        action = ResolutionAction(
            match=high_confidence_match,
            action_type="skip",
            error="Something went wrong",
        )
        
        assert action.error == "Something went wrong"
        assert action.canonical_issue is None
