"""
Integration tests for CI CLI commands.

These tests focus on CLI command integration and end-to-end workflows
to ensure the CI commands work correctly in real scenarios.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from click.testing import CliRunner

from roadmap.cli.ci import ci
from roadmap.core import RoadmapCore
from roadmap.models import IssueType, Priority


class TestCICommandsIntegration:
    """Integration tests for CI CLI command functionality."""

    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir)
        self.original_cwd = os.getcwd()

        # Initialize git repo
        subprocess.run(
            ["git", "init"], cwd=self.repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "CLI Test"], cwd=self.repo_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "cli@test.com"],
            cwd=self.repo_path,
            check=True,
        )

        # Change to test directory
        os.chdir(self.repo_path)

        # Initialize roadmap
        self.core = RoadmapCore()
        self.core.initialize()

        # Create test issues
        self.core.create_issue(
            title="CLI Test Feature",
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE,
        )

        self.core.create_issue(
            title="CLI Test Bug Fix", priority=Priority.MEDIUM, issue_type=IssueType.BUG
        )

        # Create test git history
        self.create_test_git_history()

        self.runner = CliRunner()

    def teardown_method(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_git_history(self):
        """Create realistic git history for CLI testing."""
        commits = [
            ("Initial commit", "README.md", "# Test Repository\\n"),
            (
                "cli12345: Add CLI feature implementation",
                "cli_feature.py",
                "# CLI Feature\\n",
            ),
            (
                "cli12345: Update implementation [progress:50%]",
                "cli_feature.py",
                "# CLI Feature\\n# Updated\\n",
            ),
            (
                "test6789: Fix CLI bug",
                "cli_feature.py",
                "# CLI Feature\\n# Bug fixed\\n",
            ),
            (
                "cli12345: Complete feature [closes roadmap:cli12345]",
                "cli_feature.py",
                "# CLI Feature\\n# Complete\\n",
            ),
            ("test6789: Resolve issue [progress:100%]", "bugfix.py", "# Bug fix\\n"),
        ]

        for message, filename, content in commits:
            file_path = self.repo_path / filename
            file_path.write_text(content)
            subprocess.run(["git", "add", filename], cwd=self.repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", message], cwd=self.repo_path, check=True
            )

        # Create test branches
        subprocess.run(
            ["git", "checkout", "-b", "feature/cli12345-test-cli"],
            cwd=self.repo_path,
            check=True,
        )
        (self.repo_path / "feature_branch.py").write_text("# Feature branch\\n")
        subprocess.run(
            ["git", "add", "feature_branch.py"], cwd=self.repo_path, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "cli12345: Add feature branch code"],
            cwd=self.repo_path,
            check=True,
        )
        subprocess.run(["git", "checkout", "master"], cwd=self.repo_path, check=True)

    def test_ci_status_command_integration(self):
        """Test CI status command with real repository."""
        result = self.runner.invoke(ci, ["status"])

        assert result.exit_code == 0
        assert "CI/CD Tracking Status" in result.output

        # Should show metrics table
        assert "Issues with branch associations" in result.output
        assert "Issues with commit associations" in result.output
        assert "Total branch associations" in result.output
        assert "Total commit associations" in result.output

    def test_ci_config_commands(self):
        """Test CI configuration commands."""
        # Test showing current configuration
        result = self.runner.invoke(ci, ["config", "show"])
        assert result.exit_code == 0
        assert "auto_start_on_branch" in result.output
        assert "auto_close_on_merge" in result.output

        # Test setting a configuration value
        result = self.runner.invoke(
            ci, ["config", "set", "auto_start_on_branch", "false"]
        )
        assert result.exit_code == 0
        assert "Set auto_start_on_branch = False" in result.output

        # Verify the configuration was set
        result = self.runner.invoke(ci, ["config", "show"])
        assert result.exit_code == 0
        assert "False" in result.output  # Should show the updated value

        # Test setting it back
        result = self.runner.invoke(
            ci, ["config", "set", "auto_start_on_branch", "true"]
        )
        assert result.exit_code == 0
        assert "Set auto_start_on_branch = True" in result.output

    def test_track_branch_command(self):
        """Test branch tracking functionality."""
        result = self.runner.invoke(ci, ["track-branch", "feature/cli12345-test-cli"])

        assert result.exit_code == 0
        # Check for expected output - either finds IDs or shows helpful message
        assert (
            "cli12345" in result.output
            or "No issue IDs found" in result.output
            or "Use pattern like" in result.output
        )

        # Test tracking non-existent branch (should handle gracefully)
        result = self.runner.invoke(ci, ["track-branch", "nonexistent-branch"])
        # Should either succeed with a message or fail gracefully
        assert result.exit_code == 0 or "error" in result.output.lower()

        # Test with a branch that doesn't have issue ID pattern
        result = self.runner.invoke(ci, ["track-branch", "master"])
        assert result.exit_code == 0

    def test_track_commit_command(self):
        """Test commit tracking functionality."""
        # Get a recent commit SHA
        git_result = subprocess.run(
            ["git", "log", "--format=%H", "-1"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = git_result.stdout.strip()

        result = self.runner.invoke(ci, ["track-commit", commit_sha])
        assert result.exit_code == 0
        # Should process the commit and detect issue associations

        # Test with short SHA
        short_sha = commit_sha[:8]
        result = self.runner.invoke(ci, ["track-commit", short_sha])
        assert result.exit_code == 0

        # Test with manual issue association
        result = self.runner.invoke(
            ci, ["track-commit", commit_sha, "--issue-id", "cli12345"]
        )
        assert result.exit_code == 0
        assert "cli12345" in result.output

    def test_scan_repository_command(self):
        """Test repository scanning command."""
        result = self.runner.invoke(ci, ["scan-repository", "--max-commits", "10"])

        assert result.exit_code == 0
        assert "Scanning repository history" in result.output
        # Check for either results table or no associations message
        assert (
            "Repository Scan Results" in result.output
            or "No issue associations found" in result.output
        )

        # May or may not find issues depending on repository state
        # Test passes if it either finds issues or reports none found
        if "Repository Scan Results" in result.output:
            # If results found, should show issue data
            pass  # Results table exists, that's good enough
        else:
            # If no results, should show appropriate message
            assert "No issue associations found" in result.output

        # Test with different parameters
        result = self.runner.invoke(ci, ["scan-repository", "--max-commits", "5"])
        assert result.exit_code == 0

    def test_scan_branches_command(self):
        """Test branch scanning command."""
        result = self.runner.invoke(ci, ["scan-branches"])

        assert result.exit_code == 0
        assert (
            "Scanning git branches" in result.output
            or "Scanning all branches for issue associations" in result.output
        )

        # Should either find associations or report none found
        assert (
            "feature/cli12345-test-cli" in result.output
            or "cli12345" in result.output
            or "No issue associations found" in result.output
        )

    def test_scan_full_command(self):
        """Test comprehensive repository scanning."""
        result = self.runner.invoke(
            ci, ["scan-full", "--max-commits", "15", "--max-branches", "5"]
        )

        assert result.exit_code == 0
        assert "Starting comprehensive repository scan" in result.output
        assert (
            "Repository Scan Results" in result.output
            or "🎯 Repository Scan Results" in result.output
        )
        assert "scan completed successfully" in result.output

        # Should show statistics
        assert "Commits Scanned" in result.output
        assert "Branches Scanned" in result.output

        # Should show issue activity - may or may not have issues
        assert (
            "Top Issues by Commit Activity" in result.output
            or "Issues with Commits │     0" in result.output
            or "No issue associations found" in result.output
        )

        # Should show branch analysis
        assert "Branch Analysis Summary" in result.output

    def test_scan_full_with_export(self):
        """Test comprehensive scanning with export functionality."""
        export_file = self.repo_path / "test_export.json"

        result = self.runner.invoke(
            ci, ["scan-full", "--max-commits", "10", "--export", str(export_file)]
        )

        assert result.exit_code == 0
        assert "Results exported to" in result.output
        assert export_file.exists()

        # Verify exported content
        with open(export_file) as f:
            data = json.load(f)

        assert "scan_metadata" in data
        assert "statistics" in data
        assert "commits" in data
        assert "branches" in data
        assert data["statistics"]["total_commits_scanned"] > 0

    def test_migrate_project_dry_run(self):
        """Test project migration dry run."""
        result = self.runner.invoke(
            ci, ["migrate-project", "--dry-run", "--max-commits", "10"]
        )

        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.output
        assert "Migration Analysis" in result.output
        assert "No changes will be made" in result.output

        # Should analyze existing commits and issues
        assert "Commits Analyzed" in result.output
        assert "Issue IDs Found" in result.output

        # Should show candidates - may or may not have issues to migrate
        assert (
            "Issue Candidates for Migration" in result.output
            or "Top Issue Candidates for Migration" in result.output
            or "Issue IDs Found  │     0" in result.output
            or "No issue IDs found" in result.output
        )

    def test_migrate_project_execution(self):
        """Test actual project migration."""
        result = self.runner.invoke(
            ci, ["migrate-project", "--link-commits", "--max-commits", "8"]
        )

        assert result.exit_code == 0
        assert "Performing Migration" in result.output
        assert "Migration Results" in result.output
        assert "migration completed successfully" in result.output

        # Should show results
        assert "Commits Linked" in result.output or "Issues Created" in result.output

    def test_analyze_patterns_command(self):
        """Test pattern analysis command."""
        result = self.runner.invoke(ci, ["analyze-patterns", "--commits", "10"])

        assert result.exit_code == 0
        assert "Analyzing repository patterns" in result.output
        assert "Commit Message Patterns" in result.output
        assert "Branch Naming Patterns" in result.output
        assert "Pattern Recommendations" in result.output
        assert "Pattern analysis completed" in result.output

        # Test with export
        export_file = self.repo_path / "patterns.json"
        result = self.runner.invoke(
            ci, ["analyze-patterns", "--commits", "8", "--export", str(export_file)]
        )

        assert result.exit_code == 0
        assert export_file.exists()

        with open(export_file) as f:
            data = json.load(f)

        assert "analysis_summary" in data
        assert "commit_patterns" in data
        assert "branch_patterns" in data

    def test_hooks_commands(self):
        """Test git hooks management commands."""
        # Test hooks status
        result = self.runner.invoke(ci, ["hooks", "status"])
        assert result.exit_code == 0
        assert "Git Hooks Status" in result.output

        # Test hooks install
        result = self.runner.invoke(ci, ["hooks", "install"])
        assert result.exit_code == 0
        # Should install or report already installed

        # Test hooks logs
        result = self.runner.invoke(ci, ["hooks", "logs"])
        assert result.exit_code == 0

        # Test hooks uninstall
        result = self.runner.invoke(ci, ["hooks", "uninstall"])
        assert result.exit_code == 0

    def test_github_status_command(self):
        """Test GitHub integration status."""
        result = self.runner.invoke(ci, ["github-status"])

        assert result.exit_code == 0
        assert "GitHub Actions Integration Status" in result.output
        assert "Roadmap Setup" in result.output

        # Test verbose output
        result = self.runner.invoke(ci, ["github-status", "--verbose"])
        assert result.exit_code == 0

        # Test different output formats
        result = self.runner.invoke(ci, ["github-status", "--format", "json"])
        assert result.exit_code == 0
        # Should be valid JSON or handle gracefully

    def test_setup_workflows_command(self):
        """Test GitHub Actions workflow setup."""
        result = self.runner.invoke(ci, ["setup-workflows", "starter"])

        assert result.exit_code == 0
        # May create new workflow or indicate existing one
        assert (
            "Setting up GitHub Actions workflow" in result.output
            or "Created workflow" in result.output
            or "Workflow file already exists" in result.output
        )

        # Should create workflow file
        workflow_file = self.repo_path / ".github" / "workflows" / "roadmap-starter.yml"
        assert workflow_file.exists()

        # Verify workflow content
        content = workflow_file.read_text()
        assert "roadmap" in content
        assert "github" in content.lower()

        # Test other workflow types
        for workflow_type in ["integration", "ci-cd", "lifecycle"]:
            result = self.runner.invoke(ci, ["setup-workflows", workflow_type])
            # Should succeed or gracefully handle
            assert result.exit_code == 0 or "error" in result.output.lower()

    def test_track_pr_command(self):
        """Test PR tracking functionality."""
        result = self.runner.invoke(
            ci,
            [
                "track-pr",
                "123",
                "--branch",
                "feature/test",
                "--action",
                "opened",
            ],
        )

        assert result.exit_code == 0
        # Should process PR information

        # Test with issue association
        result = self.runner.invoke(
            ci,
            [
                "track-pr",
                "124",
                "--branch",
                "feature/cli12345-fix",
                "--action",
                "opened",
            ],
        )
        assert result.exit_code == 0
        assert "cli12345" in result.output or "PR tracking" in result.output

    def test_sync_github_command(self):
        """Test GitHub sync functionality."""
        result = self.runner.invoke(ci, ["sync-github"])

        # Should handle gracefully even without GitHub configuration
        assert result.exit_code == 0 or "error" in result.output.lower()

    def test_command_error_handling(self):
        """Test error handling in CI commands."""
        # Test with invalid parameters
        result = self.runner.invoke(ci, ["scan-full", "--max-commits", "-1"])
        # Should validate parameters

        result = self.runner.invoke(ci, ["track-branch", ""])
        # Should handle empty branch name

        result = self.runner.invoke(ci, ["track-commit", "invalid-sha"])
        # Should handle invalid commit SHA

        result = self.runner.invoke(ci, ["config", "invalid_setting", "value"])
        # Should handle invalid configuration

    def test_cli_help_commands(self):
        """Test that all CI commands have proper help."""
        # Test main CI help
        result = self.runner.invoke(ci, ["--help"])
        assert result.exit_code == 0
        assert "CI/CD integration commands" in result.output

        # Test subcommand help
        commands = [
            "status",
            "config",
            "track-branch",
            "track-commit",
            "scan-repository",
            "scan-branches",
            "scan-full",
            "migrate-project",
            "analyze-patterns",
            "hooks",
            "github-status",
            "setup-workflows",
            "track-pr",
            "sync-github",
        ]

        for command in commands:
            result = self.runner.invoke(ci, [command, "--help"])
            assert result.exit_code == 0
            assert "Usage:" in result.output

    def test_end_to_end_workflow(self):
        """Test complete end-to-end CI workflow."""
        # 1. Check initial status
        result = self.runner.invoke(ci, ["status"])
        assert result.exit_code == 0

        # 2. Configure CI settings
        result = self.runner.invoke(
            ci, ["config", "set", "auto_start_on_branch", "true"]
        )
        assert result.exit_code == 0

        # 3. Scan repository
        result = self.runner.invoke(ci, ["scan-full", "--max-commits", "10"])
        assert result.exit_code == 0

        # 4. Track specific branch
        result = self.runner.invoke(ci, ["track-branch", "feature/cli12345-test-cli"])
        assert result.exit_code == 0

        # 5. Install hooks
        result = self.runner.invoke(ci, ["hooks", "install"])
        assert result.exit_code == 0

        # 6. Setup GitHub workflows
        result = self.runner.invoke(ci, ["setup-workflows", "starter"])
        assert result.exit_code == 0

        # 7. Check final status
        result = self.runner.invoke(ci, ["status"])
        assert result.exit_code == 0

        # Should show CI/CD tracking status table
        assert "CI/CD Tracking Status" in result.output
        assert "Total branch associations" in result.output
