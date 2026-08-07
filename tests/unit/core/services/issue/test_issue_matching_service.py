"""Tests for issue matching service using similarity-based matching.

Uses factories to create test data and parametrization for matching scenarios.
"""

from unittest.mock import Mock

import pytest

from roadmap.core.domain.issue import Issue
from roadmap.core.services.issue.issue_matching_service import IssueMatchingService


@pytest.fixture
def local_issue_factory():
    """Factory for creating test local Issue objects."""

    def _create_issue(
        issue_id: str = "local-1",
        title: str = "Test Issue",
        content: str = "Test content",
    ) -> Issue:
        issue = Mock(spec=Issue)
        issue.id = issue_id
        issue.title = title
        issue.content = content
        return issue

    return _create_issue


@pytest.fixture
def remote_issue_factory():
    """Factory for creating test remote issue dicts."""

    def _create_remote_issue(
        issue_id: str = "remote-1",
        title: str = "Remote Issue",
        description: str = "Remote content",
    ) -> dict:
        return {
            "id": issue_id,
            "title": title,
            "description": description,
        }

    return _create_remote_issue


class TestIssueMatchingService:
    """Tests for IssueMatchingService."""

    def test_initialization_with_local_issues(self, local_issue_factory):
        """Test matcher initializes with local issues."""
        issue1 = local_issue_factory(issue_id="1", title="Issue 1")
        issue2 = local_issue_factory(issue_id="2", title="Issue 2")

        matcher = IssueMatchingService([issue1, issue2])

        assert len(matcher.local_issues) == 2
        assert matcher.local_issues_by_id["1"] == issue1
        assert matcher.local_issues_by_id["2"] == issue2

    def test_initialization_with_empty_local_issues(self):
        """Test matcher initializes with no local issues."""
        matcher = IssueMatchingService([])

        assert len(matcher.local_issues) == 0
        assert len(matcher.local_issues_by_id) == 0

    def test_find_best_match_returns_none_when_no_local_issues(
        self, remote_issue_factory
    ):
        """Test that find_best_match returns None when no local issues exist."""
        matcher = IssueMatchingService([])
        remote = remote_issue_factory(title="Remote Issue")

        match, score, match_type = matcher.find_best_match(remote)

        assert match is None
        assert score == 0.0
        assert match_type == "new"

    @pytest.mark.parametrize(
        "remote_title,local_title,should_match",
        [
            # Similar enough to match
            ("Issue", "Issue", True),
            # Dissimilar - no match
            ("Fix parser bug", "Update documentation", False),
        ],
    )
    def test_find_best_match_similarity_thresholds_parametrized(
        self,
        local_issue_factory,
        remote_issue_factory,
        remote_title,
        local_title,
        should_match,
    ):
        """Parametrized test for similarity threshold matching."""
        local_issue = local_issue_factory(title=local_title, content="")
        matcher = IssueMatchingService([local_issue])

        remote = remote_issue_factory(title=remote_title)
        match, score, match_type = matcher.find_best_match(remote)

        if should_match:
            assert match == local_issue
            assert match_type in ["auto_link", "potential_duplicate"]
        else:
            assert match is None
            assert match_type == "new"

    def test_find_best_match_with_dict_remote_issue(
        self, local_issue_factory, remote_issue_factory
    ):
        """Test matching with dict-based remote issue."""
        local_issue = local_issue_factory(title="Test", content="")
        matcher = IssueMatchingService([local_issue])

        remote = remote_issue_factory(title="Test")
        match, score, match_type = matcher.find_best_match(remote)

        assert match == local_issue

    def test_find_best_match_with_object_remote_issue(self, local_issue_factory):
        """Test matching with object-based remote issue."""
        local_issue = local_issue_factory(title="Test", content="")
        matcher = IssueMatchingService([local_issue])

        remote = Mock()
        remote.title = "Test"

        match, score, match_type = matcher.find_best_match(remote)

        assert match == local_issue
        assert score > 0.60

    def test_find_best_match_case_insensitive(
        self, local_issue_factory, remote_issue_factory
    ):
        """Test that matching is case-insensitive."""
        local_issue = local_issue_factory(title="Test Issue", content="")
        matcher = IssueMatchingService([local_issue])

        remote = remote_issue_factory(title="test issue")
        match, score, match_type = matcher.find_best_match(remote)

        # Should still match despite case difference
        assert match == local_issue
        assert score > 0.65

    def test_find_best_match_with_whitespace(
        self, local_issue_factory, remote_issue_factory
    ):
        """Test that matching handles extra whitespace."""
        local_issue = local_issue_factory(title="Test", content="")
        matcher = IssueMatchingService([local_issue])

        remote = remote_issue_factory(title="Test")
        match, score, match_type = matcher.find_best_match(remote)

        assert match == local_issue

    def test_find_best_match_selects_best_among_multiple(
        self, local_issue_factory, remote_issue_factory
    ):
        """Test that best match is selected when multiple candidates exist."""
        issue1 = local_issue_factory(issue_id="1", title="Parser bug")
        issue2 = local_issue_factory(issue_id="2", title="Parser bug fix")
        issue3 = local_issue_factory(issue_id="3", title="Documentation")

        matcher = IssueMatchingService([issue1, issue2, issue3])
        remote = remote_issue_factory(title="Parser bug")

        match, score, match_type = matcher.find_best_match(remote)

        assert match in [issue1, issue2]  # One of the parser issues

    def test_find_best_match_with_empty_remote_title(
        self, local_issue_factory, remote_issue_factory
    ):
        """Test that empty remote title returns new."""
        local_issue = local_issue_factory(title="Some issue")
        matcher = IssueMatchingService([local_issue])

        remote = remote_issue_factory(title="")
        match, score, match_type = matcher.find_best_match(remote)

        assert match is None
        assert score == 0.0
        assert match_type == "new"

    def test_find_matches_batch(self, local_issue_factory, remote_issue_factory):
        """Test batch matching of multiple remote issues."""
        local1 = local_issue_factory(issue_id="1", title="Parser bug", content="")
        local2 = local_issue_factory(
            issue_id="2", title="Authentication issue", content=""
        )

        matcher = IssueMatchingService([local1, local2])

        remotes = [
            remote_issue_factory(title="Parser bug"),  # Exact match
            remote_issue_factory(title="Auth problem"),  # Partial match
            remote_issue_factory(title="Totally different issue"),  # No match
        ]

        results = matcher.find_matches_batch(remotes)

        # Should have at least one match in auto_link or potential_duplicate
        assert len(results["auto_link"]) + len(results["potential_duplicate"]) >= 1
        # Should have at least one new item
        assert len(results["new"]) >= 1

    def test_find_matches_batch_organizes_results_by_type(
        self, local_issue_factory, remote_issue_factory
    ):
        """Test that batch results are organized by match type."""
        local = local_issue_factory(title="Parser bug")
        matcher = IssueMatchingService([local])

        remotes = [
            remote_issue_factory(title="Parser bug"),
            remote_issue_factory(title="Parser issue"),
            remote_issue_factory(title="Unrelated"),
        ]

        results = matcher.find_matches_batch(remotes)

        assert "auto_link" in results
        assert "potential_duplicate" in results
        assert "new" in results
        assert len(results["auto_link"]) + len(results["potential_duplicate"]) + len(
            results["new"]
        ) == len(remotes)

    @pytest.mark.parametrize(
        "local_title,remote_title,expected_score_range",
        [
            ("exact title", "exact title", (0.65, 1.0)),  # Very high score
            ("bug fix", "bug fix", (0.65, 1.0)),
            ("issue title", "issue titl", (0.50, 0.95)),  # High but not exact
            ("parser", "serializer", (0.0, 0.6)),  # Low similarity
        ],
    )
    def test_calculate_similarity_score_ranges_parametrized(
        self, local_issue_factory, local_title, remote_title, expected_score_range
    ):
        """Parametrized test for similarity score ranges."""
        local_issue = local_issue_factory(title=local_title, content="")
        matcher = IssueMatchingService([local_issue])

        score = matcher._calculate_similarity(remote_title.lower(), local_issue)

        assert expected_score_range[0] <= score <= expected_score_range[1]

    def test_calculate_similarity_handles_empty_local_title(self, local_issue_factory):
        """Test similarity calculation with empty local title."""
        local_issue = local_issue_factory(title="")
        matcher = IssueMatchingService([local_issue])

        score = matcher._calculate_similarity("remote title", local_issue)

        assert score == 0.0

    def test_auto_link_threshold(self, local_issue_factory, remote_issue_factory):
        """Test that AUTO_LINK_THRESHOLD is 0.90."""
        matcher = IssueMatchingService([])

        assert matcher.AUTO_LINK_THRESHOLD == 0.90

    def test_potential_duplicate_threshold(self, local_issue_factory):
        """Test that POTENTIAL_DUPLICATE_THRESHOLD is 0.70."""
        matcher = IssueMatchingService([])

        assert matcher.POTENTIAL_DUPLICATE_THRESHOLD == 0.70
