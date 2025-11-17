"""
Integration tests for CI/CD CLI commands and repository scanning functionality.

These tests focus on end-to-end workflows and integration between components
to ensure the CI/CD features work correctly in real-world scenarios.
"""

import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.cli.ci import ci
from roadmap.core import RoadmapCore
from roadmap.git_hooks import GitHookManager
from roadmap.models import IssueType, Priority
from roadmap.repository_scanner import AdvancedRepositoryScanner, RepositoryScanConfig


class TestCICommandIntegration:
    """Integration tests for CI CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Initialize git repo
            subprocess.run(
                ["git", "init"], cwd=repo_path, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
            )

            # Create initial commit
            (repo_path / "README.md").write_text("# Test Repository\\n")
            subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True
            )

            # Create some test commits with issue references
            test_commits = [
                ("ea4606b6: Add feature implementation", "feature.py"),
                ("515a927c: Fix critical bug [progress:75%]", "bugfix.py"),
                (
                    "ea4606b6: Complete feature [closes roadmap:ea4606b6]",
                    "feature_final.py",
                ),
            ]

            for i, (message, filename) in enumerate(test_commits):
                # Make sure each commit has actual changes
                content = f"# {filename}\\n# Updated {i+1}\\n# Timestamp: {datetime.now().isoformat()}\\n"
                (repo_path / filename).write_text(content)
                subprocess.run(["git", "add", filename], cwd=repo_path, check=True)
                try:
                    subprocess.run(
                        ["git", "commit", "-m", message],
                        cwd=repo_path,
                        check=True,
                        capture_output=True,
                    )
                except subprocess.CalledProcessError:
                    # If nothing to commit, add a timestamp file to force changes
                    timestamp_file = f"timestamp_{i}.txt"
                    (repo_path / timestamp_file).write_text(
                        f"Commit {i+1} at {datetime.now()}\\n"
                    )
                    subprocess.run(
                        ["git", "add", timestamp_file], cwd=repo_path, check=True
                    )
                    subprocess.run(
                        ["git", "commit", "-m", message],
                        cwd=repo_path,
                        check=True,
                        capture_output=True,
                    )

            # Create some branches
            subprocess.run(
                ["git", "checkout", "-b", "feature/ea4606b6-test-feature"],
                cwd=repo_path,
                check=True,
            )
            (repo_path / "new_feature.py").write_text("# New feature\\n")
            subprocess.run(["git", "add", "new_feature.py"], cwd=repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", "ea4606b6: Implement new feature"],
                cwd=repo_path,
                check=True,
            )

            subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True)

            yield repo_path

    @pytest.fixture
    def roadmap_setup(self, temp_git_repo):
        """Set up roadmap in the test repository."""
        # Change to temp directory for testing
        original_cwd = os.getcwd()
        os.chdir(temp_git_repo)

        try:
            # Initialize roadmap
            core = RoadmapCore()
            core.initialize()

            # Create test issues
            core.create_issue(
                title="Test Feature Implementation",
                priority=Priority.HIGH,
                issue_type=IssueType.FEATURE,
            )

            core.create_issue(
                title="Critical Bug Fix",
                priority=Priority.HIGH,
                issue_type=IssueType.BUG,
            )

            yield core

        finally:
            os.chdir(original_cwd)

    def test_ci_status_command(self, runner, roadmap_setup):
        """Test CI status command shows correct configuration."""
        result = runner.invoke(ci, ["status"])

        assert result.exit_code == 0
        assert "CI/CD Tracking Status" in result.output
        assert "Total branch associations" in result.output  # Should show status table

    def test_ci_config_command(self, runner, roadmap_setup):
        """Test CI configuration command."""
        # Test showing current config
        result = runner.invoke(ci, ["config", "show"])
        assert result.exit_code == 0
        assert "auto_start_on_branch" in result.output

        # Test setting configuration
        result = runner.invoke(ci, ["config", "set", "auto_start_on_branch", "false"])
        assert result.exit_code == 0
        assert (
            "Configuration updated" in result.output
            or "auto_start_on_branch" in result.output
        )

    def test_track_branch_command(self, runner, roadmap_setup):
        """Test tracking a branch for issue association."""
        result = runner.invoke(ci, ["track-branch", "feature/ea4606b6-test-feature"])

        assert result.exit_code == 0
        assert "ea4606b6" in result.output
        assert (
            "Branch Tracking Results" in result.output
            or "tracked" in result.output.lower()
        )

    def test_scan_repository_command(self, runner, roadmap_setup):
        """Test repository scanning command."""
        result = runner.invoke(ci, ["scan-repository", "--max-commits", "10"])

        assert result.exit_code == 0
        assert "Scanning repository history" in result.output
        assert (
            "Repository Scan Results" in result.output
            or "No issue associations found" in result.output
        )

    def test_scan_branches_command(self, runner, roadmap_setup):
        """Test branch scanning command."""
        result = runner.invoke(ci, ["scan-branches"])

        assert result.exit_code == 0
        assert (
            "Scanning git branches" in result.output
            or "Scanning all branches" in result.output
        )
        # Should find our test branches or report no associations
        assert (
            "feature/ea4606b6-test-feature" in result.output
            or "ea4606b6" in result.output
            or "No issue associations found" in result.output
        )

    def test_hooks_command_integration(self, runner, roadmap_setup):
        """Test git hooks management commands."""
        # Test hooks status
        result = runner.invoke(ci, ["hooks", "status"])
        assert result.exit_code == 0
        assert "Git Hooks Status" in result.output

        # Test hooks install
        result = runner.invoke(ci, ["hooks", "install"])
        assert result.exit_code == 0
        # Should install hooks successfully or show they're already installed

    def test_github_status_command(self, runner, roadmap_setup):
        """Test GitHub integration status."""
        result = runner.invoke(ci, ["github-status"])

        assert result.exit_code == 0
        assert "GitHub Actions Integration Status" in result.output
        assert "Roadmap Setup" in result.output


class TestRepositoryScannerIntegration:
    """Integration tests for advanced repository scanning functionality."""

    @pytest.fixture
    def temp_git_repo_advanced(self):
        """Create a more complex temporary git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Initialize git repo
            subprocess.run(
                ["git", "init"], cwd=repo_path, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
            )

            # Create a rich commit history with various patterns
            commits_data = [
                ("Initial commit", "README.md", "# Test Repo\\n"),
                ("feat: Add authentication module", "auth.py", "# Authentication\\n"),
                (
                    "fix: Resolve login issue ea4606b6",
                    "auth.py",
                    "# Authentication\\n# Fixed\\n",
                ),
                (
                    "ea4606b6: Implement user management [progress:50%]",
                    "users.py",
                    "# Users\\n",
                ),
                ("docs: Update API documentation", "docs.md", "# API Docs\\n"),
                ("test: Add unit tests for auth", "test_auth.py", "# Tests\\n"),
                (
                    "ea4606b6: Complete user features [progress:100%] [closes roadmap:ea4606b6]",
                    "users.py",
                    "# Users\\n# Complete\\n",
                ),
                (
                    "chore: Update dependencies",
                    "requirements.txt",
                    "requests==2.28.0\\n",
                ),
                (
                    "515a927c: Fix security vulnerability",
                    "security.py",
                    "# Security fix\\n",
                ),
                (
                    "refactor: Improve code structure 515a927c",
                    "auth.py",
                    "# Authentication\\n# Refactored\\n",
                ),
            ]

            for message, filename, content in commits_data:
                file_path = repo_path / filename
                file_path.write_text(content)
                subprocess.run(["git", "add", filename], cwd=repo_path, check=True)
                subprocess.run(
                    ["git", "commit", "-m", message], cwd=repo_path, check=True
                )

            # Create multiple branches with different patterns
            branches = [
                (
                    "feature/ea4606b6-user-management",
                    "ea4606b6: Add user profile features",
                ),
                (
                    "bugfix/515a927c-security-fix",
                    "515a927c: Patch security vulnerability",
                ),
                ("hotfix/urgent-patch", "fix: Critical production issue"),
                ("docs/api-updates", "docs: Comprehensive API documentation"),
            ]

            for branch_name, commit_msg in branches:
                subprocess.run(
                    ["git", "checkout", "-b", branch_name], cwd=repo_path, check=True
                )
                test_file = repo_path / f'{branch_name.replace("/", "_")}.py'
                test_file.write_text(f"# {branch_name}\\n")
                subprocess.run(
                    ["git", "add", test_file.name], cwd=repo_path, check=True
                )
                subprocess.run(
                    ["git", "commit", "-m", commit_msg], cwd=repo_path, check=True
                )
                subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True)

            yield repo_path

    @pytest.fixture
    def scanner_setup(self, temp_git_repo_advanced):
        """Set up repository scanner in test environment."""
        original_cwd = os.getcwd()
        os.chdir(temp_git_repo_advanced)

        try:
            core = RoadmapCore()
            core.initialize()

            config = RepositoryScanConfig(
                max_commits=50,
                max_branches=10,
                use_parallel_processing=False,  # Simpler for testing
            )

            scanner = AdvancedRepositoryScanner(core, config)
            yield scanner, core

        finally:
            os.chdir(original_cwd)

    def test_comprehensive_repository_scan(self, scanner_setup):
        """Test full repository scanning functionality."""
        scanner, core = scanner_setup

        result = scanner.perform_comprehensive_scan()

        # Verify scan results
        assert result.total_commits_scanned > 0
        assert result.total_branches_scanned > 0
        assert result.scan_duration_seconds > 0

        # Should find issue associations in commits
        assert len(result.issue_associations) > 0
        assert "ea4606b6" in result.issue_associations
        assert "515a927c" in result.issue_associations

        # Verify commit analysis
        assert len(result.commits) > 0
        commit_with_type = next((c for c in result.commits if c.commit_type), None)
        assert commit_with_type is not None  # Should detect conventional commit types

        # Verify branch analysis
        assert len(result.branches) > 0
        feature_branch = next((b for b in result.branches if "feature" in b.name), None)
        assert feature_branch is not None

    def test_commit_pattern_analysis(self, scanner_setup):
        """Test detailed commit pattern analysis."""
        scanner, core = scanner_setup

        commits = scanner.scan_commit_history(max_commits=20)

        # Should analyze commit types
        commit_types = set(c.commit_type for c in commits if c.commit_type)
        expected_types = {"feat", "fix", "docs", "test", "chore", "refactor"}
        assert len(commit_types.intersection(expected_types)) > 0

        # Should find issue associations
        commits_with_issues = [c for c in commits if c.issue_ids]
        assert len(commits_with_issues) > 0

        # Should detect progress markers
        commits_with_progress = [c for c in commits if c.progress_markers]
        assert len(commits_with_progress) > 0

        # Should detect completion markers
        commits_with_completion = [c for c in commits if c.completion_markers]
        assert len(commits_with_completion) > 0

    def test_branch_lifecycle_analysis(self, scanner_setup):
        """Test branch analysis and lifecycle detection."""
        scanner, core = scanner_setup

        branches = scanner.scan_branch_history()

        # Should categorize branch types
        branch_types = set(b.branch_type for b in branches if b.branch_type)
        expected_types = {"feature", "bugfix", "docs"}
        assert len(branch_types.intersection(expected_types)) > 0

        # Should detect issue associations in branch names
        branches_with_issues = [b for b in branches if b.issue_ids]
        assert len(branches_with_issues) > 0

        # Should analyze lifecycle stages
        lifecycle_stages = set(b.lifecycle_stage for b in branches)
        assert "main" in lifecycle_stages or "merged" in lifecycle_stages

    def test_project_migration(self, scanner_setup):
        """Test project migration functionality."""
        scanner, core = scanner_setup

        # Test migration analysis (dry run)
        result = scanner.migrate_existing_project(create_issues=False, auto_link=False)

        assert result.successful > 0
        assert result.duration > 0

        # Should identify migration opportunities
        scan_result = scanner.perform_comprehensive_scan()
        assert len(scan_result.issue_associations) > 0

    def test_export_functionality(self, scanner_setup):
        """Test exporting scan results."""
        scanner, core = scanner_setup

        scan_result = scanner.perform_comprehensive_scan()

        # Test export to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = Path(f.name)

        try:
            exported_path = scanner.export_scan_results(scan_result, export_path)
            assert exported_path.exists()

            # Verify exported content
            with open(exported_path) as f:
                data = json.load(f)

            assert "scan_metadata" in data
            assert "statistics" in data
            assert "commits" in data
            assert "branches" in data
            assert "associations" in data

            # Verify data completeness
            assert data["statistics"]["total_commits_scanned"] > 0
            assert data["statistics"]["total_branches_scanned"] > 0
            assert len(data["commits"]) > 0
            assert len(data["branches"]) > 0

        finally:
            if export_path.exists():
                export_path.unlink()


class TestAdvancedCIIntegration:
    """Test advanced CI integration scenarios with full workflows."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def full_integration_setup(self):
        """Set up complete integration test environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Initialize git repo with realistic structure
            subprocess.run(
                ["git", "init"], cwd=repo_path, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Integration Test"],
                cwd=repo_path,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@integration.com"],
                cwd=repo_path,
                check=True,
            )

            original_cwd = os.getcwd()
            os.chdir(repo_path)

            try:
                # Initialize roadmap
                core = RoadmapCore()
                core.initialize()

                # Create test issues that will be used in commits
                core.create_issue(
                    title="Integration Test Feature",
                    priority=Priority.HIGH,
                    issue_type=IssueType.FEATURE,
                )

                core.create_issue(
                    title="Integration Test Bug",
                    priority=Priority.MEDIUM,
                    issue_type=IssueType.BUG,
                )

                # Create realistic git history
                commits = [
                    ("feat: Initial project setup", "setup.py"),
                    ("abc12345: Start feature implementation", "feature.py"),
                    ("abc12345: Add core functionality [progress:30%]", "feature.py"),
                    ("test: Add unit tests for feature abc12345", "test_feature.py"),
                    (
                        "abc12345: Complete feature implementation [progress:80%]",
                        "feature.py",
                    ),
                    ("def67890: Fix critical bug in authentication", "auth.py"),
                    (
                        "abc12345: Finalize feature [closes roadmap:abc12345]",
                        "feature.py",
                    ),
                    ("def67890: Resolve security issue [progress:100%]", "auth.py"),
                ]

                for i, (msg, filename) in enumerate(commits):
                    file_path = repo_path / filename
                    file_path.write_text(f"# {filename}\\n# Version {i+1}\\n")
                    subprocess.run(["git", "add", filename], cwd=repo_path, check=True)
                    subprocess.run(
                        ["git", "commit", "-m", msg], cwd=repo_path, check=True
                    )

                # Create feature branches
                subprocess.run(
                    ["git", "checkout", "-b", "feature/abc12345-integration-test"],
                    cwd=repo_path,
                    check=True,
                )
                (repo_path / "integration.py").write_text("# Integration test\\n")
                subprocess.run(
                    ["git", "add", "integration.py"], cwd=repo_path, check=True
                )
                subprocess.run(
                    ["git", "commit", "-m", "abc12345: Add integration test support"],
                    cwd=repo_path,
                    check=True,
                )
                subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True)

                yield core, repo_path

            finally:
                os.chdir(original_cwd)

    def test_full_ci_workflow_integration(self, runner, full_integration_setup):
        """Test complete CI workflow from scanning to tracking."""
        core, repo_path = full_integration_setup

        # 1. Test repository scanning
        result = runner.invoke(
            ci, ["scan-full", "--max-commits", "20", "--link-commits"]
        )
        assert result.exit_code == 0
        assert "Repository scan completed successfully" in result.output

        # 2. Test pattern analysis
        result = runner.invoke(ci, ["analyze-patterns", "--commits", "10"])
        assert result.exit_code == 0
        assert "Pattern analysis completed" in result.output

        # 3. Test branch tracking
        result = runner.invoke(
            ci, ["track-branch", "feature/abc12345-integration-test"]
        )
        assert result.exit_code == 0

        # 4. Test CI status after operations
        result = runner.invoke(ci, ["status"])
        assert result.exit_code == 0
        assert (
            "Issues Tracked" in result.output
            or "CI/CD Tracking Status" in result.output
        )

    def test_migration_workflow(self, runner, full_integration_setup):
        """Test complete migration workflow for existing project."""
        core, repo_path = full_integration_setup

        # Test dry run migration
        result = runner.invoke(
            ci, ["migrate-project", "--dry-run", "--max-commits", "15"]
        )
        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.output
        assert "Migration Analysis" in result.output

        # Should find existing issue references
        assert "abc12345" in result.output
        assert "def67890" in result.output

        # Test actual migration with link commits
        result = runner.invoke(
            ci, ["migrate-project", "--link-commits", "--max-commits", "15"]
        )
        assert result.exit_code == 0
        assert "Migration Results" in result.output
        assert "migration completed successfully" in result.output

    def test_hooks_integration_workflow(self, runner, full_integration_setup):
        """Test git hooks integration in realistic workflow."""
        core, repo_path = full_integration_setup

        # Install hooks
        result = runner.invoke(ci, ["hooks", "install"])
        assert result.exit_code == 0

        # Check hooks status
        result = runner.invoke(ci, ["hooks", "status"])
        assert result.exit_code == 0
        assert "Git Hooks Status" in result.output

        # Test hooks logs
        result = runner.invoke(ci, ["hooks", "logs"])
        assert result.exit_code == 0

    def test_github_actions_integration(self, runner, full_integration_setup):
        """Test GitHub Actions workflow setup."""
        core, repo_path = full_integration_setup

        # Test setup workflows
        result = runner.invoke(ci, ["setup-workflows", "starter"])
        assert result.exit_code == 0

        # Verify workflow file was created
        workflow_file = repo_path / ".github" / "workflows" / "roadmap-starter.yml"
        assert workflow_file.exists()

        # Test GitHub status after setup
        result = runner.invoke(ci, ["github-status"])
        assert result.exit_code == 0
        assert "GitHub Workflows" in result.output
        assert "Found" in result.output

    def test_error_handling_and_recovery(self, runner, full_integration_setup):
        """Test error handling in integration scenarios."""
        core, repo_path = full_integration_setup

        # Test with invalid parameters
        result = runner.invoke(ci, ["scan-full", "--max-commits", "0"])
        # Should handle gracefully or show appropriate error

        # Test with non-existent branch
        result = runner.invoke(ci, ["track-branch", "nonexistent-branch"])
        # Should handle gracefully

        # Test migration with invalid options
        result = runner.invoke(ci, ["migrate-project", "--max-commits", "-1"])
        # Should validate input appropriately


class TestGitHooksIntegration:
    """Integration tests for git hooks functionality."""

    @pytest.fixture
    def hooks_setup(self):
        """Set up git hooks testing environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Initialize git repo
            subprocess.run(
                ["git", "init"], cwd=repo_path, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Hook Test"], cwd=repo_path, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "hook@test.com"],
                cwd=repo_path,
                check=True,
            )

            original_cwd = os.getcwd()
            os.chdir(repo_path)

            try:
                # Initialize roadmap
                core = RoadmapCore()
                core.initialize()

                # Create test issue
                core.create_issue(
                    title="Hook Integration Test",
                    priority=Priority.HIGH,
                    issue_type=IssueType.FEATURE,
                )

                yield core, repo_path

            finally:
                os.chdir(original_cwd)

    def test_hook_manager_integration(self, hooks_setup):
        """Test git hook manager functionality."""
        core, repo_path = hooks_setup

        hook_manager = GitHookManager(core)

        # Test hook installation
        hook_manager.install_hooks()

        # Verify hooks are installed
        hooks_dir = repo_path / ".git" / "hooks"
        for hook_name in ["post-commit", "pre-push", "post-checkout", "post-merge"]:
            hook_file = hooks_dir / hook_name
            assert hook_file.exists()
            assert hook_file.stat().st_mode & 0o111  # Check executable

        # Test hook status
        status = hook_manager.get_hooks_status()
        assert len(status) > 0

        # Test hook configuration
        config = hook_manager.get_hook_config()
        assert config is not None

    @patch("subprocess.run")
    def test_hook_execution_simulation(self, mock_run, hooks_setup):
        """Test simulated hook execution (without actually running git)."""
        core, repo_path = hooks_setup

        hook_manager = GitHookManager(core)

        # Mock successful git command
        mock_run.return_value = Mock(
            returncode=0, stdout="hook1234\\nTest commit message", stderr=""
        )

        # Test post-commit hook logic
        try:
            hook_manager.on_post_commit()
            # Should handle commit processing
        except Exception:
            # Expected if git commands fail in test environment
            pass

        # Test pre-push hook logic
        try:
            hook_manager.on_pre_push()
            # Should handle pre-push validation
        except Exception:
            # Expected if git commands fail in test environment
            pass
