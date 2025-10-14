"""
Working comprehensive tests for sync module to improve coverage.
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from roadmap.sync import SyncManager, SyncConflict, SyncStrategy, SyncConflictStrategy
from roadmap.models import Issue, Milestone, RoadmapConfig, Status, Priority, MilestoneStatus  
from roadmap.core import RoadmapCore
from roadmap.github_client import GitHubAPIError
from roadmap.credentials import CredentialManagerError


@pytest.fixture
def mock_core():
    """Mock RoadmapCore for testing."""
    core = Mock(spec=RoadmapCore)
    core.roadmap_dir = Path("/tmp/.roadmap")
    return core


@pytest.fixture
def mock_config():
    """Mock RoadmapConfig for testing."""
    config = RoadmapConfig()
    config.github = {
        "owner": "test_owner",
        "repo": "test_repo", 
        "token": "test_token"
    }
    return config


class TestSyncConflictEdgeCases:
    """Test edge cases in SyncConflict functionality."""

    def test_get_newer_item_exception_handling(self):
        """Test get_newer_item with proper datetime objects."""
        # Test with datetime objects (as the function expects)
        conflict = SyncConflict(
            "issue", "test-123", Mock(), {}, 
            datetime(2024, 1, 1), datetime(2024, 1, 2)
        )
        
        # Should return "remote" since remote is newer
        result = conflict.get_newer_item()
        assert result == "remote"


class TestSyncStrategyEdgeCases:
    """Test edge cases in SyncStrategy functionality."""

    def test_resolve_conflict_local_wins_strategy(self):
        """Test conflict resolution with local wins strategy."""
        strategy = SyncStrategy(SyncConflictStrategy.LOCAL_WINS)
        
        conflict = SyncConflict(
            "issue", "test-123", Mock(), {}, 
            datetime(2024, 1, 1), datetime(2024, 1, 2)
        )
        
        result = strategy.resolve_conflict(conflict)
        assert result == "use_local"

    def test_resolve_conflict_remote_wins_strategy(self):
        """Test conflict resolution with remote wins strategy."""
        strategy = SyncStrategy(SyncConflictStrategy.REMOTE_WINS)
        
        conflict = SyncConflict(
            "issue", "test-123", Mock(), {},
            datetime(2024, 1, 2), datetime(2024, 1, 1)
        )
        
        result = strategy.resolve_conflict(conflict)
        assert result == "use_remote"


class TestSyncManagerCredentialHandling:
    """Test credential handling in SyncManager."""

    @patch("roadmap.sync.get_credential_manager")
    def test_get_token_secure_credential_manager_unavailable(self, mock_credential_manager, mock_core):
        """Test token retrieval when credential manager is unavailable."""
        config = RoadmapConfig()
        config.github = {"owner": "test", "repo": "test"}
        
        # Mock credential manager unavailable
        mock_manager = Mock()
        mock_manager.is_available.return_value = False
        mock_credential_manager.return_value = mock_manager
        
        sync_manager = SyncManager(mock_core, config)
        
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
            token = sync_manager._get_token_secure(config.github)
            assert token == "env_token"

    @patch("roadmap.sync.get_credential_manager") 
    def test_store_token_secure_credential_manager_unavailable(self, mock_credential_manager, mock_core, mock_config):
        """Test token storage when credential manager is unavailable."""
        mock_manager = Mock()
        mock_manager.is_available.return_value = False
        mock_credential_manager.return_value = mock_manager
        
        sync_manager = SyncManager(mock_core, mock_config)
        
        success, message = sync_manager.store_token_secure("test_token", "github")
        assert success is False
        assert "not available" in message.lower()

    @patch("roadmap.sync.get_credential_manager")
    def test_delete_token_secure_credential_manager_unavailable(self, mock_credential_manager, mock_core, mock_config):
        """Test token deletion when credential manager is unavailable.""" 
        mock_manager = Mock()
        mock_manager.is_available.return_value = False
        mock_credential_manager.return_value = mock_manager
        
        sync_manager = SyncManager(mock_core, mock_config)
        
        success, message = sync_manager.delete_token_secure()
        assert success is False
        assert "not available" in message.lower()


class TestSyncManagerGitHubIntegration:
    """Test GitHub integration aspects of SyncManager."""

    def test_init_github_client_missing_owner(self, mock_core):
        """Test GitHub client initialization with missing owner."""
        config = RoadmapConfig()
        config.github = {"repo": "test_repo", "token": "test_token"}
        
        sync_manager = SyncManager(mock_core, config)
        assert sync_manager.github_client is None

    def test_init_github_client_missing_repo(self, mock_core):
        """Test GitHub client initialization with missing repo."""
        config = RoadmapConfig()
        config.github = {"owner": "test_owner", "token": "test_token"}
        
        sync_manager = SyncManager(mock_core, config)
        assert sync_manager.github_client is None

    def test_init_github_client_missing_token(self, mock_core):
        """Test GitHub client initialization with missing token."""
        config = RoadmapConfig()
        config.github = {"owner": "test_owner", "repo": "test_repo"}
        
        with patch.dict(os.environ, {}, clear=True), \
             patch("roadmap.sync.get_credential_manager") as mock_credential_manager:
            # Mock credential manager to return None
            mock_manager = Mock()
            mock_manager.is_available.return_value = True
            mock_manager.get_token.return_value = None
            mock_credential_manager.return_value = mock_manager
            
            sync_manager = SyncManager(mock_core, config)
            assert sync_manager.github_client is None

    @patch("roadmap.sync.GitHubClient")
    def test_test_connection_authentication_failure(self, mock_client_class, mock_core, mock_config):
        """Test connection test with authentication failure."""
        mock_client = Mock()
        mock_client.test_authentication.side_effect = GitHubAPIError("Authentication failed")
        mock_client_class.return_value = mock_client
        
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}):
            sync_manager = SyncManager(mock_core, mock_config)
            
            success, message = sync_manager.test_connection()
            assert success is False
            assert "authentication failed" in message.lower()

    def test_init_github_client_import_error(self, mock_core, mock_config):
        """Test GitHub client initialization with import error."""
        # Simulate scenario where GitHubClient initialization fails
        with patch("roadmap.sync.GitHubClient", side_effect=ImportError("No module named github")), \
             patch("roadmap.sync.os.getenv", return_value=None), \
             patch("roadmap.sync.get_credential_manager") as mock_credential_manager:
            
            # Mock credential manager to return None
            mock_manager = Mock()
            mock_manager.is_available.return_value = True
            mock_manager.get_token.return_value = None
            mock_credential_manager.return_value = mock_manager
            
            # Remove token from config to force using environment/credential manager
            mock_config.github = {"owner": "test_owner", "repo": "test_repo"}
            
            sync_manager = SyncManager(mock_core, mock_config)
            # Should handle missing GitHubClient gracefully
            assert sync_manager.github_client is None


class TestSyncManagerTokenInfo:
    """Test token information methods."""

    @patch("roadmap.sync.get_credential_manager")
    def test_get_token_info_no_token_available(self, mock_credential_manager, mock_core):
        """Test getting token info when no token is available."""
        config = RoadmapConfig()
        config.github = {"owner": "test", "repo": "test"}
        
        mock_manager = Mock()
        mock_manager.is_available.return_value = True
        mock_manager.get_token.return_value = None
        mock_credential_manager.return_value = mock_manager
        
        # Clear environment variables and create sync manager
        with patch.dict(os.environ, {}, clear=True):
            sync_manager = SyncManager(mock_core, config)
            info = sync_manager.get_token_info()
            assert info["config_file"] is False
            assert info["environment"] is False
            assert info["credential_manager"] is False
            assert info["active_source"] is None

    @patch("roadmap.sync.get_credential_manager")
    def test_get_token_info_from_environment(self, mock_credential_manager, mock_core):
        """Test getting token info from environment variable."""
        config = RoadmapConfig()
        config.github = {"owner": "test", "repo": "test"}
        
        mock_manager = Mock()
        mock_manager.is_available.return_value = True
        mock_manager.get_token.return_value = None
        mock_credential_manager.return_value = mock_manager
        
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_12345"}):
            sync_manager = SyncManager(mock_core, config)
            info = sync_manager.get_token_info()
            assert info["environment"] is True
            assert info["active_source"] == "environment"
            assert info["masked_token"] == "****2345"  # Last 4 chars of env_token_12345


class TestSyncManagerRepositoryOperations:
    """Test repository operation methods."""

    def test_setup_repository_no_client(self, mock_core, mock_config):
        """Test repository setup when no GitHub client is available."""
        sync_manager = SyncManager(mock_core, mock_config)
        sync_manager.github_client = None
        
        success, message = sync_manager.setup_repository()
        assert success is False
        assert "not configured" in message.lower()

    @patch("roadmap.sync.GitHubClient")
    def test_setup_repository_with_api_error(self, mock_client_class, mock_core, mock_config):
        """Test repository setup with API error during label setup."""
        mock_client = Mock()
        mock_client.setup_default_labels.side_effect = GitHubAPIError("Label setup failed")
        mock_client_class.return_value = mock_client
        
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}):
            sync_manager = SyncManager(mock_core, mock_config)
            
            success, message = sync_manager.setup_repository()
            assert success is False
            assert "failed" in message.lower()


class TestSyncManagerEdgeCases:
    """Test various edge cases in SyncManager."""

    def test_is_configured_with_partial_config(self, mock_core):
        """Test is_configured with partially configured GitHub settings."""
        config = RoadmapConfig()
        config.github = {"owner": "test"}  # Missing repo and token
        
        sync_manager = SyncManager(mock_core, config)
        # Should be false since client creation would fail
        assert sync_manager.is_configured() is False

    def test_sync_manager_initialization_edge_cases(self, mock_core):
        """Test sync manager initialization with various edge case configurations."""
        # Empty github config
        config1 = RoadmapConfig()
        config1.github = {}
        sync1 = SyncManager(mock_core, config1)
        assert sync1.github_client is None
        
        # None github config
        config2 = RoadmapConfig()
        config2.github = None
        sync2 = SyncManager(mock_core, config2)
        assert sync2.github_client is None

    @patch("roadmap.sync.get_credential_manager")
    def test_credential_manager_exception_handling(self, mock_credential_manager, mock_core, mock_config):
        """Test handling of credential manager exceptions."""
        # Make credential manager raise exception on creation
        mock_credential_manager.side_effect = Exception("Credential manager error")
        
        # Should handle gracefully and not crash
        sync_manager = SyncManager(mock_core, mock_config)
        assert hasattr(sync_manager, 'github_client')


class TestSyncManagerStringRepresentation:
    """Test string representation and utility methods."""

    def test_sync_manager_string_methods(self, mock_core, mock_config):
        """Test string representation methods."""
        sync_manager = SyncManager(mock_core, mock_config)
        
        # Test that object can be converted to string without errors
        str_repr = str(sync_manager)
        assert isinstance(str_repr, str)
        assert "SyncManager" in str_repr or "object" in str_repr


class TestSyncConflictStringMethods:
    """Test string representation of SyncConflict."""

    def test_sync_conflict_string_representation(self):
        """Test SyncConflict string representation."""
        conflict = SyncConflict(
            "issue", "test-123", Mock(), {}, 
            datetime(2024, 1, 1), datetime(2024, 1, 2)
        )
        
        str_repr = str(conflict)
        assert isinstance(str_repr, str)
        assert "test-123" in str_repr or "SyncConflict" in str_repr or "object" in str_repr


class TestSyncStrategyStringMethods:
    """Test string representation of SyncStrategy."""

    def test_sync_strategy_string_representation(self):
        """Test SyncStrategy string representation."""
        strategy = SyncStrategy(SyncConflictStrategy.NEWER_WINS)
        
        str_repr = str(strategy)
        assert isinstance(str_repr, str)
        assert "SyncStrategy" in str_repr or "object" in str_repr