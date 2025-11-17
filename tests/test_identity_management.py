"""
Tests for identity management and assignee resolution system.

This test suite covers the comprehensive identity management features:
- User profile management and alias resolution
- Different validation modes (strict, relaxed, github-only, local-only, hybrid)
- Identity learning and suggestion system
- Team configuration management
- Git integration scenarios
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from roadmap.identity import IdentityManager, TeamConfig, UserProfile


@pytest.fixture
def temp_roadmap():
    """Create a temporary roadmap directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        roadmap_path = Path(temp_dir)
        (roadmap_path / ".roadmap").mkdir(parents=True)
        yield roadmap_path


@pytest.fixture
def sample_team_config():
    """Sample team configuration for testing."""
    return {
        'config': {
            'validation_mode': 'hybrid',
            'auto_normalize_assignees': True,
            'require_team_membership': True,
            'allow_identity_learning': True,
        },
        'team_members': {
            'shane.wilkins': {
                'display_name': 'Shane Wilkins',
                'email': 'shane@company.com',
                'github_username': 'shanewilkins',
                'aliases': ['shane', 'Shane', 'Shane Wilkins', 's.wilkins'],
                'roles': ['admin', 'developer'],
                'active': True
            },
            'alice.cooper': {
                'display_name': 'Alice Cooper',
                'email': 'alice@company.com',
                'github_username': 'alicecooper',
                'aliases': ['alice', 'Alice', 'a.cooper'],
                'roles': ['developer'],
                'active': True
            },
            'bob.inactive': {
                'display_name': 'Bob Inactive',
                'email': 'bob@company.com',
                'github_username': 'bobuser',
                'aliases': ['bob', 'Bob'],
                'roles': ['developer'],
                'active': False
            }
        }
    }


@pytest.fixture
def identity_manager_with_team(temp_roadmap, sample_team_config):
    """Create an identity manager with sample team configuration."""
    team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
    with open(team_config_path, 'w') as f:
        yaml.dump(sample_team_config, f)

    return IdentityManager(temp_roadmap)


class TestUserProfile:
    """Test UserProfile functionality."""

    def test_user_profile_creation(self):
        """Test creating a user profile with all fields."""
        profile = UserProfile(
            canonical_id="shane.wilkins",
            display_name="Shane Wilkins",
            email="shane@company.com",
            github_username="shanewilkins",
            aliases={"shane", "Shane", "s.wilkins"},
            roles={"admin", "developer"}
        )

        assert profile.canonical_id == "shane.wilkins"
        assert profile.display_name == "Shane Wilkins"
        assert profile.email == "shane@company.com"
        assert profile.github_username == "shanewilkins"
        assert "shane" in profile.aliases
        assert "admin" in profile.roles
        assert profile.active is True

    def test_user_profile_matches(self):
        """Test name matching functionality."""
        profile = UserProfile(
            canonical_id="shane.wilkins",
            display_name="Shane Wilkins",
            email="shane@company.com",
            github_username="shanewilkins",
            aliases={"shane", "Shane", "s.wilkins"}
        )

        # Test exact matches (case-insensitive)
        assert profile.matches("shane.wilkins")
        assert profile.matches("SHANE.WILKINS")
        assert profile.matches("Shane Wilkins")
        assert profile.matches("shane@company.com")
        assert profile.matches("shanewilkins")

        # Test alias matches
        assert profile.matches("shane")
        assert profile.matches("Shane")
        assert profile.matches("s.wilkins")

        # Test non-matches
        assert not profile.matches("alice")
        assert not profile.matches("bob")
        assert not profile.matches("")
        assert not profile.matches(None)

    def test_add_alias(self):
        """Test adding aliases to a user profile."""
        profile = UserProfile(canonical_id="shane", display_name="Shane")

        profile.add_alias("s.wilkins")
        assert "s.wilkins" in profile.aliases

        profile.add_alias("  shane.w  ")  # Test whitespace handling
        assert "shane.w" in profile.aliases

        profile.add_alias("")  # Empty alias should be ignored
        assert "" not in profile.aliases


class TestIdentityManager:
    """Test IdentityManager core functionality."""

    def test_identity_manager_creation(self, temp_roadmap):
        """Test creating identity manager without existing config."""
        manager = IdentityManager(temp_roadmap)

        assert manager.roadmap_path == temp_roadmap
        assert manager.config.validation_mode == "hybrid"
        assert len(manager.profiles) == 0

    def test_load_team_config(self, identity_manager_with_team):
        """Test loading team configuration from file."""
        manager = identity_manager_with_team

        assert manager.config.validation_mode == "hybrid"
        assert manager.config.auto_normalize_assignees is True
        assert len(manager.profiles) == 3

        shane_profile = manager.profiles["shane.wilkins"]
        assert shane_profile.display_name == "Shane Wilkins"
        assert shane_profile.github_username == "shanewilkins"
        assert "shane" in shane_profile.aliases
        assert "admin" in shane_profile.roles

    def test_save_team_config(self, temp_roadmap):
        """Test saving team configuration to file."""
        manager = IdentityManager(temp_roadmap)

        # Add a team member
        profile = manager.add_team_member(
            canonical_id="test.user",
            display_name="Test User",
            github_username="testuser",
            aliases=["test", "tuser"]
        )

        # Save and reload
        manager.save_team_config()
        manager2 = IdentityManager(temp_roadmap)

        assert "test.user" in manager2.profiles
        reloaded_profile = manager2.profiles["test.user"]
        assert reloaded_profile.display_name == "Test User"
        assert reloaded_profile.github_username == "testuser"
        assert "test" in reloaded_profile.aliases


class TestAssigneeResolution:
    """Test assignee resolution in different modes."""

    def test_resolve_known_assignee_by_canonical_id(self, identity_manager_with_team):
        """Test resolving by canonical ID."""
        manager = identity_manager_with_team

        is_valid, canonical_id, profile = manager.resolve_assignee("shane.wilkins")

        assert is_valid is True
        assert canonical_id == "shane.wilkins"
        assert profile is not None
        assert profile.display_name == "Shane Wilkins"

    def test_resolve_known_assignee_by_alias(self, identity_manager_with_team):
        """Test resolving by alias."""
        manager = identity_manager_with_team

        is_valid, canonical_id, profile = manager.resolve_assignee("shane")

        assert is_valid is True
        assert canonical_id == "shane.wilkins"
        assert profile is not None
        assert profile.display_name == "Shane Wilkins"

    def test_resolve_known_assignee_by_github_username(self, identity_manager_with_team):
        """Test resolving by GitHub username."""
        manager = identity_manager_with_team

        is_valid, canonical_id, profile = manager.resolve_assignee("shanewilkins")

        assert is_valid is True
        assert canonical_id == "shane.wilkins"
        assert profile is not None

    def test_resolve_inactive_user(self, identity_manager_with_team):
        """Test resolving inactive user."""
        manager = identity_manager_with_team

        is_valid, error, profile = manager.resolve_assignee("bob")

        assert is_valid is False
        assert "no longer active" in error
        assert profile is None

    def test_resolve_empty_assignee(self, identity_manager_with_team):
        """Test resolving empty assignee."""
        manager = identity_manager_with_team

        for empty_value in ["", "   ", None]:
            is_valid, error, profile = manager.resolve_assignee(empty_value)
            assert is_valid is False
            assert "cannot be empty" in error
            assert profile is None


class TestValidationModes:
    """Test different validation modes."""

    def test_strict_validation_mode(self, temp_roadmap, sample_team_config):
        """Test strict validation mode."""
        sample_team_config['config']['validation_mode'] = 'strict'
        team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
        with open(team_config_path, 'w') as f:
            yaml.dump(sample_team_config, f)

        manager = IdentityManager(temp_roadmap)

        # Known user should work
        is_valid, result, profile = manager.resolve_assignee("shane")
        assert is_valid is True

        # Unknown user should fail
        is_valid, error, profile = manager.resolve_assignee("unknown")
        assert is_valid is False
        assert "Unknown team member" in error
        assert "Add them to team configuration" in error

    def test_relaxed_validation_mode(self, temp_roadmap, sample_team_config):
        """Test relaxed validation mode."""
        sample_team_config['config']['validation_mode'] = 'relaxed'
        sample_team_config['config']['allow_identity_learning'] = True
        team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
        with open(team_config_path, 'w') as f:
            yaml.dump(sample_team_config, f)

        manager = IdentityManager(temp_roadmap)

        # Known user should work
        is_valid, result, profile = manager.resolve_assignee("shane")
        assert is_valid is True

        # Unknown but reasonable user should work with learning enabled
        is_valid, result, profile = manager.resolve_assignee("newuser")
        assert is_valid is True
        assert result == "newuser"
        assert profile is None

    def test_relaxed_validation_with_suggestions(self, temp_roadmap, sample_team_config):
        """Test relaxed validation with name suggestions."""
        sample_team_config['config']['validation_mode'] = 'relaxed'
        sample_team_config['config']['allow_identity_learning'] = False
        team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
        with open(team_config_path, 'w') as f:
            yaml.dump(sample_team_config, f)

        manager = IdentityManager(temp_roadmap)

        # Typo in known name should suggest correct name
        is_valid, error, profile = manager.resolve_assignee("shan")  # typo of "shane"
        assert is_valid is False
        assert "Did you mean:" in error
        assert "shane" in error

    def test_github_validation_mode(self, temp_roadmap):
        """Test GitHub-only validation mode."""
        config = {
            'config': {'validation_mode': 'github-only'},
            'team_members': {}
        }
        team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
        with open(team_config_path, 'w') as f:
            yaml.dump(config, f)

        manager = IdentityManager(temp_roadmap)

        # Valid GitHub username format
        is_valid, result, profile = manager.resolve_assignee("validusername")
        assert is_valid is True
        assert result == "validusername"

        # Invalid GitHub username format
        is_valid, error, profile = manager.resolve_assignee("invalid-username-")
        assert is_valid is False
        assert "not appear to be a valid GitHub username" in error

    def test_local_validation_mode(self, temp_roadmap):
        """Test local-only validation mode."""
        config = {
            'config': {'validation_mode': 'local-only'},
            'team_members': {}
        }
        team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
        with open(team_config_path, 'w') as f:
            yaml.dump(config, f)

        manager = IdentityManager(temp_roadmap)

        # Any reasonable name should work
        for name in ["alice", "Bob Smith", "j.doe", "user@company.com"]:
            is_valid, result, profile = manager.resolve_assignee(name)
            assert is_valid is True
            assert result == name

        # Invalid characters should fail
        for invalid_name in ["<script>", "user{}", "[]"]:
            is_valid, error, profile = manager.resolve_assignee(invalid_name)
            assert is_valid is False
            assert "not a valid assignee name" in error

    def test_hybrid_validation_mode(self, identity_manager_with_team):
        """Test hybrid validation mode."""
        manager = identity_manager_with_team
        manager.config.validation_mode = "hybrid"

        # Known team member should work
        is_valid, result, profile = manager.resolve_assignee("shane")
        assert is_valid is True
        assert result == "shane.wilkins"
        assert profile is not None

        # GitHub username format should fail (no GitHub validation in this test)
        # but get caught by fallback
        is_valid, result, profile = manager.resolve_assignee("newgithubuser")
        assert is_valid is False  # Should fail since we have team profiles configured
        assert "Unknown team member" in result or "GitHub validation" in result

        # Local name should fail when team profiles are configured (strict mode)
        is_valid, result, profile = manager.resolve_assignee("Local User")
        assert is_valid is False
        assert "Unknown team member" in result


class TestIdentityLearning:
    """Test identity learning and suggestion features."""

    def test_suggest_identity_mappings(self, temp_roadmap):
        """Test identity mapping suggestions."""
        manager = IdentityManager(temp_roadmap)

        assignee_names = [
            "shane", "Shane", "Shane Wilkins", "shane@company.com",
            "alice", "Alice", "a.cooper",
            "bob", "different.user"
        ]

        suggestions = manager.suggest_identity_mappings(assignee_names)

        # Should group shane variants together
        shane_variants = None
        for cluster_names in suggestions.values():
            if "shane" in cluster_names and "Shane" in cluster_names:
                shane_variants = cluster_names
                break

        assert shane_variants is not None
        assert "shane" in shane_variants
        assert "Shane" in shane_variants
        assert "Shane Wilkins" in shane_variants

        # Should group alice variants
        alice_variants = None
        for cluster_names in suggestions.values():
            if "alice" in cluster_names and "Alice" in cluster_names:
                alice_variants = cluster_names
                break

        assert alice_variants is not None

    def test_names_likely_same_person(self, temp_roadmap):
        """Test heuristic for determining if names refer to same person."""
        manager = IdentityManager(temp_roadmap)

        # Test exact matches
        assert manager._names_likely_same_person("shane", "shane")
        assert manager._names_likely_same_person("Shane", "shane")  # case insensitive

        # Test containment
        assert manager._names_likely_same_person("shane", "shane.wilkins")
        assert manager._names_likely_same_person("Shane Wilkins", "Shane")

        # Test email patterns
        assert manager._names_likely_same_person("shane@company.com", "shane")

        # Test component matching
        assert manager._names_likely_same_person("shane.wilkins", "Shane Wilkins")
        assert manager._names_likely_same_person("j.doe", "John Doe")

        # Test non-matches
        assert not manager._names_likely_same_person("shane", "alice")
        assert not manager._names_likely_same_person("john", "jane")

    def test_find_similar_names(self, identity_manager_with_team):
        """Test finding similar names using fuzzy matching."""
        manager = identity_manager_with_team

        # Test close typo
        similar = manager._find_similar_names("shan")  # typo of "shane"
        assert "shane" in similar or "Shane" in similar

        # Test partial match
        similar = manager._find_similar_names("alic")  # partial "alice"
        assert any("alice" in name.lower() for name in similar)

        # Test no match
        similar = manager._find_similar_names("xyz")
        assert len(similar) == 0


class TestTeamManagement:
    """Test team member management functionality."""

    def test_add_team_member(self, temp_roadmap):
        """Test adding new team members."""
        manager = IdentityManager(temp_roadmap)

        profile = manager.add_team_member(
            canonical_id="new.user",
            display_name="New User",
            github_username="newuser",
            email="new@company.com",
            aliases=["new", "nu"]
        )

        assert profile.canonical_id == "new.user"
        assert profile.display_name == "New User"
        assert profile.github_username == "newuser"
        assert "new" in profile.aliases

        # Should be findable
        is_valid, result, found_profile = manager.resolve_assignee("new")
        assert is_valid is True
        assert result == "new.user"
        assert found_profile == profile

    def test_get_user_dashboard_context(self, identity_manager_with_team):
        """Test getting user context for dashboard."""
        manager = identity_manager_with_team

        # Test known user
        context = manager.get_user_dashboard_context("shane")
        assert context['canonical_id'] == "shane.wilkins"
        assert context['display_name'] == "Shane Wilkins"
        assert context['github_username'] == "shanewilkins"
        assert "admin" in context['roles']
        assert "shane" in context['aliases']

        # Test unknown user
        context = manager.get_user_dashboard_context("unknown")
        assert context['canonical_id'] == "unknown"
        assert context['display_name'] == "unknown"
        assert context['github_username'] is None
        assert len(context['roles']) == 0


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    def test_git_project_with_github_integration(self, temp_roadmap):
        """Test scenario: Git project with GitHub integration."""
        # Configure for GitHub mode
        config = {
            'config': {
                'validation_mode': 'hybrid',
                'require_team_membership': True,
                'github_org': 'mycompany'
            },
            'team_members': {
                'shane.wilkins': {
                    'display_name': 'Shane Wilkins',
                    'github_username': 'shanewilkins',
                    'aliases': ['shane'],
                    'roles': ['admin'],
                    'active': True
                }
            }
        }

        team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
        with open(team_config_path, 'w') as f:
            yaml.dump(config, f)

        manager = IdentityManager(temp_roadmap)

        # Known team member should resolve to canonical form
        is_valid, result, profile = manager.resolve_assignee("shane")
        assert is_valid is True
        assert result == "shane.wilkins"
        assert profile.github_username == "shanewilkins"

    def test_local_project_without_github(self, temp_roadmap):
        """Test scenario: Local project without GitHub."""
        # Configure for local-only mode
        config = {
            'config': {
                'validation_mode': 'local-only',
                'require_team_membership': False
            },
            'team_members': {}
        }

        team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
        with open(team_config_path, 'w') as f:
            yaml.dump(config, f)

        manager = IdentityManager(temp_roadmap)

        # Any reasonable name should work
        for name in ["John Doe", "alice@company.com", "developer1"]:
            is_valid, result, profile = manager.resolve_assignee(name)
            assert is_valid is True
            assert result == name
            assert profile is None

    def test_mixed_team_project(self, identity_manager_with_team):
        """Test scenario: Mixed team with GitHub and non-GitHub users."""
        manager = identity_manager_with_team

        # Add a non-GitHub team member
        manager.add_team_member(
            canonical_id="consultant.external",
            display_name="External Consultant",
            aliases=["consultant", "ext"]
        )

        # GitHub user should work
        is_valid, result, profile = manager.resolve_assignee("shane")
        assert is_valid is True
        assert profile.github_username == "shanewilkins"

        # Non-GitHub user should work
        is_valid, result, profile = manager.resolve_assignee("consultant")
        assert is_valid is True
        assert result == "consultant.external"
        assert profile.github_username is None


class TestErrorCases:
    """Test error handling and edge cases."""

    def test_corrupted_team_config(self, temp_roadmap):
        """Test handling corrupted team configuration file."""
        team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
        with open(team_config_path, 'w') as f:
            f.write("invalid: yaml: content: [")

        # Should not crash, should use defaults
        manager = IdentityManager(temp_roadmap)
        assert manager.config.validation_mode == "hybrid"
        assert len(manager.profiles) == 0

    def test_permission_denied_team_config(self, temp_roadmap):
        """Test handling when team config cannot be read."""
        # This is hard to test cross-platform, so we'll mock it
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            manager = IdentityManager(temp_roadmap)
            assert manager.config.validation_mode == "hybrid"
            assert len(manager.profiles) == 0

    def test_unknown_validation_mode(self, temp_roadmap):
        """Test handling unknown validation mode."""
        config = {
            'config': {'validation_mode': 'unknown-mode'},
            'team_members': {}
        }
        team_config_path = temp_roadmap / ".roadmap" / "team.yaml"
        with open(team_config_path, 'w') as f:
            yaml.dump(config, f)

        manager = IdentityManager(temp_roadmap)

        is_valid, error, profile = manager.resolve_assignee("testuser")
        assert is_valid is False
        assert "Unknown validation mode" in error


if __name__ == "__main__":
    pytest.main([__file__])
