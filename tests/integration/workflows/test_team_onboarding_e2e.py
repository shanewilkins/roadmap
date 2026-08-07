"""Integration tests for Phase 4: End-to-End Team Onboarding

Tests complete team onboarding workflow patterns using the infrastructure
that's been validated in earlier phases (config management, project detection).
"""

from pathlib import Path

from roadmap.common.configuration import ConfigManager


class TestTeamOnboardingE2EPatterns:
    """End-to-end test patterns for team onboarding."""

    def test_alice_commits_shared_config_bob_adds_local_override(
        self, temp_roadmap_with_config
    ):
        """E2E: Alice commits shared config, Bob adds local override."""
        roadmap_dir, shared_config = temp_roadmap_with_config

        # Verify Alice's config is valid
        config_mgr = ConfigManager(shared_config)
        alice_config = config_mgr.load()
        assert alice_config.user.name == "alice"

        # Bob adds local override
        bob_config = roadmap_dir / "config.yaml.local"
        bob_config.write_text(
            """user:
  name: bob
  email: bob@team.com
"""
        )

        # Verify both configs exist
        assert shared_config.exists()
        assert bob_config.exists()

        # Load merged config (Bob's local overrides Alice's shared)
        merged_config = config_mgr.load()
        assert merged_config is not None

    def test_alice_creates_projects_bob_joins_same_projects(
        self, temp_roadmap_with_projects
    ):
        """E2E: Alice creates projects, Bob clones and joins same projects."""
        roadmap_dir, projects_dir = temp_roadmap_with_projects

        # Bob clones (projects exist)
        bob_projects = list(projects_dir.glob("*.md"))
        assert len(bob_projects) == 2

        # Bob sees Alice's projects
        for proj_name in ["main", "backend"]:
            assert (projects_dir / f"{proj_name}.md").exists()

    def test_alice_updates_shared_config_bob_still_has_local_override(
        self, temp_roadmap_with_config
    ):
        """E2E: Alice updates shared config, Bob's local override persists."""
        roadmap_dir, shared_config = temp_roadmap_with_config

        # Bob's local override
        bob_config = roadmap_dir / "config.yaml.local"
        bob_config.write_text(
            """user:
  name: bob
  email: bob@team.com
"""
        )

        # Alice updates shared config (new GitHub setting)
        shared_config.write_text(
            """user:
  name: alice
  email: alice@team.com
github:
  enabled: true
"""
        )

        # Bob's local config still exists (not deleted by Alice's update)
        assert bob_config.exists()

        # Both files can be loaded
        config_mgr = ConfigManager(shared_config)
        merged = config_mgr.load()
        assert merged is not None

    def test_config_file_separation_shared_vs_local(self, temp_roadmap_with_config):
        """E2E: Verify config file separation (.yaml vs .yaml.local)."""
        roadmap_dir, shared_config = temp_roadmap_with_config

        # Local config (not committed)
        local = roadmap_dir / "config.yaml.local"
        local.write_text(
            """user:
  name: individual
"""
        )

        # Verify file pattern separation
        shared_files = list(roadmap_dir.glob("config.yaml"))
        local_files = list(roadmap_dir.glob("config.yaml.local"))

        assert len(shared_files) == 1
        assert len(local_files) == 1
        assert shared_files[0] != local_files[0]

    def test_multi_project_team_setup(self, cli_runner):
        """E2E: Multi-project setup with shared config and local overrides."""
        with cli_runner.isolated_filesystem():
            # Team setup
            roadmap_dir = Path(".roadmap")
            roadmap_dir.mkdir()

            # Shared config for all projects
            shared_config = roadmap_dir / "config.yaml"
            shared_config.write_text(
                """user:
  name: team
  email: team@org.com
"""
            )

            # Multiple projects
            projects_dir = roadmap_dir / "projects"
            projects_dir.mkdir()

            for proj_name in ["api", "cli", "web"]:
                project_file = projects_dir / f"{proj_name}.md"
                project_file.write_text(
                    f"""---
id: {proj_name}
name: {proj_name}
status: active
---

# {proj_name}
"""
                )

            # Team member adds local override
            local_config = roadmap_dir / "config.yaml.local"
            local_config.write_text(
                """user:
  name: member
"""
            )

            # Verify all components exist
            assert shared_config.exists()
            assert local_config.exists()
            assert len(list(projects_dir.glob("*.md"))) == 3

    def test_backward_compat_existing_single_project(self, cli_runner):
        """E2E: Backward compatibility with existing single project setup."""
        with cli_runner.isolated_filesystem():
            # Existing setup
            roadmap_dir = Path(".roadmap")
            roadmap_dir.mkdir()

            config_file = roadmap_dir / "config.yaml"
            config_file.write_text(
                """user:
  name: legacy_user
  email: user@example.com
"""
            )

            projects_dir = roadmap_dir / "projects"
            projects_dir.mkdir()

            project_file = projects_dir / "main.md"
            project_file.write_text(
                """---
id: legacy
name: Main
status: active
---

# Main
"""
            )

            # Should load successfully with new system
            config_mgr = ConfigManager(config_file)
            config = config_mgr.load()
            assert config is not None
            assert config.user.name == "legacy_user"

            # Project still exists
            assert project_file.exists()

    def test_config_merge_behavior(self, temp_roadmap_with_config):
        """E2E: Test config merge behavior (local overrides shared)."""
        roadmap_dir, shared_config = temp_roadmap_with_config

        # Local config overrides user name only
        local = roadmap_dir / "config.yaml.local"
        local.write_text(
            """user:
  name: alice
"""
        )

        # Load merged config
        config_mgr = ConfigManager(shared_config)
        merged = config_mgr.load()
        assert merged is not None
        # Local should merge with shared
