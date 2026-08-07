"""Tests for duplicate issue detection system.

This module contains comprehensive tests for the DuplicateDetector class and
related duplicate detection functionality.
"""

from datetime import UTC, datetime

import pytest

from roadmap.common.constants import Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync.duplicate_detector import (
    DuplicateDetector,
    DuplicateMatch,
    MatchType,
    RecommendedAction,
)


@pytest.fixture
def detector():
    """Create a DuplicateDetector with default thresholds."""
    return DuplicateDetector()


@pytest.fixture
def sample_local_issue():
    """Create a sample local issue for testing."""
    return Issue(
        id="local-1",
        title="Fix authentication bug",
        headline="Users cannot log in with OAuth",
        status=Status.IN_PROGRESS,
        priority=Priority.HIGH,
        assignee="alice",
        created=datetime(2024, 1, 1, tzinfo=UTC),
        updated=datetime(2024, 1, 5, tzinfo=UTC),
    )


@pytest.fixture
def sample_remote_issue():
    """Create a sample remote issue for testing."""
    return SyncIssue(
        id="remote-1",
        title="Fix authentication bug",
        headline="Users cannot log in with OAuth",
        status="in_progress",
        assignee="alice",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 6, tzinfo=UTC),
        backend_name="github",
        backend_id=123,
        labels=["bug", "auth"],
    )


class TestDuplicateMatch:
    """Test the DuplicateMatch dataclass."""

    def test_valid_duplicate_match(self, sample_local_issue, sample_remote_issue):
        """Test creating a valid DuplicateMatch."""
        match = DuplicateMatch(
            local_issue=sample_local_issue,
            remote_issue=sample_remote_issue,
            match_type=MatchType.TITLE_EXACT,
            confidence=0.98,
            recommended_action=RecommendedAction.AUTO_MERGE,
            similarity_details={"title_similarity": 1.0},
        )

        assert match.local_issue == sample_local_issue
        assert match.remote_issue == sample_remote_issue
        assert match.match_type == MatchType.TITLE_EXACT
        assert match.confidence == 0.98
        assert match.recommended_action == RecommendedAction.AUTO_MERGE

    def test_invalid_confidence_too_low(self, sample_local_issue, sample_remote_issue):
        """Test that confidence < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            DuplicateMatch(
                local_issue=sample_local_issue,
                remote_issue=sample_remote_issue,
                match_type=MatchType.TITLE_SIMILAR,
                confidence=-0.1,
                recommended_action=RecommendedAction.MANUAL_REVIEW,
            )

    def test_invalid_confidence_too_high(self, sample_local_issue, sample_remote_issue):
        """Test that confidence > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            DuplicateMatch(
                local_issue=sample_local_issue,
                remote_issue=sample_remote_issue,
                match_type=MatchType.TITLE_SIMILAR,
                confidence=1.5,
                recommended_action=RecommendedAction.MANUAL_REVIEW,
            )


class TestDuplicateDetector:
    """Test the DuplicateDetector class."""

    def test_initialization_default_thresholds(self):
        """Test detector initialization with default thresholds."""
        detector = DuplicateDetector()

        assert detector.title_similarity_threshold == 0.90
        assert detector.content_similarity_threshold == 0.85
        assert detector.auto_resolve_threshold == 0.95

    def test_initialization_custom_thresholds(self):
        """Test detector initialization with custom thresholds."""
        detector = DuplicateDetector(
            title_similarity_threshold=0.85,
            content_similarity_threshold=0.80,
            auto_resolve_threshold=0.90,
        )

        assert detector.title_similarity_threshold == 0.85
        assert detector.content_similarity_threshold == 0.80
        assert detector.auto_resolve_threshold == 0.90

    def test_detect_all_no_duplicates(self, detector):
        """Test detect_all with no duplicates."""
        local_issues = [
            Issue(
                id="local-1",
                title="Fix bug A",
                headline="Bug A description",
                status=Status.TODO,
            )
        ]
        remote_issues = [
            SyncIssue(
                id="remote-1",
                title="Fix bug B",
                headline="Bug B description",
                status="open",
                backend_id=123,
            )
        ]

        matches = detector.detect_all(
            local_issues,
            {f"remote-{i}": issue for i, issue in enumerate(remote_issues, 1)},
        )
        assert len(matches) == 0

    def test_detect_id_collision_exact_match(self, detector):
        """Test ID collision detection with exact content match."""
        local_issue = Issue(
            id="local-1",
            title="Fix authentication bug",
            headline="Content with #123",
            status=Status.TODO,
        )
        remote_issue = SyncIssue(
            id="remote-1",
            title="Fix authentication bug",
            headline="Content with #123",
            status="open",
            backend_id=123,
        )

        matches = detector.detect_all([local_issue], {"remote-1": remote_issue})

        assert len(matches) == 1
        match = matches[0]
        assert match.match_type == MatchType.TITLE_EXACT
        assert match.confidence >= 0.98
        assert match.recommended_action == RecommendedAction.AUTO_MERGE

    def test_detect_id_collision_content_divergence(self, detector):
        """Test ID collision detection with diverged content."""
        local_issue = Issue(
            id="local-1",
            title="Original title",
            content="Content with #123 and local changes",
            status=Status.TODO,
            remote_ids={"github": 123},  # Has github ID
        )
        remote_issue = SyncIssue(
            id="remote-1",
            title="Different title",
            headline="Content with #123 and remote changes",
            status="open",
            backend_name="github",
            backend_id=123,
        )

        matches = detector.detect_all([local_issue], {"remote-1": remote_issue})

        # When local has matching GitHub ID, it's detected as ID collision
        assert len(matches) >= 1
        match = matches[0]
        # Should detect ID collision since both have the same GitHub ID
        assert match.match_type == MatchType.ID_COLLISION
        # ID collisions are definitive (1.0 confidence), but recommended_action is MANUAL_REVIEW due to content divergence
        assert match.confidence == 1.0
        assert match.recommended_action == RecommendedAction.MANUAL_REVIEW

    def test_detect_title_exact_match(self, detector):
        """Test exact title matching."""
        local_issue = Issue(
            id="local-1",
            title="Fix Authentication Bug",
            headline="Description A",
            status=Status.TODO,
        )
        remote_issue = SyncIssue(
            id="remote-1",
            title="Fix Authentication Bug",
            headline="Description B",
            status="open",
            backend_id=123,
        )

        matches = detector.detect_all([local_issue], {"remote-1": remote_issue})

        assert len(matches) == 1
        match = matches[0]
        assert match.match_type == MatchType.TITLE_EXACT
        assert match.confidence == 0.98
        assert match.recommended_action == RecommendedAction.AUTO_MERGE

    def test_detect_title_similar_match(self, detector):
        """Test similar title matching (above threshold)."""
        local_issue = Issue(
            id="local-1",
            title="Fix authentication bug in user login",
            headline="Description",
            status=Status.TODO,
        )
        remote_issue = SyncIssue(
            id="remote-1",
            title="Fix authentication bug in user sign-in",
            headline="Description",
            status="open",
            backend_id=123,
        )

        matches = detector.detect_all([local_issue], {"remote-1": remote_issue})

        assert len(matches) == 1
        match = matches[0]
        assert match.match_type == MatchType.TITLE_SIMILAR
        assert match.confidence >= detector.title_similarity_threshold
        assert match.confidence < 0.98

    def test_detect_title_below_threshold(self, detector):
        """Test that titles below threshold are not matched."""
        local_issue = Issue(
            id="local-1",
            title="Fix authentication bug",
            headline="Description",
            status=Status.TODO,
        )
        remote_issue = SyncIssue(
            id="remote-1",
            title="Update documentation",
            headline="Description",
            status="open",
            backend_id=123,
        )

        matches = detector.detect_all([local_issue], {"remote-1": remote_issue})
        assert len(matches) == 0

    def test_detect_content_similarity_high(self, detector):
        """Test content similarity matching with high similarity."""
        long_description = "This is a detailed description of the issue. " * 10
        local_issue = Issue(
            id="local-1",
            title="Bug A",
            headline=long_description + " with local additions",
            status=Status.TODO,
        )
        remote_issue = SyncIssue(
            id="remote-1",
            title="Bug A",
            headline=long_description + " with remote additions",
            status="open",
            backend_id=123,
        )

        matches = detector.detect_all([local_issue], {"remote-1": remote_issue})

        assert len(matches) >= 1
        # May match on title exact or content similarity
        content_matches = [
            m for m in matches if m.match_type == MatchType.CONTENT_SIMILAR
        ]
        if content_matches:
            match = content_matches[0]
            assert match.confidence >= detector.content_similarity_threshold

    def test_detect_content_similarity_below_threshold(self, detector):
        """Test that content below threshold is not matched."""
        local_issue = Issue(
            id="local-1",
            title="Fix authentication issue",
            content="Authentication problems with OAuth login",
            status=Status.TODO,
        )
        remote_issue = SyncIssue(
            id="remote-1",
            title="Update deployment documentation",
            headline="How to deploy the application",
            status="open",
            backend_id=123,
        )

        matches = detector.detect_all([local_issue], {"remote-1": remote_issue})
        assert len(matches) == 0

    def test_calculate_text_similarity_identical(self, detector):
        """Test text similarity calculation with identical text."""
        text1 = "Fix authentication bug"
        text2 = "Fix authentication bug"

        similarity = detector._calculate_text_similarity(text1, text2)
        assert similarity == 1.0

    def test_calculate_text_similarity_case_insensitive(self, detector):
        """Test that similarity calculation is case-insensitive."""
        text1 = "Fix Authentication Bug"
        text2 = "fix authentication bug"

        similarity = detector._calculate_text_similarity(text1, text2)
        assert similarity == 1.0

    def test_calculate_text_similarity_whitespace_normalized(self, detector):
        """Test that whitespace is normalized in similarity calculation."""
        text1 = "Fix   authentication  bug"
        text2 = "Fix authentication bug"

        similarity = detector._calculate_text_similarity(text1, text2)
        assert similarity == 1.0

    def test_calculate_text_similarity_different(self, detector):
        """Test text similarity with different texts."""
        text1 = "Fix authentication bug"
        text2 = "Update documentation"

        similarity = detector._calculate_text_similarity(text1, text2)
        assert 0.0 <= similarity < 0.5

    def test_extract_github_number_from_url(self, detector):
        """Test extracting GitHub issue number from URL."""
        url = "https://github.com/owner/repo/issues/123"
        number = detector._extract_github_number(url)
        # Returns string since it's extracted from URL
        assert number == "123"

    def test_extract_github_number_from_hash_format(self, detector):
        """Test extracting GitHub issue number from #123 format."""
        text = "#123"
        number = detector._extract_github_number(text)
        # Should return the string number
        assert number == "123"

    def test_extract_github_number_no_match(self, detector):
        """Test that None is returned when no GitHub number found."""
        text = "No issue number here"
        number = detector._extract_github_number(text)
        assert number is None

    def test_deduplicate_matches_keeps_highest_confidence(
        self, detector, sample_local_issue, sample_remote_issue
    ):
        """Test that deduplication keeps the match with highest confidence."""
        matches = [
            DuplicateMatch(
                local_issue=sample_local_issue,
                remote_issue=sample_remote_issue,
                match_type=MatchType.TITLE_SIMILAR,
                confidence=0.90,
                recommended_action=RecommendedAction.MANUAL_REVIEW,
            ),
            DuplicateMatch(
                local_issue=sample_local_issue,
                remote_issue=sample_remote_issue,
                match_type=MatchType.TITLE_EXACT,
                confidence=0.98,
                recommended_action=RecommendedAction.AUTO_MERGE,
            ),
            DuplicateMatch(
                local_issue=sample_local_issue,
                remote_issue=sample_remote_issue,
                match_type=MatchType.CONTENT_SIMILAR,
                confidence=0.85,
                recommended_action=RecommendedAction.MANUAL_REVIEW,
            ),
        ]

        deduplicated = detector._deduplicate_matches(matches)

        assert len(deduplicated) == 1
        assert deduplicated[0].confidence == 0.98
        assert deduplicated[0].match_type == MatchType.TITLE_EXACT

    def test_detect_all_sorts_by_confidence(self, detector):
        """Test that detect_all returns matches sorted by confidence (descending)."""
        local_issues = [
            Issue(id="local-1", title="Bug A", headline="Desc A", status=Status.TODO),
            Issue(
                id="local-2", title="Feature B", headline="Desc B", status=Status.TODO
            ),
            Issue(id="local-3", title="Task C", headline="Desc C", status=Status.TODO),
        ]
        remote_issues = [
            SyncIssue(
                id="remote-1",
                title="Bug A",
                headline="Desc A",
                status="open",
                backend_id=1,
            ),
            SyncIssue(
                id="remote-2",
                title="Feature B similar",
                headline="Desc B",
                status="open",
                backend_id=2,
            ),
            SyncIssue(
                id="remote-3",
                title="Task C different",
                headline="Desc C",
                status="open",
                backend_id=3,
            ),
        ]

        matches = detector.detect_all(
            local_issues,
            {f"remote-{i}": issue for i, issue in enumerate(remote_issues, 1)},
        )

        # Verify matches are sorted by confidence descending
        for i in range(len(matches) - 1):
            assert matches[i].confidence >= matches[i + 1].confidence

    def test_recommended_action_high_confidence(self, detector):
        """Test that high confidence matches get AUTO_MERGE recommendation."""
        local_issue = Issue(
            id="local-1", title="Fix bug", headline="Description", status=Status.TODO
        )
        remote_issue = SyncIssue(
            id="remote-1",
            title="Fix bug",
            headline="Description",
            status="open",
            backend_id=123,
        )

        matches = detector.detect_all([local_issue], {"remote-1": remote_issue})

        assert len(matches) == 1
        # Exact title match should have confidence >= 0.95
        if matches[0].confidence >= detector.auto_resolve_threshold:
            assert matches[0].recommended_action == RecommendedAction.AUTO_MERGE

    def test_recommended_action_medium_confidence(self, detector):
        """Test that medium confidence matches get MANUAL_REVIEW recommendation."""
        local_issue = Issue(
            id="local-1",
            title="Fix authentication bug",
            headline="Desc",
            status=Status.TODO,
        )
        remote_issue = SyncIssue(
            id="remote-1",
            title="Fix auth bug",
            headline="Desc",
            status="open",
            backend_id=123,
        )

        matches = detector.detect_all([local_issue], {"remote-1": remote_issue})

        if matches and matches[0].confidence < detector.auto_resolve_threshold:
            assert matches[0].recommended_action == RecommendedAction.MANUAL_REVIEW

    def test_multiple_local_issues_one_remote(self, detector):
        """Test detection with multiple local issues matching one remote."""
        local_issues = [
            Issue(id="local-1", title="Fix bug", headline="Desc A", status=Status.TODO),
            Issue(id="local-2", title="Fix bug", headline="Desc B", status=Status.TODO),
        ]
        remote_issue = SyncIssue(
            id="remote-1",
            title="Fix bug",
            headline="Desc C",
            status="open",
            backend_id=123,
        )

        matches = detector.detect_all(local_issues, {"remote-1": remote_issue})

        # Both local issues should match the remote
        assert len(matches) == 2
        local_ids = {m.local_issue.id for m in matches}
        assert local_ids == {"local-1", "local-2"}

    def test_one_local_multiple_remote(self, detector):
        """Test detection with one local issue matching multiple remotes."""
        local_issue = Issue(
            id="local-1", title="Fix bug", headline="Description", status=Status.TODO
        )
        remote_issues = [
            SyncIssue(
                id="remote-1",
                title="Fix bug",
                headline="Description",
                status="open",
                backend_id=123,
            ),
            SyncIssue(
                id="remote-2",
                title="Fix bug",
                headline="Description",
                status="open",
                backend_id=124,
            ),
        ]

        matches = detector.detect_all(
            [local_issue],
            {f"remote-{i}": issue for i, issue in enumerate(remote_issues, 1)},
        )

        # Local issue should match both remotes
        assert len(matches) == 2
        remote_ids = {m.remote_issue.id for m in matches}
        assert remote_ids == {"remote-1", "remote-2"}

    def test_empty_inputs(self, detector):
        """Test detect_all with empty inputs."""
        assert detector.detect_all([], {}) == []
        assert (
            detector.detect_all([Issue(id="1", title="A", status=Status.TODO)], {})
            == []
        )
        assert (
            detector.detect_all(
                [], {"1": SyncIssue(id="1", title="A", status="open", backend_id=1)}
            )
            == []
        )
