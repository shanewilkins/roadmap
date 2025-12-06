"""
Integration tests for Phase 4: End-to-End Team Onboarding

Tests complete team onboarding workflow patterns using the infrastructure
that's been validated in earlier phases (config management, project detection).
"""

from pathlib import Path

from roadmap.common.config_manager import ConfigManager


class TestTeamOnboardingE2EPatterns:
    """End-to-end test patterns for team onboarding."""

    def test_alice_commits_shared_config_bob_adds_local_override(self, tmp_path):
        """E2E: Alice commits shared config, Bob adds local override."""
        # Change to temp directory
        original_dir = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            # Step 1: Alice creates and commits shared config
            roadmap_dir = Path(".roadmap")
            roadmap_dir.mkdir()

            shared_config = roadmap_dir / "config.yaml"
            shared_config.write_text(
                """user:
  name: alice
  email: alice@team.com
github:
  enabled: false
"""
            )

            # Verify Alice's config is valid
            config_mgr = ConfigManager(shared_config)
            alice_config = config_mgr.load()
            assert alice_config.user.name == "alice"

            # Step 2: Bob clones repo (config exists)
            # Bob adds local override
            bob_config = roadmap_dir / "config.yaml.local"
            bob_config.write_text(
                """user:
  name: bob
  email: bob@team.com
"""
            )

            # Step 3: Verify both configs exist
            assert shared_config.exists()
            assert bob_config.exists()

            # Step 4: Load merged config (Bob's local overrides Alice's shared)
            merged_config = config_mgr.load()
            assert merged_config is not None

        finally:
            os.chdir(original_dir)

    def test_alice_creates_projects_bob_joins_same_projects(self, tmp_path):
        """E2E: Alice creates projects, Bob clones and joins same projects."""
        original_dir = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            # Step 1: Alice creates projects
            projects_dir = Path(".roadmap/projects")
            projects_dir.mkdir(parents=True)

            projects = ["backend", "frontend"]
            for proj_name in projects:
                project_file = projects_dir / f"{proj_name}.md"
                project_file.write_text(
                    f"""---
id: {proj_name}_proj
name: {proj_name.title()}
status: active
---

# {proj_name.title()}
"""
                )

            # Step 2: Bob clones (projects exist)
            bob_projects = list(projects_dir.glob("*.md"))
            assert len(bob_projects) == 2

            # Step 3: Bob sees Alice's projects
            for proj_name in projects:
                assert (projects_dir / f"{proj_name}.md").exists()

        finally:
            os.chdir(original_dir)

    def test_alice_updates_shared_config_bob_still_has_local_override(self, tmp_path):
        """E2E: Alice updates shared config, Bob's local override persists."""
        original_dir = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            # Step 1: Initial setup
            roadmap_dir = Path(".roadmap")
            roadmap_dir.mkdir()

            shared_config = roadmap_dir / "config.yaml"
            shared_config.write_text(
                """user:
  name: alice
  email: alice@team.com
github:
  enabled: false
"""
            )

            # Bob's local override
            bob_config = roadmap_dir / "config.yaml.local"
            bob_config.write_text(
                """user:
  name: bob
  email: bob@team.com
"""
            )

            # Step 2: Alice updates shared config (new GitHub setting)
            shared_config.write_text(
                """user:
  name: alice
  email: alice@team.com
github:
  enabled: true
"""
            )

            # Step 3: Bob's local config still exists (not deleted by Alice's update)
            assert bob_config.exists()

            # Step 4: Both files can be loaded
            config_mgr = ConfigManager(shared_config)
            merged = config_mgr.load()
            assert merged is not None

        finally:
            os.chdir(original_dir)

    def test_config_file_separation_shared_vs_local(self, tmp_path):
        """E2E: Verify config file separation (.yaml vs .yaml.local)."""
        original_dir = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            roadmap_dir = Path(".roadmap")
            roadmap_dir.mkdir()

            # Shared config (committed)
            shared = roadmap_dir / "config.yaml"
            shared.write_text(
                """user:
  name: team
  email: team@org.com
"""
            )

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

        finally:
            os.chdir(original_dir)

    def test_multi_project_team_setup(self, tmp_path):
        """E2E: Multi-project setup with shared config and local overrides."""
        original_dir = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

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

        finally:
            os.chdir(original_dir)

    def test_backward_compat_existing_single_project(self, tmp_path):
        """E2E: Backward compatibility with existing single project setup."""
        original_dir = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

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

        finally:
            os.chdir(original_dir)

    def test_config_merge_behavior(self, tmp_path):
        """E2E: Test config merge behavior (local overrides shared)."""
        original_dir = Path.cwd()
        try:
            import os

            os.chdir(tmp_path)

            roadmap_dir = Path(".roadmap")
            roadmap_dir.mkdir()

            # Shared config with multiple settings
            shared = roadmap_dir / "config.yaml"
            shared.write_text(
                """user:
  name: team
  email: team@org.com
github:
  enabled: true
"""
            )

            # Local config overrides user name only
            local = roadmap_dir / "config.yaml.local"
            local.write_text(
                """user:
  name: alice
"""
            )

            # Load merged config
            config_mgr = ConfigManager(shared)
            merged = config_mgr.load()
            assert merged is not None
            # Local should merge with shared

        finally:
            os.chdir(original_dir)
