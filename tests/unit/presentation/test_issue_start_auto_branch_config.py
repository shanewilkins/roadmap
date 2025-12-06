from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from roadmap.adapters.cli import main

pytestmark = pytest.mark.skip(
    reason="CLI command integration tests - complex Click mocking"
)


def test_start_issue_respects_config_auto_branch(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        # Create .roadmap/config.yaml with auto_branch: true
        Path(".roadmap").mkdir()
        config = {"defaults": {"auto_branch": True}}
        with open(".roadmap/config.yaml", "w") as f:
            yaml.dump(config, f)

        fake_issue = Mock()
        fake_issue.id = "abc12345"
        fake_issue.title = "Test Issue"

        class DummyGit:
            def is_git_repository(self):
                return True

            def create_branch_for_issue(self, issue, checkout=True):
                assert issue == fake_issue
                return True

            def suggest_branch_name(self, issue):
                return "feature/abc12345-test-issue"

        dummy_git = DummyGit()

        with patch("roadmap.cli.RoadmapCore") as MockCoreMain:
            core_inst = MockCoreMain.return_value
            core_inst.is_initialized.return_value = True
            core_inst.get_issue.return_value = fake_issue
            core_inst.update_issue.return_value = True
            # Ensure the mocked core points to the real config file we created
            core_inst.config_file = Path(".roadmap/config.yaml")
            core_inst.git = dummy_git

            result = runner.invoke(
                main,
                [
                    "issue",
                    "start",
                    fake_issue.id,
                ],
            )

            assert result.exit_code == 0
            assert (
                "Created Git branch" in result.output
                or "Checked out branch" in result.output
            )
