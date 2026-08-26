"""CLI issue journeys through the composed application boundary."""

import pytest

from roadmap.bootstrap import cli as main
from tests.fixtures.ansi import clean_cli_output
from tests.fixtures.integration_helpers import IntegrationTestBase


def _issues():
    return IntegrationTestBase.get_roadmap_core().issues.list()


def _created_issue_id(cli_runner, *, title: str = "Test Issue") -> str:
    IntegrationTestBase.create_issue(cli_runner, title=title)
    issues = _issues()
    assert issues, "issue fixture did not persist an issue"
    return str(issues[-1].id)


def _issue(issue_id: str):
    issue = IntegrationTestBase.get_roadmap_core().issues.get(issue_id)
    assert issue is not None, f"issue {issue_id} was not persisted"
    return issue


class TestCLIIssueCreate:
    @pytest.mark.parametrize(
        "title,options",
        [
            ("Test Issue", []),
            (
                "Feature Request",
                ["--type", "feature", "--priority", "high", "--estimate", "4.5"],
            ),
            ("Bug Report", ["--type", "bug"]),
            ("Task", ["--priority", "medium"]),
        ],
    )
    def test_create_issue(self, cli_runner, title, options):
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)
            result = cli_runner.invoke(
                main, ["issue", "create", "--title", title, *options]
            )
            IntegrationTestBase.assert_cli_success(result)
            assert any(str(issue.title) == title for issue in _issues())

    def test_create_issue_help(self, cli_runner):
        result = cli_runner.invoke(main, ["issue", "create", "--help"])
        IntegrationTestBase.assert_cli_success(result)
        output = clean_cli_output(result.output).lower()
        assert "create" in output
        assert "title" in output


class TestCLIIssueList:
    @pytest.mark.parametrize(
        "filter_args",
        [[], ["--status", "todo"], ["--priority", "high"]],
    )
    def test_list_issues(self, cli_runner, filter_args):
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)
            IntegrationTestBase.create_issue(
                cli_runner, title="High Priority Issue", priority="high"
            )
            result = cli_runner.invoke(main, ["issue", "list", *filter_args])
            IntegrationTestBase.assert_cli_success(result)
            assert "High Priority Issue" in clean_cli_output(result.output)

    def test_list_issues_empty(self, cli_runner):
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)
            result = cli_runner.invoke(main, ["issue", "list"])
            IntegrationTestBase.assert_cli_success(result)
            assert not _issues()

    def test_list_issues_help(self, cli_runner):
        result = cli_runner.invoke(main, ["issue", "list", "--help"])
        IntegrationTestBase.assert_cli_success(result)


class TestCLIIssueUpdate:
    @pytest.mark.parametrize(
        "option,value,attribute,expected",
        [
            ("--title", "Updated Title", "title", "Updated Title"),
            ("--priority", "critical", "priority", "critical"),
            ("--status", "in-progress", "status", "in-progress"),
        ],
    )
    def test_update_issue(self, cli_runner, option, value, attribute, expected):
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)
            issue_id = _created_issue_id(cli_runner)
            result = cli_runner.invoke(
                main, ["issue", "update", issue_id, option, value]
            )
            IntegrationTestBase.assert_cli_success(result)
            actual = getattr(_issue(issue_id), attribute)
            assert getattr(actual, "value", str(actual)) == expected

    def test_update_nonexistent_issue_fails(self, cli_runner):
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)
            result = cli_runner.invoke(
                main, ["issue", "update", "999", "--title", "Test"]
            )
            assert result.exit_code != 0
            assert "not found" in result.output.lower()


class TestCLIIssueDelete:
    @pytest.mark.parametrize("use_yes", [False, True])
    def test_delete_archived_issue(self, cli_runner, use_yes):
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)
            issue_id = _created_issue_id(cli_runner)
            archived = cli_runner.invoke(
                main, ["issue", "archive", issue_id, "--force"]
            )
            IntegrationTestBase.assert_cli_success(archived)
            args = ["issue", "delete", issue_id, *(["--yes"] if use_yes else [])]
            result = cli_runner.invoke(main, args, input=None if use_yes else "y\n")
            IntegrationTestBase.assert_cli_success(result)
            assert "deleted" in clean_cli_output(result.output).lower()

    def test_delete_nonexistent_issue_fails(self, cli_runner):
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)
            result = cli_runner.invoke(main, ["issue", "delete", "999", "--yes"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()


class TestCLIIssueWorkflow:
    def test_start_close_and_progress(self, cli_runner):
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)
            issue_id = _created_issue_id(cli_runner)
            started = cli_runner.invoke(main, ["issue", "start", issue_id])
            IntegrationTestBase.assert_cli_success(started)
            assert _issue(issue_id).status.value == "in-progress"

            progressed = cli_runner.invoke(main, ["issue", "progress", issue_id, "50"])
            IntegrationTestBase.assert_cli_success(progressed)
            assert _issue(issue_id).progress_percentage == 50

            closed = cli_runner.invoke(main, ["issue", "close", issue_id])
            IntegrationTestBase.assert_cli_success(closed)
            issue = _issue(issue_id)
            assert issue.status.value == "closed"
            assert issue.progress_percentage == 100

    def test_block_and_unblock(self, cli_runner):
        with cli_runner.isolated_filesystem():
            IntegrationTestBase.init_roadmap(cli_runner)
            issue_id = _created_issue_id(cli_runner)
            blocked = cli_runner.invoke(
                main,
                ["issue", "block", issue_id, "--reason", "Waiting for dependency"],
            )
            IntegrationTestBase.assert_cli_success(blocked)
            assert _issue(issue_id).status.value == "blocked"

            unblocked = cli_runner.invoke(main, ["issue", "unblock", issue_id])
            IntegrationTestBase.assert_cli_success(unblocked)
            assert _issue(issue_id).status.value == "in-progress"


class TestCLIIssueHelp:
    def test_issue_group_help(self, cli_runner):
        result = cli_runner.invoke(main, ["issue", "--help"])
        IntegrationTestBase.assert_cli_success(result)
        output = clean_cli_output(result.output).lower()
        assert "issue" in output
        assert "create" in output
        assert "list" in output

    @pytest.mark.parametrize(
        "subcommand",
        [
            "create",
            "list",
            "update",
            "delete",
            "start",
            "close",
            "progress",
            "block",
            "unblock",
            "deps",
        ],
    )
    def test_issue_subcommand_help(self, cli_runner, subcommand):
        result = cli_runner.invoke(main, ["issue", subcommand, "--help"])
        IntegrationTestBase.assert_cli_success(result)
