"""Error path tests for issue_status_helpers module.

Tests cover StatusChangeConfig, apply_status_change function,
pre-checks, and error handling.
"""

from unittest import mock

import click
import pytest

from roadmap.adapters.cli.issues.issue_status_helpers import (
    StatusChangeConfig,
    apply_status_change,
)
from roadmap.core.domain import Status


class TestStatusChangeConfig:
    """Test StatusChangeConfig dataclass."""

    def test_config_initialization(self):
        """Test StatusChangeConfig initializes correctly."""
        config = StatusChangeConfig(
            status=Status.BLOCKED,
            emoji="🚫",
            title_verb="Blocked",
            title_style="bold red",
            status_display="🚫 Blocked",
        )
        assert config.status == Status.BLOCKED
        assert config.emoji == "🚫"
        assert config.title_verb == "Blocked"
        assert config.title_style == "bold red"
        assert config.status_display == "🚫 Blocked"
        assert config.pre_check is None

    def test_config_with_pre_check(self):
        """Test StatusChangeConfig with pre_check function."""

        def check_fn(issue):
            return True, None

        config = StatusChangeConfig(
            status=Status.CLOSED,
            emoji="✅",
            title_verb="Closed",
            title_style="bold green",
            status_display="✅ Closed",
            pre_check=check_fn,
        )
        assert config.pre_check is not None
        assert config.pre_check({}) == (True, None)


class TestApplyStatusChangeSuccess:
    """Test successful status change application."""

    def test_apply_status_change_success(self):
        """Test successful status change."""
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Test Issue"
        mock_core.issues.update.return_value = mock_issue

        config = StatusChangeConfig(
            status=Status.CLOSED,
            emoji="✅",
            title_verb="Closed",
            title_style="bold green",
            status_display="✅ Closed",
        )

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch(
                "roadmap.adapters.cli.issues.issue_status_helpers.console"
            ) as mock_console:
                apply_status_change(mock_core, "ISSUE-1", config)

                # Verify update was called
                mock_core.issues.update.assert_called_once()

    def test_apply_status_change_with_reason(self):
        """Test status change with reason."""
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Test Issue"
        mock_core.issues.update.return_value = mock_issue

        config = StatusChangeConfig(
            status=Status.BLOCKED,
            emoji="🚫",
            title_verb="Blocked",
            title_style="bold red",
            status_display="🚫 Blocked",
        )

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.issue_status_helpers.console"):
                apply_status_change(
                    mock_core, "ISSUE-1", config, reason="Waiting for approval"
                )

                # Should update with status
                mock_core.issues.update.assert_called()


class TestApplyStatusChangePreCheck:
    """Test status change with pre-checks."""

    def test_pre_check_passes(self):
        """Test when pre-check passes."""
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_core.issues.update.return_value = mock_issue

        def check_fn(issue):
            return True, None

        config = StatusChangeConfig(
            status=Status.CLOSED,
            emoji="✅",
            title_verb="Closed",
            title_style="bold green",
            status_display="✅ Closed",
            pre_check=check_fn,
        )

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.issue_status_helpers.console"):
                apply_status_change(mock_core, "ISSUE-1", config)

                # Should proceed with update
                mock_core.issues.update.assert_called_once()

    def test_pre_check_fails(self):
        """Test when pre-check fails."""
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()

        def check_fn(issue):
            return False, "Issue is already closed"

        config = StatusChangeConfig(
            status=Status.CLOSED,
            emoji="✅",
            title_verb="Closed",
            title_style="bold green",
            status_display="✅ Closed",
            pre_check=check_fn,
        )

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.issue_status_helpers.console"):
                apply_status_change(mock_core, "ISSUE-1", config)

                # Should NOT update since pre-check failed
                mock_core.issues.update.assert_not_called()


class TestApplyStatusChangeErrors:
    """Test error handling in status change."""

    def test_issue_not_found(self):
        """Test handling when issue doesn't exist."""
        mock_core = mock.MagicMock()

        config = StatusChangeConfig(
            status=Status.CLOSED,
            emoji="✅",
            title_verb="Closed",
            title_style="bold green",
            status_display="✅ Closed",
        )

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.side_effect = click.Abort()

            with pytest.raises(click.Abort):
                apply_status_change(mock_core, "INVALID", config)

    def test_update_fails(self):
        """Test when update returns None."""
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_core.issues.update.return_value = None  # Update failed

        config = StatusChangeConfig(
            status=Status.CLOSED,
            emoji="✅",
            title_verb="Closed",
            title_style="bold green",
            status_display="✅ Closed",
        )

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.issue_status_helpers.console"):
                with pytest.raises(click.Abort):
                    apply_status_change(mock_core, "ISSUE-1", config)


class TestApplyStatusChangeAllStatuses:
    """Test status changes for all relevant status types."""

    def test_closed_status(self):
        """Test closing an issue."""
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Task"
        mock_core.issues.update.return_value = mock_issue

        config = StatusChangeConfig(
            status=Status.CLOSED,
            emoji="✅",
            title_verb="Closed",
            title_style="bold green",
            status_display="✅ Closed",
        )

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.issue_status_helpers.console"):
                apply_status_change(mock_core, "ISSUE-1", config)
                assert mock_core.issues.update.called

    def test_open_status(self):
        """Test opening an issue."""
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Task"
        mock_core.issues.update.return_value = mock_issue

        config = StatusChangeConfig(
            status=Status.TODO,
            emoji="📝",
            title_verb="Opened",
            title_style="bold cyan",
            status_display="📝 Open",
        )

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.issue_status_helpers.console"):
                apply_status_change(mock_core, "ISSUE-1", config)
                assert mock_core.issues.update.called


class TestStatusChangeIntegration:
    """Integration tests for status changes."""

    def test_multiple_status_changes(self):
        """Test multiple status changes in sequence."""
        mock_core = mock.MagicMock()
        mock_issue = mock.MagicMock()
        mock_issue.title = "Task"
        mock_core.issues.update.return_value = mock_issue

        config1 = StatusChangeConfig(
            status=Status.BLOCKED,
            emoji="🚫",
            title_verb="Blocked",
            title_style="bold red",
            status_display="🚫 Blocked",
        )

        config2 = StatusChangeConfig(
            status=Status.CLOSED,
            emoji="✅",
            title_verb="Closed",
            title_style="bold green",
            status_display="✅ Closed",
        )

        with mock.patch(
            "roadmap.adapters.cli.helpers.ensure_entity_exists"
        ) as mock_ensure:
            mock_ensure.return_value = mock_issue

            with mock.patch("roadmap.adapters.cli.issues.issue_status_helpers.console"):
                apply_status_change(mock_core, "ISSUE-1", config1)
                apply_status_change(mock_core, "ISSUE-1", config2)

                # Both updates should have been called
                assert mock_core.issues.update.call_count == 2
