"""Tests for interactive baseline selection utility.

Tests the baseline selector's ability to guide teams through baseline
selection during first sync.
"""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.baseline.baseline_selector import (
    BaselineSelectionResult,
    BaselineStrategy,
    InteractiveBaselineSelector,
)


class TestBaselineStrategy:
    """Test BaselineStrategy enum."""

    def test_baseline_strategy_values(self):
        """Test that strategy values are correct."""
        assert BaselineStrategy.LOCAL.value == "local"
        assert BaselineStrategy.REMOTE.value == "remote"
        assert BaselineStrategy.INTERACTIVE.value == "interactive"


class TestBaselineSelectionResult:
    """Test BaselineSelectionResult class."""

    def test_result_initialization_local(self):
        """Test creating result with LOCAL strategy."""
        result = BaselineSelectionResult(BaselineStrategy.LOCAL)
        assert result.strategy == BaselineStrategy.LOCAL
        assert result.selected_issues == {}

    def test_result_initialization_remote(self):
        """Test creating result with REMOTE strategy."""
        result = BaselineSelectionResult(BaselineStrategy.REMOTE)
        assert result.strategy == BaselineStrategy.REMOTE
        assert result.selected_issues == {}

    def test_result_initialization_interactive(self):
        """Test creating result with INTERACTIVE strategy and selections."""
        selections = {"issue-1": "local", "issue-2": "remote"}
        result = BaselineSelectionResult(
            BaselineStrategy.INTERACTIVE, selected_issues=selections
        )
        assert result.strategy == BaselineStrategy.INTERACTIVE
        assert result.selected_issues == selections

    def test_get_baseline_for_issue_local_strategy(self):
        """Test getting baseline with LOCAL strategy."""
        result = BaselineSelectionResult(BaselineStrategy.LOCAL)
        local = {"id": "1", "status": "todo"}
        remote = {"id": "1", "status": "done"}
        baseline = result.get_baseline_for_issue("1", local, remote)
        assert baseline == local

    def test_get_baseline_for_issue_remote_strategy(self):
        """Test getting baseline with REMOTE strategy."""
        result = BaselineSelectionResult(BaselineStrategy.REMOTE)
        local = {"id": "1", "status": "todo"}
        remote = {"id": "1", "status": "done"}
        baseline = result.get_baseline_for_issue("1", local, remote)
        assert baseline == remote

    def test_get_baseline_for_issue_interactive_local_choice(self):
        """Test getting baseline with INTERACTIVE strategy, local chosen."""
        selections = {"issue-1": "local"}
        result = BaselineSelectionResult(
            BaselineStrategy.INTERACTIVE, selected_issues=selections
        )
        local = {"id": "issue-1", "status": "todo"}
        remote = {"id": "issue-1", "status": "done"}
        baseline = result.get_baseline_for_issue("issue-1", local, remote)
        assert baseline == local

    def test_get_baseline_for_issue_interactive_remote_choice(self):
        """Test getting baseline with INTERACTIVE strategy, remote chosen."""
        selections = {"issue-1": "remote"}
        result = BaselineSelectionResult(
            BaselineStrategy.INTERACTIVE, selected_issues=selections
        )
        local = {"id": "issue-1", "status": "todo"}
        remote = {"id": "issue-1", "status": "done"}
        baseline = result.get_baseline_for_issue("issue-1", local, remote)
        assert baseline == remote

    def test_get_baseline_for_issue_interactive_default_to_local(self):
        """Test interactive baseline defaults to local if issue not in selections."""
        result = BaselineSelectionResult(
            BaselineStrategy.INTERACTIVE, selected_issues={}
        )
        local = {"id": "issue-1", "status": "todo"}
        remote = {"id": "issue-1", "status": "done"}
        baseline = result.get_baseline_for_issue("issue-1", local, remote)
        assert baseline == local


class TestInteractiveBaselineSelector:
    """Test InteractiveBaselineSelector class."""

    @pytest.fixture
    def selector(self):
        """Create a selector with mock output."""
        output_mock = MagicMock()
        return InteractiveBaselineSelector(console_output_fn=output_mock), output_mock

    def test_selector_initialization(self):
        """Test selector initialization."""
        selector = InteractiveBaselineSelector()
        assert selector.logger is not None

    def test_selector_default_output(self, capsys):
        """Test default output function."""
        selector = InteractiveBaselineSelector()
        selector._default_output("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_prompt_baseline_strategy_local(self, selector):
        """Test baseline strategy prompt selecting LOCAL."""
        selector, output_mock = selector
        with patch("builtins.input", return_value="1"):
            result = selector.prompt_baseline_strategy()
        assert result == BaselineStrategy.LOCAL
        output_mock.assert_called()

    def test_prompt_baseline_strategy_remote(self, selector):
        """Test baseline strategy prompt selecting REMOTE."""
        selector, output_mock = selector
        with patch("builtins.input", return_value="2"):
            result = selector.prompt_baseline_strategy()
        assert result == BaselineStrategy.REMOTE
        output_mock.assert_called()

    def test_prompt_baseline_strategy_interactive(self, selector):
        """Test baseline strategy prompt selecting INTERACTIVE."""
        selector, output_mock = selector
        with patch("builtins.input", return_value="3"):
            result = selector.prompt_baseline_strategy()
        assert result == BaselineStrategy.INTERACTIVE
        output_mock.assert_called()

    def test_prompt_baseline_strategy_invalid_then_valid(self, selector):
        """Test strategy prompt with invalid then valid input."""
        selector, output_mock = selector
        with patch("builtins.input", side_effect=["99", "1"]):
            result = selector.prompt_baseline_strategy()
        assert result == BaselineStrategy.LOCAL

    def test_prompt_interactive_selections(self, selector):
        """Test interactive selections for multiple issues."""
        selector, output_mock = selector
        issues = [
            {
                "issue_id": "issue-1",
                "title": "Issue 1",
                "local_changes": {"status": "in_progress"},
                "remote_changes": None,
            },
            {
                "issue_id": "issue-2",
                "title": "Issue 2",
                "local_changes": None,
                "remote_changes": {"assignee": "bob"},
            },
        ]

        with patch("builtins.input", side_effect=["L", "R"]):
            selections = selector.prompt_interactive_selections(issues)

        assert selections["issue-1"] == "local"
        assert selections["issue-2"] == "remote"
        output_mock.assert_called()

    def test_prompt_interactive_selections_lowercase_input(self, selector):
        """Test interactive selections with lowercase input."""
        selector, output_mock = selector
        issues = [
            {
                "issue_id": "issue-1",
                "title": "Issue 1",
                "local_changes": {"status": "in_progress"},
                "remote_changes": None,
            }
        ]

        with patch("builtins.input", side_effect=["l"]):
            selections = selector.prompt_interactive_selections(issues)

        assert selections["issue-1"] == "local"

    def test_prompt_interactive_selections_full_words(self, selector):
        """Test interactive selections with full words."""
        selector, output_mock = selector
        issues = [
            {
                "issue_id": "issue-1",
                "title": "Issue 1",
                "local_changes": {"status": "in_progress"},
                "remote_changes": None,
            }
        ]

        with patch("builtins.input", side_effect=["LOCAL"]):
            selections = selector.prompt_interactive_selections(issues)

        assert selections["issue-1"] == "local"

    def test_prompt_interactive_selections_invalid_then_valid(self, selector):
        """Test interactive selections with invalid then valid input."""
        selector, output_mock = selector
        issues = [
            {
                "issue_id": "issue-1",
                "title": "Issue 1",
                "local_changes": {"status": "in_progress"},
                "remote_changes": None,
            }
        ]

        with patch("builtins.input", side_effect=["X", "R"]):
            selections = selector.prompt_interactive_selections(issues)

        assert selections["issue-1"] == "remote"

    def test_select_baseline_with_strategy_override(self, selector):
        """Test complete baseline selection with strategy override."""
        selector, output_mock = selector
        result = selector.select_baseline(strategy=BaselineStrategy.LOCAL)
        assert result.strategy == BaselineStrategy.LOCAL
        assert result.selected_issues == {}

    def test_select_baseline_without_strategy_local(self, selector):
        """Test complete baseline selection prompting for LOCAL."""
        selector, output_mock = selector
        with patch("builtins.input", return_value="1"):
            result = selector.select_baseline()
        assert result.strategy == BaselineStrategy.LOCAL
        assert result.selected_issues == {}

    def test_select_baseline_interactive_with_issues(self, selector):
        """Test complete baseline selection with interactive and issues."""
        selector, output_mock = selector
        issues = [
            {
                "issue_id": "issue-1",
                "title": "Issue 1",
                "local_changes": {"status": "in_progress"},
                "remote_changes": None,
            }
        ]

        with patch("builtins.input", side_effect=["3", "L"]):
            result = selector.select_baseline(issues_with_changes=issues)

        assert result.strategy == BaselineStrategy.INTERACTIVE
        assert result.selected_issues["issue-1"] == "local"

    def test_select_baseline_interactive_without_issues(self, selector):
        """Test interactive baseline selection without issues provided."""
        selector, output_mock = selector
        with patch("builtins.input", return_value="3"):
            result = selector.select_baseline(issues_with_changes=None)
        assert result.strategy == BaselineStrategy.INTERACTIVE
        assert result.selected_issues == {}

    def test_selector_with_issue_objects(self, selector):
        """Test selector works with Issue objects."""
        selector, output_mock = selector
        issues = [
            {
                "issue_id": "issue-1",
                "title": "Test Issue",
                "local_changes": {"status": "in_progress"},
                "remote_changes": None,
            }
        ]

        with patch("builtins.input", side_effect=["1"]):
            result = selector.select_baseline(
                issues_with_changes=issues, strategy=BaselineStrategy.LOCAL
            )

        assert result.strategy == BaselineStrategy.LOCAL
