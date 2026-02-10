"""Unit tests for DuplicateResolver - updated for correct analysis-phase behavior.

During the sync analysis phase, the DuplicateResolver should:
1. Detect duplicates between local and remote issues
2. Return link actions (not actually merge, since remote may not exist locally)
3. NOT call service methods that would fail on non-existent remote issues

Actual merging/deletion/archiving happens later in the execution phase
when both issues are confirmed to exist locally.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from roadmap.common.constants import Priority, Status
from roadmap.common.result import Ok
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
    """Create a mock issue service."""
    service = MagicMock(
        spec=__import__(
            "roadmap.core.services.issue.issue_service", fromlist=["IssueService"]
        ).IssueService
    )
    service.merge_issues.return_value = Ok(
        Issue(
            id="local-1",
            title="Merged",
            status=Status.IN_PROGRESS,
            priority=Priority.HIGH,
        )
    )
    service.delete_issue.return_value = True
    service.archive_issue.return_value = Ok(
        Issue(
            id="archived-1",
            title="Archived",
            status=Status.ARCHIVED,
        )
    )
    return service


@pytest.fixture
def resolver(mock_issue_service):
    """Create a DuplicateResolver with mocked service."""
    return DuplicateResolver(
        issue_service=mock_issue_service, auto_resolve_threshold=0.95
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


class TestDuplicateResolverAnalysisPhase:
    """Test DuplicateResolver behavior during sync analysis phase."""

    def test_initialization_default_threshold(self, mock_issue_service):
        """Test resolver initialization with default threshold."""
        resolver = DuplicateResolver(issue_service=mock_issue_service)
        assert resolver.auto_resolve_threshold == 0.95

    def test_initialization_custom_threshold(self, mock_issue_service):
        """Test resolver initialization with custom threshold."""
        resolver = DuplicateResolver(
            issue_service=mock_issue_service, auto_resolve_threshold=0.90
        )
        assert resolver.auto_resolve_threshold == 0.90

    def test_resolve_automatic_returns_result_type(
        self, resolver, high_confidence_match
    ):
        """Test that resolve_automatic returns Result type."""
        result = resolver.resolve_automatic([high_confidence_match])
        assert result.is_ok()
        actions = result.unwrap()
        assert len(actions) == 1
        assert isinstance(actions[0], ResolutionAction)

    def test_resolve_automatic_cross_repo_returns_link_action(
        self, resolver, high_confidence_match
    ):
        """Test that cross-repo duplicates return link action during analysis phase."""
        result = resolver.resolve_automatic([high_confidence_match])
        assert result.is_ok()
        actions = result.unwrap()
        assert len(actions) == 1
        # During analysis, we return link (not delete/archive) since remote may not exist locally
        assert actions[0].action_type == "link"
        assert actions[0].error is None

    def test_resolve_automatic_empty_list(self, resolver):
        """Test automatic resolution with empty match list."""
        result = resolver.resolve_automatic([])
        assert result.is_ok()
        actions = result.unwrap()
        assert len(actions) == 0

    def test_resolve_automatic_filters_low_confidence(
        self, resolver, local_issue, remote_issue
    ):
        """Test that low-confidence matches are filtered."""
        match = DuplicateMatch(
            local_issue=local_issue,
            remote_issue=remote_issue,
            match_type=MatchType.CONTENT_SIMILAR,
            confidence=0.85,
            recommended_action=RecommendedAction.MANUAL_REVIEW,
        )
        result = resolver.resolve_automatic([match])
        assert result.is_ok()
        actions = result.unwrap()
        # Low confidence MANUAL_REVIEW -> returned as skip
        assert len(actions) == 1
        assert actions[0].action_type == "skip"

    def test_resolve_automatic_no_service_calls_during_analysis(
        self, resolver, mock_issue_service, high_confidence_match
    ):
        """Test that no service methods are called during analysis phase."""
        resolver.resolve_automatic([high_confidence_match])
        # Should NOT call merge/delete/archive during analysis
        mock_issue_service.merge_issues.assert_not_called()
        mock_issue_service.delete_issue.assert_not_called()
        mock_issue_service.archive_issue.assert_not_called()

    def test_resolution_action_has_expected_fields(
        self, resolver, high_confidence_match
    ):
        """Test that ResolutionAction has all expected fields."""
        result = resolver.resolve_automatic([high_confidence_match])
        actions = result.unwrap()
        action = actions[0]

        assert hasattr(action, "match")
        assert hasattr(action, "action_type")
        assert hasattr(action, "canonical_issue")
        assert hasattr(action, "duplicate_issue_id")
        assert hasattr(action, "confidence")
        assert hasattr(action, "error")
        assert action.action_type == "link"
        assert action.canonical_issue is not None
        assert action.confidence == 0.98

    def test_resolve_interactive_returns_empty_for_empty_list(self, resolver):
        """Test interactive resolution with empty list."""
        actions = resolver.resolve_interactive([])
        assert isinstance(actions, list)
        assert len(actions) == 0
