"""Integration tests for DeduplicateService."""

import pytest

from roadmap.application.services.deduplicate_service import DeduplicateService
from roadmap.core.services.sync.duplicate_detector import DuplicateDetector
from tests.fixtures.factories import DuplicateSetFactory, IssueFactory, SyncIssueFactory
from tests.fixtures.fakes.fake_issue_repository import (
    FakeIssueRepository,
    IssueNotFound,
)


@pytest.fixture
def fake_repo():
    """Provide a fresh fake repository for each test."""
    return FakeIssueRepository()


@pytest.fixture
def duplicate_detector():
    """Provide duplicate detector with default thresholds."""
    return DuplicateDetector(
        title_similarity_threshold=0.90,
        content_similarity_threshold=0.85,
        auto_resolve_threshold=0.95,
    )


@pytest.fixture
def dedup_service(fake_repo, duplicate_detector):
    """Provide DeduplicateService with fakes."""
    return DeduplicateService(
        issue_repo=fake_repo,
        duplicate_detector=duplicate_detector,
    )


class TestDeduplicateServiceBasics:
    """Test basic deduplication functionality."""

    def test_returns_clean_local_and_remote_data(self, dedup_service, fake_repo):
        """Test that dedup returns deduplicated data structures."""
        canonical = IssueFactory.create(title="Build feature X")
        dup1 = IssueFactory.create(title="Build feature X")
        dup2 = IssueFactory.create(title="Build feature X")

        fake_repo.save_all([canonical, dup1, dup2])

        # Execute dedup
        response = dedup_service.execute(
            local_issues=[canonical, dup1, dup2],
            remote_issues={},
            dry_run=False,
        )

        # Only canonical in result
        assert len(response.local_issues) == 1
        assert response.local_issues[0].id == canonical.id

        # Duplicates removed
        assert response.duplicates_removed == 2

    def test_dedup_filters_remote_issues_too(self, dedup_service):
        """Test that dedup filters both local and remote."""
        canonical = IssueFactory.create(title="Design system")
        remote_dup1 = SyncIssueFactory.create(title="Design system")
        remote_dup2 = SyncIssueFactory.create(title="Design system")

        response = dedup_service.execute(
            local_issues=[canonical],
            remote_issues={"github-1": remote_dup1, "github-2": remote_dup2},
            dry_run=False,
        )

        # One remote preserved, one removed (self-dedup of remote)
        assert len(response.remote_issues) == 1

    def test_dry_run_doesnt_execute_deletions(self, dedup_service, fake_repo):
        """Test that dry_run=True prevents actual deletion."""
        canonical = IssueFactory.create(title="Test")
        dup = IssueFactory.create(title="Test")

        fake_repo.save_all([canonical, dup])

        response = dedup_service.execute(
            local_issues=[canonical, dup],
            remote_issues={},
            dry_run=True,
        )

        # Still filtered from response
        assert len(response.local_issues) == 1

        # But NOT actually deleted from repo
        assert len(fake_repo.get_all()) == 2
        fake_repo.get(dup.id)  # Should not raise

    def test_non_dry_run_actually_deletes(self, dedup_service, fake_repo):
        """Test that dry_run=False actually deletes."""
        canonical = IssueFactory.create(title="Test")
        dup = IssueFactory.create(title="Test")

        fake_repo.save_all([canonical, dup])

        dedup_service.execute(
            local_issues=[canonical, dup],
            remote_issues={},
            dry_run=False,
        )

        # Deleted from repo
        assert len(fake_repo.get_all()) == 1
        with pytest.raises(IssueNotFound):
            fake_repo.get(dup.id)

        # And tracked in deleted_ids
        assert dup.id in fake_repo.deleted_ids

    def test_returns_correct_counts(self, dedup_service):
        """Test that duplicates_removed count is accurate."""
        canonical = IssueFactory.create(title="Feature")
        dup1 = IssueFactory.create(title="Feature")
        dup2 = IssueFactory.create(title="Feature")

        response = dedup_service.execute(
            local_issues=[canonical, dup1, dup2],
            remote_issues={},
            dry_run=False,
        )

        assert response.duplicates_removed == 2


class TestDeduplicateServiceCounts:
    """Test that dedup reports correct counts."""

    def test_counts_duplicates_removed_local(self, dedup_service):
        """Test that duplicates_removed is accurate for local duplicates."""
        canonical, dups, remote_dups = (
            DuplicateSetFactory.create_canonical_with_duplicates(
                num_local_duplicates=3,
                num_remote_duplicates=0,
            )
        )

        response = dedup_service.execute(
            local_issues=[canonical] + dups,
            remote_issues={},
            dry_run=False,
        )

        # 3 local duplicates should be removed
        assert response.duplicates_removed == 3

    def test_counts_duplicates_removed_remote(self, dedup_service):
        """Test that duplicates_removed is accurate for remote duplicates."""
        canonical, dups, remote_dups = (
            DuplicateSetFactory.create_canonical_with_duplicates(
                num_local_duplicates=0,
                num_remote_duplicates=2,
            )
        )

        response = dedup_service.execute(
            local_issues=[canonical],
            remote_issues=remote_dups,
            dry_run=False,
        )

        # 1 remote duplicate should be removed (2 came in, 1 canonical kept)
        assert response.duplicates_removed == 1


class TestDeduplicateServicePreservesCanonical:
    """Test that canonical issues are preserved."""

    def test_canonical_issue_preserved_in_local(self, dedup_service, fake_repo):
        """Test that canonical is kept in local_issues."""
        canonical = IssueFactory.create(id="canonical-1", title="Keep this")
        dup = IssueFactory.create(title="Keep this")

        fake_repo.save_all([canonical, dup])

        response = dedup_service.execute(
            local_issues=[canonical, dup],
            remote_issues={},
            dry_run=False,
        )

        # Canonical preserved
        assert len(response.local_issues) == 1
        assert response.local_issues[0].id == "canonical-1"

        # Duplicate deleted
        assert dup.id in fake_repo.deleted_ids

    def test_canonical_issue_preserved_in_remote(self, dedup_service):
        """Test that ONE canonical is kept in remote_issues after dedup."""
        canonical_local = IssueFactory.create(title="Sync this")
        remote_canonical = SyncIssueFactory.create(id="github-1", title="Sync this")
        remote_dup = SyncIssueFactory.create(title="Sync this")

        response = dedup_service.execute(
            local_issues=[canonical_local],
            remote_issues={"github-1": remote_canonical, "github-2": remote_dup},
            dry_run=False,
        )

        # Only ONE remote preserved (the one not marked as duplicate by resolver)
        assert len(response.remote_issues) == 1
        # The preserved one should have a valid ID
        preserved_key = list(response.remote_issues.keys())[0]
        assert preserved_key in ["github-1", "github-2"]


class TestDeduplicateServiceEmpty:
    """Test edge cases with empty inputs."""

    def test_handles_no_duplicates(self, dedup_service):
        """Test when there are no duplicates."""
        issue1 = IssueFactory.create(title="Feature A")
        issue2 = IssueFactory.create(title="Feature B")

        response = dedup_service.execute(
            local_issues=[issue1, issue2],
            remote_issues={},
            dry_run=False,
        )

        # All issues preserved
        assert len(response.local_issues) == 2
        assert response.duplicates_removed == 0

    def test_handles_empty_local(self, dedup_service):
        """Test with no local issues."""
        response = dedup_service.execute(
            local_issues=[],
            remote_issues={},
            dry_run=False,
        )

        assert response.local_issues == []
        assert response.remote_issues == {}
        assert response.duplicates_removed == 0

    def test_handles_empty_remote(self, dedup_service, fake_repo):
        """Test with no remote issues."""
        canonical = IssueFactory.create(title="Test")
        dup = IssueFactory.create(title="Test")
        fake_repo.save_all([canonical, dup])

        response = dedup_service.execute(
            local_issues=[canonical, dup],
            remote_issues={},
            dry_run=False,
        )

        assert len(response.local_issues) == 1
        assert response.duplicates_removed >= 1
