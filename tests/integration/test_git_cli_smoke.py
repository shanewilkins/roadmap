"""Smoke tests for Git integration CLI - verifies happy paths without output parsing.

These tests verify that Git integration commands complete successfully without
attempting to parse Rich console output (which is incompatible with xdist).
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.infrastructure.core import RoadmapCore


class TestGitIntegrationCLI:
    """Smoke tests for Git integration CLI commands."""

    def setUp(self):
        """Set up test environment with roadmap and git."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Initialize roadmap
        self.core = RoadmapCore()
        self.core.initialize()

        # Initialize git
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create initial commit
        test_file = Path("README.md")
        test_file.write_text("# Test Repository")
        subprocess.run(["git", "add", "README.md"], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.no_xdist
    def test_git_status_command(self):
        """Test git status command returns success."""
        self.setUp()
        try:
            runner = CliRunner()
            result = runner.invoke(main, ["git", "status"])

            # Verify command succeeds - don't parse output
            assert result.exit_code == 0, f"Command failed with code {result.exit_code}"
        finally:
            self.tearDown()

    @pytest.mark.no_xdist
    def test_issue_create_succeeds(self):
        """Test issue creation command succeeds and persists to database."""
        self.setUp()
        try:
            runner = CliRunner()

            # Create an issue
            result = runner.invoke(
                main, ["issue", "create", "Test Feature", "--type", "feature"]
            )
            assert result.exit_code == 0, "Issue creation failed"

            # Verify issue was saved to database
            issues = self.core.issues.list()
            assert len(issues) > 0, "Issue was not saved to database"
            assert any(issue.title == "Test Feature" for issue in issues)
        finally:
            self.tearDown()

    @pytest.mark.no_xdist
    def test_git_and_issue_integration(self):
        """Test that Git and issue operations work together."""
        self.setUp()
        try:
            runner = CliRunner()

            # Create an issue
            result = runner.invoke(
                main, ["issue", "create", "Test Issue", "--type", "feature"]
            )
            assert result.exit_code == 0

            # Verify git status still works
            result = runner.invoke(main, ["git", "status"])
            assert result.exit_code == 0

            # Verify issue was saved
            issues = self.core.issues.list()
            assert len(issues) > 0
        finally:
            self.tearDown()
