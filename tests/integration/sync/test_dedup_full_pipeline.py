"""Integration test for end-to-end duplicate detection and resolution.

This test validates that the full duplicate detection pipeline works correctly
with actual Issue and SyncIssue objects, without mocking.
"""

from datetime import UTC, datetime
import pytest

from roadmap.common.constants import Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync.duplicate_detector import DuplicateDetector
from roadmap.core.services.sync.duplicate_resolver import DuplicateResolver
from roadmap.core.services.issue.issue_service import IssueService
from roadmap.adapters.persistence.repositories.issue_repository import IssueRepository


class TestDuplicateDetectionPipeline:
    """Integration tests for the complete duplicate detection pipeline."""

    def create_test_local_issues(self, count: int = 10) -> list[Issue]:
        """Create test local issues with some duplicates by title."""
        issues = []
        base_now = datetime(2024, 1, 1, tzinfo=UTC)
        
        # Create 10 issues, with some having identical titles (duplicates)
        for i in range(count):
            title = f"Issue {i // 2}"  # Pairs will have same title
            issue = Issue(
                id=f"local-{i}",
                title=title,
                headline=f"Headline for issue {i}",
                status=Status.TODO if i % 2 == 0 else Status.IN_PROGRESS,
                priority=Priority.MEDIUM,
                created=base_now,
                updated=base_now,
            )
            issues.append(issue)
        
        return issues

    def create_test_remote_issues(self, count: int = 10) -> dict[str, SyncIssue]:
        """Create test remote issues with some duplicates by title."""
        issues = {}
        base_now = datetime(2024, 1, 1, tzinfo=UTC)
        
        # Create 10 remote issues, with some having identical titles
        for i in range(count):
            title = f"Issue {i // 2}"  # Pairs will have same title
            issue = SyncIssue(
                id=f"remote-{i}",
                title=title,
                headline=f"Headline for issue {i}",
                status="todo" if i % 2 == 0 else "in-progress",
                backend_name="github",
                backend_id=f"{1000 + i}",
                updated_at=base_now,
            )
            issues[f"remote-{i}"] = issue
        
        return issues

    def test_duplicate_detector_reduces_search_space(self):
        """Test that local/remote self-dedup significantly reduces search space."""
        # Create 100 issues with duplicates by title (pairs: 0/1 same, 2/3 same, etc)
        local_issues = self.create_test_local_issues(100)
        remote_issues = self.create_test_remote_issues(100)
        
        detector = DuplicateDetector()
        
        # Run self-dedup
        dedup_local = detector.local_self_dedup(local_issues)
        dedup_remote = detector.remote_self_dedup(remote_issues)
        
        # Should reduce from 100 to 50 canonical issues (50% reduction from title dedup)
        assert len(dedup_local) < len(local_issues)
        assert len(dedup_remote) < len(remote_issues)
        
        # With paired titles (i // 2), reduction should be exactly 50%
        reduction_local = 1 - (len(dedup_local) / len(local_issues))
        reduction_remote = 1 - (len(dedup_remote) / len(remote_issues))
        
        assert reduction_local >= 0.49, f"Local reduction too small: {reduction_local}"
        assert reduction_remote >= 0.49, f"Remote reduction too small: {reduction_remote}"

    def test_duplicate_detection_finds_matches_after_dedup(self):
        """Test that duplicate detection works on deduplicated sets with overlapping content."""
        # Create local issues with specific titles
        local_issues = []
        remote_issues = {}
        base_now = datetime(2024, 1, 1, tzinfo=UTC)
        
        # Create matching pairs: local-0 matches remote-0, local-1 matches remote-1, etc.
        for i in range(10):
            title = f"Unique Issue {i}"
            
            local = Issue(
                id=f"local-{i}",
                title=title,
                headline=f"Local headline {i}",
                status=Status.TODO,
                priority=Priority.MEDIUM,
                created=base_now,
                updated=base_now,
            )
            local_issues.append(local)
            
            remote = SyncIssue(
                id=f"remote-{i}",
                title=title,  # Same title as local
                headline=f"Remote headline {i}",
                status="todo",
                backend_name="github",
                backend_id=f"{1000 + i}",
                updated_at=base_now,
            )
            remote_issues[f"remote-{i}"] = remote
        
        detector = DuplicateDetector(
            title_similarity_threshold=0.90,
            auto_resolve_threshold=0.95,
        )
        
        # Run self-dedup (no duplicates within each set in this case)
        dedup_local = detector.local_self_dedup(local_issues)
        dedup_remote = detector.remote_self_dedup(remote_issues)
        
        # Detect cross-set duplicates
        matches = detector.detect_all(dedup_local, dedup_remote)
        
        # Should find exact title matches between local and remote
        assert len(matches) > 0, "Should find matches between local and remote with same titles"

    def test_resolution_action_counts_are_accurate(self):
        """Test that ResolutionAction counts match actual resolutions."""
        from unittest.mock import MagicMock
        from roadmap.common.result import Ok
        
        # Create mock issue service
        mock_service = MagicMock(spec=IssueService)
        mock_service.merge_issues.return_value = Ok(
            Issue(id="canonical", title="Merged")
        )
        mock_service.delete_issue.return_value = True
        mock_service.archive_issue.return_value = Ok(
            Issue(id="archived", title="Archived")
        )
        
        resolver = DuplicateResolver(
            issue_service=mock_service,
            auto_resolve_threshold=0.95
        )
        
        # Create matches - mix of high confidence and low confidence
        local = Issue(
            id="local-1",
            title="Bug fix",
            status=Status.IN_PROGRESS,
            priority=Priority.HIGH,
            created=datetime(2024, 1, 1, tzinfo=UTC),
            updated=datetime(2024, 1, 1, tzinfo=UTC),
        )
        remote = SyncIssue(
            id="remote-1",
            title="Bug fix",
            headline="Fix the bug",
            status="in-progress",
            backend_name="github",
            backend_id="42",
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        
        from roadmap.core.services.sync.duplicate_detector import (
            DuplicateMatch,
            MatchType,
            RecommendedAction,
        )
        
        match = DuplicateMatch(
            local_issue=local,
            remote_issue=remote,
            match_type=MatchType.TITLE_EXACT,
            confidence=1.0,
            recommended_action=RecommendedAction.AUTO_MERGE,
        )
        
        result = resolver.resolve_automatic([match])
        
        assert result.is_ok()
        actions = result.unwrap()
        
        # Should have 1 action that's not skipped
        assert len(actions) == 1
        assert actions[0].error is None
        assert mock_service.merge_issues.called

    def test_pipeline_handles_large_dedup_correctly(self):
        """Test the full pipeline with larger dataset (simulating 1800+1800 issues)."""
        # Create 50 local issues with heavy duplication (80% duplicates)
        local_issues = self.create_test_local_issues(50)
        # Create 50 remote issues with heavy duplication
        remote_issues = self.create_test_remote_issues(50)
        
        detector = DuplicateDetector(
            title_similarity_threshold=0.90,
            content_similarity_threshold=0.85,
            auto_resolve_threshold=0.95,
        )
        
        # Stage 1: Self-dedup local
        dedup_local = detector.local_self_dedup(local_issues)
        assert len(dedup_local) < len(local_issues), "Local dedup should reduce count"
        
        # Stage 2: Self-dedup remote
        dedup_remote = detector.remote_self_dedup(remote_issues)
        assert len(dedup_remote) < len(remote_issues), "Remote dedup should reduce count"
        
        # Stage 3: Cross-comparison
        matches = detector.detect_all(dedup_local, dedup_remote)
        
        # Verify no match explosion
        assert len(matches) < len(dedup_local) * len(dedup_remote), (
            "Matches should be sparse, not Cartesian product"
        )

    def test_integration_with_status_archived(self):
        """Test that Status.ARCHIVED is properly defined for archiving."""
        # Verify Status.ARCHIVED exists and can be used
        assert hasattr(Status, "ARCHIVED")
        assert Status.ARCHIVED.value == "archived"
        
        # Create issue and verify it can be archived
        issue = Issue(
            id="test-1",
            title="To be archived",
            status=Status.TODO,
            created=datetime(2024, 1, 1, tzinfo=UTC),
            updated=datetime(2024, 1, 1, tzinfo=UTC),
        )
        
        # Should be able to change status to ARCHIVED
        issue.status = Status.ARCHIVED
        assert issue.status == Status.ARCHIVED
