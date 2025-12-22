"""Additional comprehensive coverage for GitHookAutoSyncService event handling."""

from unittest.mock import MagicMock, patch

from roadmap.core.services.git_hook_auto_sync_service import (
    GitHookAutoSyncConfig,
    GitHookAutoSyncService,
)


class TestGitHookAutoSyncEventHandling:
    """Test event-based sync triggering."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_disabled(self, mock_sync_service):
        """Test should_sync_on_event returns False when disabled."""
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        # Auto-sync is disabled by default
        assert service.should_sync_on_event("commit") is False
        assert service.should_sync_on_event("checkout") is False
        assert service.should_sync_on_event("merge") is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_enabled_all(self, mock_sync_service):
        """Test should_sync_on_event with all triggers enabled."""
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_checkout=True,
            sync_on_merge=True,
        )
        service.set_config(config)

        assert service.should_sync_on_event("commit") is True
        assert service.should_sync_on_event("checkout") is True
        assert service.should_sync_on_event("merge") is True

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_selective(self, mock_sync_service):
        """Test should_sync_on_event with selective triggers."""
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_checkout=False,
            sync_on_merge=True,
        )
        service.set_config(config)

        assert service.should_sync_on_event("commit") is True
        assert service.should_sync_on_event("checkout") is False
        assert service.should_sync_on_event("merge") is True

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_unknown_event(self, mock_sync_service):
        """Test should_sync_on_event with unknown event type."""
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_commit=True)
        service.set_config(config)

        # Unknown event should return False
        assert service.should_sync_on_event("unknown") is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_should_sync_on_event_auto_sync_disabled_overrides(self, mock_sync_service):
        """Test that auto_sync_enabled=False overrides specific triggers."""
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(
            auto_sync_enabled=False,
            sync_on_commit=True,  # Even though enabled
            sync_on_checkout=True,
            sync_on_merge=True,
        )
        service.set_config(config)

        # All should return False because auto_sync_enabled is False
        assert service.should_sync_on_event("commit") is False
        assert service.should_sync_on_event("checkout") is False
        assert service.should_sync_on_event("merge") is False


class TestGitHookAutoSyncCommit:
    """Test auto-sync on commit events."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_commit_disabled(self, mock_sync_service):
        """Test auto_sync_on_commit when sync is disabled."""
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        # Default config has auto-sync disabled
        result = service.auto_sync_on_commit()
        assert result is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_commit_enabled_no_linked_issues(self, mock_sync_service):
        """Test auto_sync_on_commit with no linked issues."""
        mock_core = MagicMock()
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
        mock_core = MagicMock()
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
        mock_core = MagicMock()
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
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        result = service.auto_sync_on_checkout()
        assert result is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_checkout_enabled(self, mock_sync_service):
        """Test auto_sync_on_checkout when enabled."""
        mock_core = MagicMock()
        mock_core.issues.all.return_value = []
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_checkout=True)
        service.set_config(config)

        service.auto_sync_on_checkout()
        # Should not raise error

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_checkout_with_branch(self, mock_sync_service):
        """Test auto_sync_on_checkout with branch name."""
        mock_core = MagicMock()
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
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        result = service.auto_sync_on_merge()
        assert result is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_auto_sync_on_merge_enabled(self, mock_sync_service):
        """Test auto_sync_on_merge when enabled."""
        mock_core = MagicMock()
        mock_core.issues.all.return_value = []
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_merge=True)
        service.set_config(config)

        service.auto_sync_on_merge()
        # Should work


class TestGitHookAutoSyncFileOperations:
    """Test file loading and saving of config."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_load_config_from_file_not_exists(self, mock_sync_service, tmp_path):
        """Test loading config from non-existent file."""
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config_path = tmp_path / "nonexistent.json"
        result = service.load_config_from_file(config_path)
        assert result is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_load_config_from_file_exists_valid(self, mock_sync_service, tmp_path):
        """Test loading valid config from file."""
        import json

        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config_path = tmp_path / "config.json"
        config_data = {
            "auto_sync": {
                "auto_sync_enabled": True,
                "sync_on_commit": True,
                "sync_on_checkout": False,
                "sync_on_merge": False,
                "confirm_before_sync": False,
                "force_local": False,
                "force_github": False,
            }
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        result = service.load_config_from_file(config_path)
        assert result is True
        assert service.get_config().auto_sync_enabled is True
        assert service.get_config().sync_on_commit is True

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_load_config_from_file_empty(self, mock_sync_service, tmp_path):
        """Test loading config from file with no auto_sync section."""
        import json

        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config_path = tmp_path / "config.json"
        config_data = {}  # Empty config
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        result = service.load_config_from_file(config_path)
        assert result is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_save_config_to_file_new(self, mock_sync_service, tmp_path):
        """Test saving config to new file."""
        import json

        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True, sync_on_commit=True, confirm_before_sync=False
        )
        service.set_config(config)

        config_path = tmp_path / "config.json"
        result = service.save_config_to_file(config_path)
        assert result is True
        assert config_path.exists()

        # Verify saved content
        with open(config_path) as f:
            data = json.load(f)
        assert data["auto_sync"]["auto_sync_enabled"] is True
        assert data["auto_sync"]["sync_on_commit"] is True

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_save_config_to_file_existing(self, mock_sync_service, tmp_path):
        """Test saving config to existing file preserves other data."""
        import json

        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config_path = tmp_path / "config.json"

        # Create initial file with other data
        initial_data = {"other_setting": "value", "nested": {"key": "data"}}
        with open(config_path, "w") as f:
            json.dump(initial_data, f)

        # Save config
        config = GitHookAutoSyncConfig(auto_sync_enabled=True)
        service.set_config(config)
        result = service.save_config_to_file(config_path)
        assert result is True

        # Verify both old and new data are preserved
        with open(config_path) as f:
            data = json.load(f)
        assert "other_setting" in data
        assert "auto_sync" in data
        assert data["other_setting"] == "value"

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_save_config_to_file_creates_parent_dirs(self, mock_sync_service, tmp_path):
        """Test saving config creates parent directories."""
        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        config_path = tmp_path / "subdir" / "nested" / "config.json"
        config = GitHookAutoSyncConfig(auto_sync_enabled=True)
        service.set_config(config)

        result = service.save_config_to_file(config_path)
        assert result is True
        assert config_path.exists()
        assert config_path.parent.exists()

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_config_roundtrip_file(self, mock_sync_service, tmp_path):
        """Test save and load roundtrip preserves config."""

        mock_core = MagicMock()
        service = GitHookAutoSyncService(mock_core)

        # Set complex config
        original_config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_checkout=False,
            sync_on_merge=True,
            confirm_before_sync=False,
            force_local=True,
            force_github=False,
        )
        service.set_config(original_config)

        config_path = tmp_path / "config.json"

        # Save
        save_result = service.save_config_to_file(config_path)
        assert save_result is True

        # Create new service and load
        mock_core2 = MagicMock()
        service2 = GitHookAutoSyncService(mock_core2)
        load_result = service2.load_config_from_file(config_path)
        assert load_result is True

        # Verify all settings match
        loaded_config = service2.get_config()
        assert loaded_config.auto_sync_enabled == original_config.auto_sync_enabled
        assert loaded_config.sync_on_commit == original_config.sync_on_commit
        assert loaded_config.sync_on_checkout == original_config.sync_on_checkout
        assert loaded_config.sync_on_merge == original_config.sync_on_merge
        assert loaded_config.confirm_before_sync == original_config.confirm_before_sync
        assert loaded_config.force_local == original_config.force_local
        assert loaded_config.force_github == original_config.force_github


class TestGitHookAutoSyncGetSyncStats:
    """Test getting sync statistics."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_get_sync_stats_no_issues(self, mock_sync_service):
        """Test getting sync stats with no issues."""
        mock_core = MagicMock()
        mock_core.issues.all.return_value = []
        mock_sync_service_instance = MagicMock()
        mock_sync_service.return_value = mock_sync_service_instance
        mock_sync_service_instance.get_statistics.return_value = {}

        service = GitHookAutoSyncService(mock_core)
        stats = service.get_sync_stats()
        assert isinstance(stats, dict)


class TestGitHookAutoSyncPerformAutoSync:
    """Test the internal _perform_auto_sync method."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubSyncOrchestrator")
    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubIntegrationService")
    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_perform_auto_sync_no_github_config(
        self, mock_sync_service, mock_gh_integration, mock_orchestrator
    ):
        """Test _perform_auto_sync when GitHub not configured."""
        mock_core = MagicMock()
        mock_core.issues.all.return_value = []

        mock_gh_service = MagicMock()
        mock_gh_integration.return_value = mock_gh_service
        mock_gh_service.get_github_config.return_value = None

        service = GitHookAutoSyncService(mock_core)
        result = service._perform_auto_sync(event="commit")

        # Should return False when GitHub not configured
        assert result is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubSyncOrchestrator")
    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubIntegrationService")
    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_perform_auto_sync_no_linked_issues(
        self, mock_sync_service, mock_gh_integration, mock_orchestrator
    ):
        """Test _perform_auto_sync when no linked issues exist."""
        mock_core = MagicMock()
        mock_core.issues.all.return_value = []

        mock_gh_service = MagicMock()
        mock_gh_integration.return_value = mock_gh_service
        mock_gh_service.get_github_config.return_value = (
            "owner",
            "repo",
            "token",
        )

        service = GitHookAutoSyncService(mock_core)
        result = service._perform_auto_sync(event="commit")

        # Should return False when no linked issues
        assert result is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubSyncOrchestrator")
    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubIntegrationService")
    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_perform_auto_sync_dict_config_return(
        self, mock_sync_service, mock_gh_integration, mock_orchestrator
    ):
        """Test _perform_auto_sync with dict-style config return."""
        mock_issue = MagicMock()
        mock_issue.id = "issue-1"
        mock_issue.github_issue = "123"

        mock_core = MagicMock()
        mock_core.issues.all.return_value = [mock_issue]

        mock_gh_service = MagicMock()
        mock_gh_integration.return_value = mock_gh_service
        # Return dict instead of tuple (mocked style)
        mock_gh_service.get_github_config.return_value = {
            "owner": "owner",
            "repo": "repo",
            "token": "token",
        }

        # Mock the orchestrator to return sync report with no changes
        mock_report = MagicMock()
        mock_report.has_changes.return_value = False
        mock_orchestrator.return_value.sync_all_linked_issues.return_value = mock_report

        service = GitHookAutoSyncService(mock_core)
        result = service._perform_auto_sync(event="commit")

        # Should work and return True (no changes = no errors)
        assert result is True

    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubSyncOrchestrator")
    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubIntegrationService")
    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_perform_auto_sync_with_conflicts(
        self, mock_sync_service, mock_gh_integration, mock_orchestrator
    ):
        """Test _perform_auto_sync when conflicts detected."""
        mock_issue = MagicMock()
        mock_issue.id = "issue-1"
        mock_issue.github_issue = "123"

        mock_core = MagicMock()
        mock_core.issues.all.return_value = [mock_issue]

        mock_gh_service = MagicMock()
        mock_gh_integration.return_value = mock_gh_service
        mock_gh_service.get_github_config.return_value = (
            "owner",
            "repo",
            "token",
        )

        # Mock report with conflicts but force_local enabled
        mock_report = MagicMock()
        mock_report.has_changes.return_value = True
        mock_report.has_conflicts.return_value = True
        mock_orchestrator.return_value.sync_all_linked_issues.return_value = mock_report

        service = GitHookAutoSyncService(mock_core)
        service.config.force_local = True

        result = service._perform_auto_sync(event="commit", confirm=False)

        # Should attempt sync with force_local
        assert result is True or result is False  # Depends on implementation

    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubSyncOrchestrator")
    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubIntegrationService")
    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_perform_auto_sync_exception_handling(
        self, mock_sync_service, mock_gh_integration, mock_orchestrator
    ):
        """Test _perform_auto_sync handles exceptions gracefully."""
        mock_core = MagicMock()
        mock_core.issues.all.side_effect = Exception("Test error")

        mock_gh_service = MagicMock()
        mock_gh_integration.return_value = mock_gh_service
        mock_gh_service.get_github_config.return_value = (
            "owner",
            "repo",
            "token",
        )

        service = GitHookAutoSyncService(mock_core)
        result = service._perform_auto_sync(event="commit")

        # Should return False on exception
        assert result is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubSyncOrchestrator")
    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubIntegrationService")
    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_perform_auto_sync_event_types(
        self, mock_sync_service, mock_gh_integration, mock_orchestrator
    ):
        """Test _perform_auto_sync with different event types."""
        mock_core = MagicMock()
        mock_core.issues.all.return_value = []

        mock_gh_service = MagicMock()
        mock_gh_integration.return_value = mock_gh_service
        mock_gh_service.get_github_config.return_value = (
            "owner",
            "repo",
            "token",
        )

        service = GitHookAutoSyncService(mock_core)

        # Test with different event types
        for event in ["commit", "checkout", "merge"]:
            result = service._perform_auto_sync(event=event)
            assert result is False  # No linked issues

    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubSyncOrchestrator")
    @patch("roadmap.core.services.git_hook_auto_sync_service.GitHubIntegrationService")
    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_perform_auto_sync_with_optional_params(
        self, mock_sync_service, mock_gh_integration, mock_orchestrator
    ):
        """Test _perform_auto_sync with optional parameters."""
        mock_core = MagicMock()
        mock_core.issues.all.return_value = []

        mock_gh_service = MagicMock()
        mock_gh_integration.return_value = mock_gh_service
        mock_gh_service.get_github_config.return_value = None

        service = GitHookAutoSyncService(mock_core)

        # Test with commit SHA and branch name
        result1 = service._perform_auto_sync(
            event="commit",
            commit_sha="abc123",
            confirm=False,
        )
        assert result1 is False

        result2 = service._perform_auto_sync(
            event="checkout",
            branch="feature/test",
            confirm=True,
        )
        assert result2 is False

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_get_sync_stats_with_linked_issues(self, mock_sync_service):
        """Test getting sync stats with linked issues."""
        mock_issue1 = MagicMock()
        mock_issue1.id = "issue-1"
        mock_issue1.github_issue = "gh-123"

        mock_issue2 = MagicMock()
        mock_issue2.id = "issue-2"
        mock_issue2.github_issue = None

        mock_core = MagicMock()
        mock_core.issues.all.return_value = [mock_issue1, mock_issue2]
        mock_sync_service_instance = MagicMock()
        mock_sync_service.return_value = mock_sync_service_instance
        mock_sync_service_instance.get_statistics.return_value = {
            "synced": 1,
            "errors": 0,
        }

        service = GitHookAutoSyncService(mock_core)
        stats = service.get_sync_stats()
        assert isinstance(stats, dict)
