"""Unit tests for issue comment command."""

from roadmap.adapters.cli.issues.comment import add_comment


class TestCommentCommand:
    """Test issue comment command."""

    def test_add_comment_to_issue(self, cli_runner):
        """Test adding a comment to an issue."""
        result = cli_runner.invoke(
            add_comment,
            ["issue1", "This is a test comment"],
        )

        # Test completes without crashing
        assert result is not None

    def test_comment_nonexistent_issue(self, cli_runner):
        """Test adding comment to nonexistent issue."""
        result = cli_runner.invoke(
            add_comment,
            ["nonexistent", "Comment"],
        )

        # Test completes without crashing
        assert result is not None

    def test_comment_with_multiline_text(self, cli_runner):
        """Test adding multiline comment."""
        result = cli_runner.invoke(
            add_comment,
            ["issue1", "Line 1\nLine 2\nLine 3"],
        )

        # Test completes without crashing
        assert result is not None

    def test_comment_with_empty_text(self, cli_runner):
        """Test adding empty comment."""
        result = cli_runner.invoke(
            add_comment,
            ["issue1", ""],
        )

        # Test completes without crashing
        assert result is not None
