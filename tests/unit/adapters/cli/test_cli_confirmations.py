"""Tests for CLI confirmation and entity validation helpers.

Tests confirmation prompts, entity existence checks, and cancellation handling.
"""

from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.cli.cli_confirmations import check_entity_exists, confirm_action


class TestCheckEntityExists:
    """Tests for check_entity_exists function."""

    @pytest.fixture
    def mock_core(self):
        """Create a mock RoadmapCore with issues, milestones, and projects."""
        core = Mock()

        # Setup issues collection
        issue = Mock(id="issue-1", title="Test Issue")
        core.issues = {"issue-1": issue}

        # Setup milestones collection
        milestone = Mock(id="milestone-1", name="v1-0")
        core.milestones = {"milestone-1": milestone}

        # Setup projects collection
        project = Mock(id="project-1", name="Test Project")
        core.projects = {"project-1": project}

        return core

    @pytest.mark.parametrize(
        "entity_type,entity_id,should_exist",
        [
            ("issue", "issue-1", True),
            ("issue", "nonexistent", False),
            ("milestone", "milestone-1", True),
            ("milestone", "nonexistent", False),
            ("project", "project-1", True),
            ("project", "nonexistent", False),
        ],
    )
    def test_check_entity_exists_parametrized(
        self, mock_core, entity_type, entity_id, should_exist
    ):
        """Parametrized test for entity existence checks."""
        result = check_entity_exists(mock_core, entity_type, entity_id)

        if should_exist:
            assert result is not False
            assert hasattr(result, "id")
        else:
            assert result is False

    def test_check_entity_exists_with_entity_lookup(self, mock_core):
        """Test that pre-fetched entity is used instead of lookup."""
        pre_fetched = Mock(id="issue-1", title="Pre-fetched Issue")

        result = check_entity_exists(
            mock_core, "issue", "fake-id", entity_lookup=pre_fetched
        )

        assert result == pre_fetched

    def test_check_entity_exists_with_invalid_entity_type(self):
        """Test handling of invalid entity type."""
        core = Mock()
        core.invalid_types = None  # No such collection exists

        result = check_entity_exists(core, "invalid_type", "some-id")

        assert result is False

    def test_check_entity_exists_with_none_entity_lookup(self, mock_core):
        """Test that None entity_lookup returns False."""
        result = check_entity_exists(mock_core, "issue", "some-id", entity_lookup=None)

        assert result is False


class TestConfirmAction:
    """Tests for confirm_action function."""

    @pytest.mark.parametrize(
        "user_confirms,default,expected",
        [
            (True, False, True),
            (False, False, False),
            (True, True, True),
            (False, True, False),
        ],
    )
    def test_confirm_action_parametrized(self, user_confirms, default, expected):
        """Parametrized test for confirmation prompts."""
        with patch("click.confirm", return_value=user_confirms):
            result = confirm_action("Are you sure?", default=default)

            assert result == expected

    def test_confirm_action_displays_cancellation_message(self):
        """Test that cancellation message is displayed when user declines."""
        with patch("click.confirm", return_value=False):
            with patch(
                "roadmap.adapters.cli.cli_confirmations.console.print"
            ) as mock_print:
                confirm_action("Continue?", default=False)

                # Verify console.print was called with cancellation message
                mock_print.assert_called()
                call_args = str(mock_print.call_args)
                assert "Cancelled" in call_args

    def test_confirm_action_with_default_true(self):
        """Test confirmation with default=True."""
        with patch("click.confirm", return_value=True):
            result = confirm_action("Confirm?", default=True)

            assert result is True

    def test_confirm_action_with_default_false(self):
        """Test confirmation with default=False."""
        with patch("click.confirm", return_value=False):
            result = confirm_action("Confirm?", default=False)

            assert result is False

    def test_confirm_action_prompt_text_passed_to_click(self):
        """Test that prompt text is passed to click.confirm."""
        prompt = "Are you absolutely sure?"

        with patch("click.confirm") as mock_confirm:
            mock_confirm.return_value = True
            confirm_action(prompt, default=False)

            mock_confirm.assert_called_once_with(prompt, default=False)
