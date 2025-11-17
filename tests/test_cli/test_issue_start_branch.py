from unittest.mock import Mock, patch

from roadmap.cli import main


def test_start_issue_creates_branch(cli_runner):
    runner = cli_runner
    with runner.isolated_filesystem():
        # Prepare a fake core and git helper
        fake_issue = Mock()
        fake_issue.id = "abc12345"
        fake_issue.title = "Test Issue"

        class DummyGit:
            def __init__(self):
                pass

            def is_git_repository(self):
                return True

            def create_branch_for_issue(self, issue, checkout=True):
                assert issue == fake_issue
                return True

            def suggest_branch_name(self, issue):
                return "feature/abc12345-test-issue"

        dummy_git = DummyGit()

        # Patch RoadmapCore in both the issue module and the main CLI so
        # the created ctx.obj['core'] uses our mocked instance
        with patch("roadmap.cli.RoadmapCore") as MockCoreMain:
            core_inst = MockCoreMain.return_value
            core_inst.is_initialized.return_value = True
            core_inst.get_issue.return_value = fake_issue
            core_inst.update_issue.return_value = True
            core_inst.git = dummy_git

            result = runner.invoke(
                main,
                [
                    "issue",
                    "start",
                    fake_issue.id,
                    "--git-branch",
                    "--no-checkout",
                ],
            )

            assert result.exit_code == 0
            assert (
                "Created Git branch" in result.output
                or "Not in a Git repository" in result.output
            )
