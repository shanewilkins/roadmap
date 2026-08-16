"""Unit tests for issue comment command."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.issues.comment import add_comment
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


class TestCommentCommand:
    """Test issue comment command."""

    def test_add_comment_success_uses_system_user(
        self, cli_runner, mock_core_initialized
    ):
        """Add comment should resolve default author and persist comments."""
        issue = Issue(id="iss-1", title="Issue title")
        issue.comments = []
        comment = Comment(
            id=101,
            issue_id="iss-1",
            author="alice",
            body="Looks good",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch(
                "roadmap.adapters.cli.issues.comment.ensure_entity_exists",
                return_value=issue,
            ),
            patch("getpass.getuser", return_value="alice") as mock_getuser,
            patch(
                "roadmap.adapters.cli.issues.comment.CommentService.create_comment",
                return_value=comment,
            ) as mock_create,
            patch("roadmap.adapters.cli.issues.comment.get_console") as mock_console,
        ):
            console = MagicMock()
            mock_console.return_value = console
            result = cli_runner.invoke(
                add_comment,
                ["iss-1", "Looks good"],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 0
        mock_getuser.assert_called_once()
        mock_create.assert_called_once_with(
            author="alice",
            body="Looks good",
            entity_id="iss-1",
            in_reply_to=None,
        )
        mock_core_initialized.issues.update.assert_called_once_with(
            "iss-1", comments=[comment]
        )
        printed = "\n".join(str(call.args[0]) for call in console.print.call_args_list)
        assert "Comment added to issue iss-1" in printed
        assert "By: alice" in printed
        assert "ID: 101" in printed

    def test_add_comment_rejects_empty_body(self, cli_runner, mock_core_initialized):
        """Whitespace-only body should be rejected before comment creation."""
        issue = Issue(id="iss-empty", title="Issue title")

        with (
            patch(
                "roadmap.adapters.cli.issues.comment.ensure_entity_exists",
                return_value=issue,
            ),
            patch("roadmap.adapters.cli.issues.comment.get_console") as mock_console,
            patch(
                "roadmap.adapters.cli.issues.comment.CommentService.create_comment"
            ) as mock_create,
        ):
            console = MagicMock()
            mock_console.return_value = console
            result = cli_runner.invoke(
                add_comment,
                ["iss-empty", "   "],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 1
        mock_create.assert_not_called()
        mock_core_initialized.issues.update.assert_not_called()
        assert "cannot be empty" in clean_cli_output(result.output).lower()

    def test_add_comment_reply_target_missing_stops_before_update(
        self, cli_runner, mock_core_initialized
    ):
        """Reply should fail when requested parent comment is absent."""
        issue = Issue(id="iss-2", title="Issue title")
        issue.comments = [
            Comment(
                id=7,
                issue_id="iss-2",
                author="bob",
                body="existing",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]
        new_comment = Comment(
            id=8,
            issue_id="iss-2",
            author="bob",
            body="reply",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            in_reply_to=999,
        )

        with (
            patch(
                "roadmap.adapters.cli.issues.comment.ensure_entity_exists",
                return_value=issue,
            ),
            patch(
                "roadmap.adapters.cli.issues.comment.CommentService.create_comment",
                return_value=new_comment,
            ),
            patch("roadmap.adapters.cli.issues.comment.get_console") as mock_console,
        ):
            console = MagicMock()
            mock_console.return_value = console
            result = cli_runner.invoke(
                add_comment,
                ["iss-2", "reply", "--author", "bob", "--reply-to", "999"],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 1
        mock_core_initialized.issues.update.assert_not_called()
        assert "Cannot find comment 999" in clean_cli_output(result.output)

    def test_add_comment_create_failure_prints_error(
        self, cli_runner, mock_core_initialized
    ):
        """Comment creation exception should be handled and printed."""
        issue = Issue(id="iss-3", title="Issue title")

        with (
            patch(
                "roadmap.adapters.cli.issues.comment.ensure_entity_exists",
                return_value=issue,
            ),
            patch(
                "roadmap.adapters.cli.issues.comment.CommentService.create_comment",
                side_effect=RuntimeError("create failed"),
            ),
            patch("roadmap.adapters.cli.issues.comment.get_console") as mock_console,
        ):
            console = MagicMock()
            mock_console.return_value = console
            result = cli_runner.invoke(
                add_comment,
                ["iss-3", "message", "--author", "sue"],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 1
        mock_core_initialized.issues.update.assert_not_called()
        assert "Failed to create comment" in clean_cli_output(result.output)

    def test_add_comment_update_failure_prints_error(
        self, cli_runner, mock_core_initialized
    ):
        """Issue update exception should be handled and printed."""
        issue = Issue(id="iss-4", title="Issue title")
        comment = Comment(
            id=202,
            issue_id="iss-4",
            author="sam",
            body="body",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_core_initialized.issues.update.side_effect = RuntimeError("db down")

        with (
            patch(
                "roadmap.adapters.cli.issues.comment.ensure_entity_exists",
                return_value=issue,
            ),
            patch(
                "roadmap.adapters.cli.issues.comment.CommentService.create_comment",
                return_value=comment,
            ),
            patch("roadmap.adapters.cli.issues.comment.get_console") as mock_console,
        ):
            console = MagicMock()
            mock_console.return_value = console
            result = cli_runner.invoke(
                add_comment,
                ["iss-4", "body", "--author", "sam"],
                obj={"core": mock_core_initialized},
            )

        assert result.exit_code == 1
        assert mock_core_initialized.issues.update.call_count == 1
        assert "Failed to update issue" in clean_cli_output(result.output)
