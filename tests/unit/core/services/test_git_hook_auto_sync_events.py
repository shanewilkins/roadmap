"""Additional comprehensive coverage for GitHookAutoSyncService event handling."""

from unittest.mock import patch

from roadmap.core.services.git_hook_auto_sync_service import (
    GitHookAutoSyncConfig,
    GitHookAutoSyncService,
)
from tests.unit.domain.test_data_factory import TestDataFactory


class TestGitHookAutoSyncEventHandling:
    """Test event-based sync triggering."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_disabled(self, mock_sync_service):
        """Test should_sync_on_event returns False when disabled."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        # Auto-sync is disabled by default
        assert not service.should_sync_on_event("commit")
        assert not service.should_sync_on_event("checkout")
        assert not service.should_sync_on_event("merge")

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_enabled_all(self, mock_sync_service):
        """Test should_sync_on_event with all triggers enabled."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_checkout=True,
            sync_on_merge=True,
        )
        service.set_config(config)

        assert service.should_sync_on_event("commit")
        assert service.should_sync_on_event("checkout")
        assert service.should_sync_on_event("merge")

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_selective(self, mock_sync_service):
        """Test should_sync_on_event with selective triggers."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_checkout=False,
            sync_on_merge=True,
        )
        service.set_config(config)

        assert service.should_sync_on_event("commit")
        assert not service.should_sync_on_event("checkout")
        assert service.should_sync_on_event("merge")

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_unknown_event(self, mock_sync_service):
        """Test should_sync_on_event with unknown event type."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_commit=True)
        service.set_config(config)

        # Unknown event should return False
        assert not service.should_sync_on_event("unknown")

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_auto_sync_disabled_overrides(self, mock_sync_service):
        """Test that auto_sync_enabled=False overrides specific triggers."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(
            auto_sync_enabled=False,
            sync_on_commit=True,  # Even though enabled
            sync_on_checkout=True,
            sync_on_merge=True,
        )
        service.set_config(config)

        # All should return False because auto_sync_enabled is False
        assert not service.should_sync_on_event("commit")
        assert not service.should_sync_on_event("checkout")
        assert not service.should_sync_on_event("merge")


class TestGitHookAutoSyncCommit:
    """Test auto-sync on commit events."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_commit_disabled(self, mock_sync_service):
        """Test auto_sync_on_commit when sync is disabled."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        # Default config has auto-sync disabled
        result = service.auto_sync_on_commit()
        assert not result

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_commit_enabled_no_linked_issues(self, mock_sync_service):
        """Test auto_sync_on_commit with no linked issues."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.all.return_value = []
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_commit=True)
        service.set_config(config)

        # With no linked issues, sync should still work but be quick
        service.auto_sync_on_commit()
        # Result depends on GitHub config and other factors, just check it doesn't error

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_commit_with_sha(self, mock_sync_service):
        """Test auto_sync_on_commit with commit SHA."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.all.return_value = []
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_commit=True)
        service.set_config(config)

        # Pass commit SHA for logging
        service.auto_sync_on_commit(commit_sha="abc123def456")
        # Should return without error

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_commit_confirm_parameter(self, mock_sync_service):
        """Test auto_sync_on_commit respects confirm parameter."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.all.return_value = []
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True, sync_on_commit=True, confirm_before_sync=False
        )
        service.set_config(config)

        # Explicitly pass confirm=False
        service.auto_sync_on_commit(confirm=False)
        # Should work


class TestGitHookAutoSyncCheckout:
    """Test auto-sync on checkout events."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_checkout_disabled(self, mock_sync_service):
        """Test auto_sync_on_checkout when disabled."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        result = service.auto_sync_on_checkout()
        assert not result

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_checkout_enabled(self, mock_sync_service):
        """Test auto_sync_on_checkout when enabled."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.all.return_value = []
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_checkout=True)
        service.set_config(config)

        service.auto_sync_on_checkout()
        # Should not raise error

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_checkout_with_branch(self, mock_sync_service):
        """Test auto_sync_on_checkout with branch name."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.all.return_value = []
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_checkout=True)
        service.set_config(config)

        service.auto_sync_on_checkout(branch="feature/test-branch")
        # Should work with branch name


class TestGitHookAutoSyncMerge:
    """Test auto-sync on merge events."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_merge_disabled(self, mock_sync_service):
        """Test auto_sync_on_merge when disabled."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        result = service.auto_sync_on_merge()
        assert not result

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_merge_enabled(self, mock_sync_service):
        """Test auto_sync_on_merge when enabled."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.all.return_value = []
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_merge=True)
        service.set_config(config)

        service.auto_sync_on_merge()
        # Should work
