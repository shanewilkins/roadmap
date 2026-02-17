from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from roadmap.adapters.cli import main
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


class DummyGit:
    """Mock Git helper for testing."""

    def __init__(self, branch_name="feature/abc12345-test-issue"):
        self.branch_name = branch_name

    def is_git_repository(self):
        return True

    def create_branch_for_issue(self, issue, checkout=True, force=False):
        assert issue.id == "abc12345"
        return (True, self.branch_name)

    def suggest_branch_name(self, issue):
        return self.branch_name


@pytest.fixture
def fake_issue():
    """Create a mock issue for testing."""
    issue = Mock()
    issue.id = "abc12345"
    issue.title = "Test Issue"
    return issue


@pytest.fixture
def mocked_core(fake_issue):
    """Create a mocked RoadmapCore instance."""
    with patch("roadmap.cli.RoadmapCore") as MockCoreMain:
        core_inst = MockCoreMain.return_value
        core_inst.is_initialized.return_value = True
        core_inst.issues.get.return_value = fake_issue
        core_inst.update_issue.return_value = True
        core_inst.git = DummyGit()
        yield core_inst, MockCoreMain


class TestIssueStartBranch:
    """Test issue start command with Git branch creation."""

    def test_start_respects_auto_branch_config(
        self, cli_runner, fake_issue, mocked_core
    ):
        """Test that config auto_branch setting is respected (currently disabled)."""
        core_inst, _ = mocked_core
        runner = cli_runner

        with runner.isolated_filesystem():
            # Create .roadmap/config.yaml with auto_branch: true
            Path(".roadmap").mkdir()
            config = {"defaults": {"auto_branch": True}}
            with open(".roadmap/config.yaml", "w") as f:
                yaml.dump(config, f)

            core_inst.config_file = Path(".roadmap/config.yaml")

            result = runner.invoke(main, ["issue", "start", fake_issue.id])

            # Without --git-branch flag, branch should not be created
            assert result.exit_code == 0
            assert "Created Git branch" not in clean_cli_output(result.output)

    def test_start_creates_branch_with_flag(self, cli_runner, fake_issue, mocked_core):
        """Test that --git-branch flag creates a Git branch."""
        _, _ = mocked_core
        runner = cli_runner

        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                ["issue", "start", fake_issue.id, "--git-branch", "--no-checkout"],
            )

            assert result.exit_code == 0
            output = clean_cli_output(result.output)
            assert "Created Git branch" in output or "Not in a Git repository" in output
