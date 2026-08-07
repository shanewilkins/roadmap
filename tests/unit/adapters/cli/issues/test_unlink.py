"""Unit tests for issue unlink GitHub command."""

from unittest.mock import call, patch

from roadmap.adapters.cli.issues.unlink import unlink_github_issue
from roadmap.core.domain.issue import Issue


class TestUnlinkCommand:
    """Test issue unlink command."""

    def test_unlink_nonexistent_issue_prints_failure(
        self, cli_runner, mock_core_initialized
    ):
        """Command should format and print a not-found failure message."""
        mock_core_initialized.issues.get.return_value = None

        with (
            patch(
                "roadmap.adapters.cli.issues.unlink.format_operation_failure",
                return_value=["ERR: not found"],
            ) as mock_failure,
            patch("roadmap.adapters.cli.issues.unlink.console.print") as mock_print,
        ):
            result = cli_runner.invoke(
                unlink_github_issue,
                ["missing-id"],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 0
        mock_failure.assert_called_once_with(
            action="unlink",
            entity_id="missing-id",
            error="Issue not found",
        )
        mock_print.assert_called_once_with("ERR: not found", style="bold red")

    def test_unlink_not_linked_issue_prints_warning(
        self, cli_runner, mock_core_initialized
    ):
        """Command should stop early when issue has no GitHub link."""
        issue = Issue(id="abc123", title="Local only")
        issue.github_issue = None
        mock_core_initialized.issues.get.return_value = issue

        with patch("roadmap.adapters.cli.issues.unlink.console.print") as mock_print:
            result = cli_runner.invoke(
                unlink_github_issue,
                ["abc123"],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 0
        mock_print.assert_called_once()
        printed_msg = mock_print.call_args.args[0]
        assert "not linked to GitHub" in printed_msg
        assert mock_print.call_args.kwargs["style"] == "yellow"
        mock_core_initialized.issues.update.assert_not_called()

    def test_unlink_linked_issue_success_formats_details(
        self, cli_runner, mock_core_initialized
    ):
        """Command should update issue and print formatted success lines."""
        issue = Issue(id="issue-7", title="Linked issue")
        issue.github_issue = 42
        updated_issue = Issue(id="issue-7", title="Linked issue")

        mock_core_initialized.issues.get.return_value = issue
        mock_core_initialized.issues.update.return_value = updated_issue

        with (
            patch(
                "roadmap.adapters.cli.issues.unlink.format_operation_success",
                return_value=["✅ Unlinked", "details"],
            ) as mock_success,
            patch("roadmap.adapters.cli.issues.unlink.console.print") as mock_print,
        ):
            result = cli_runner.invoke(
                unlink_github_issue,
                ["issue-7"],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 0
        mock_core_initialized.issues.update.assert_called_once_with(
            "issue-7", github_issue=None
        )
        mock_success.assert_called_once()
        extra = mock_success.call_args.kwargs["extra_details"]
        assert extra["GitHub Issue"] == "#42"
        assert extra["Local Issue"] == "issue-7"
        assert call("✅ Unlinked", style="bold green") in mock_print.call_args_list
        assert call("details", style="cyan") in mock_print.call_args_list

    def test_unlink_update_failure_uses_operation_failure(
        self, cli_runner, mock_core_initialized
    ):
        """Command should print failure output when update returns falsy."""
        issue = Issue(id="issue-9", title="Linked issue")
        issue.github_issue = 99
        mock_core_initialized.issues.get.return_value = issue
        mock_core_initialized.issues.update.return_value = None

        with (
            patch(
                "roadmap.adapters.cli.issues.unlink.format_operation_failure",
                return_value=["ERR: update failed"],
            ) as mock_failure,
            patch("roadmap.adapters.cli.issues.unlink.console.print") as mock_print,
        ):
            result = cli_runner.invoke(
                unlink_github_issue,
                ["issue-9"],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 0
        mock_failure.assert_called_once_with(
            action="unlink",
            entity_id="issue-9",
            error="Failed to update issue",
        )
        mock_print.assert_called_once_with("ERR: update failed", style="bold red")

    def test_unlink_exception_calls_cli_error_handler(
        self, cli_runner, mock_core_initialized
    ):
        """Command should delegate unexpected errors to CLI error handler."""
        mock_core_initialized.issues.get.side_effect = RuntimeError("boom")

        with (
            patch("roadmap.adapters.cli.issues.unlink.handle_cli_error") as mock_handle,
            patch(
                "roadmap.adapters.cli.issues.unlink.format_operation_failure",
                return_value=["ERR: boom"],
            ) as mock_failure,
            patch("roadmap.adapters.cli.issues.unlink.console.print") as mock_print,
        ):
            result = cli_runner.invoke(
                unlink_github_issue,
                ["issue-err"],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 0
        mock_handle.assert_called_once()
        assert mock_handle.call_args.kwargs["operation"] == "unlink_github_issue"
        assert mock_handle.call_args.kwargs["fatal"] is True
        mock_failure.assert_called_once_with(
            action="unlink",
            entity_id="issue-err",
            error="boom",
        )
        mock_print.assert_called_once_with("ERR: boom", style="bold red")
