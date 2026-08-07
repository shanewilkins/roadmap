"""Tests for status change parsing helpers.

Tests the extracted status change helpers using:
- Pure unit tests without mocks where possible
- Real Status and MilestoneStatus enums
- Comprehensive edge case coverage
- Clear assertions on actual behavior
"""

from roadmap.common.constants import MilestoneStatus, Status
from roadmap.core.services.helpers import (
    extract_issue_status_update,
    extract_milestone_status_update,
    parse_status_change,
)


class TestParseStatusChange:
    """Test parse_status_change helper function."""

    def test_parse_valid_status_change(self):
        """Test parsing valid status change string."""
        result = parse_status_change("open -> closed")
        assert result == "closed"

    def test_parse_with_whitespace(self):
        """Test parsing handles extra whitespace correctly."""
        result = parse_status_change("open ->  closed  ")
        assert result == "closed"  # strip() removes extra whitespace

    def test_parse_with_multiple_words(self):
        """Test parsing status with multiple words."""
        result = parse_status_change("in-progress -> closed")
        assert result == "closed"

    def test_parse_missing_arrow(self):
        """Test parsing fails without arrow separator."""
        result = parse_status_change("open done")
        assert result is None

    def test_parse_too_many_parts(self):
        """Test parsing fails with too many arrow separators."""
        result = parse_status_change("open -> in progress -> done")
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing fails on empty string."""
        result = parse_status_change("")
        assert result is None

    def test_parse_non_string(self):
        """Test parsing fails with non-string input."""
        assert parse_status_change(None) is None  # type: ignore[arg-type]
        assert parse_status_change(123) is None  # type: ignore[arg-type]
        assert parse_status_change([]) is None  # type: ignore[arg-type]

    def test_parse_only_arrow(self):
        """Test parsing with only arrow."""
        result = parse_status_change(" -> ")
        assert result == ""

    def test_parse_arrow_at_start(self):
        """Test parsing with arrow at start."""
        result = parse_status_change("->closed")
        assert result is None  # No space before arrow

    def test_parse_arrow_at_end(self):
        """Test parsing with arrow at end."""
        result = parse_status_change("todo -> ")
        assert result == ""


class TestExtractIssueStatusUpdate:
    """Test extract_issue_status_update helper function."""

    def test_extract_valid_status_to_closed(self):
        """Test extracting valid status change to closed."""
        result = extract_issue_status_update("todo -> closed")
        assert result is not None
        assert result["status_enum"] == Status.CLOSED
        assert result["github_state"] == "closed"

    def test_extract_valid_status_to_todo(self):
        """Test extracting valid status change to todo."""
        result = extract_issue_status_update("closed -> todo")
        assert result is not None
        assert result["status_enum"] == Status.TODO
        assert result["github_state"] == "open"

    def test_extract_valid_status_to_in_progress(self):
        """Test extracting valid status change to in_progress."""
        result = extract_issue_status_update("todo -> in-progress")
        assert result is not None
        assert result["status_enum"] == Status.IN_PROGRESS
        assert result["github_state"] == "open"

    def test_extract_invalid_status(self):
        """Test extracting invalid status fails gracefully."""
        result = extract_issue_status_update("todo -> invalid_status")
        assert result is None

    def test_extract_invalid_format(self):
        """Test extracting invalid format fails gracefully."""
        result = extract_issue_status_update("todo closed")
        assert result is None

    def test_extract_empty_string(self):
        """Test extracting from empty string returns None."""
        result = extract_issue_status_update("")
        assert result is None

    def test_extract_github_state_mapping_closed_to_closed(self):
        """Test GitHub state mapping for closed status."""
        result = extract_issue_status_update("todo -> closed")
        assert result is not None
        assert result["github_state"] == "closed"

    def test_extract_github_state_mapping_others_to_open(self):
        """Test GitHub state mapping for non-closed statuses."""
        for status_name in ["todo", "in-progress", "blocked", "review"]:
            result = extract_issue_status_update(f"closed -> {status_name}")
            assert result is not None
            assert result["github_state"] == "open"

    def test_extract_all_valid_issue_statuses(self):
        """Test extraction works for all valid issue statuses."""
        for status in Status:
            result = extract_issue_status_update(f"todo -> {status.value}")
            assert result is not None
            assert result["status_enum"] == status
            # Verify github_state is correctly mapped
            expected_state = "closed" if status == Status.CLOSED else "open"
            assert result["github_state"] == expected_state


class TestExtractMilestoneStatusUpdate:
    """Test extract_milestone_status_update helper function."""

    def test_extract_valid_milestone_status_to_closed(self):
        """Test extracting valid milestone status change to closed."""
        result = extract_milestone_status_update("open -> closed")
        assert result is not None
        assert result["status_enum"] == MilestoneStatus.CLOSED
        assert result["github_state"] == "closed"

    def test_extract_valid_milestone_status_to_open(self):
        """Test extracting valid milestone status change to open."""
        result = extract_milestone_status_update("closed -> open")
        assert result is not None
        assert result["status_enum"] == MilestoneStatus.OPEN
        assert result["github_state"] == "open"

    def test_extract_invalid_milestone_status(self):
        """Test extracting invalid milestone status fails gracefully."""
        result = extract_milestone_status_update("open -> invalid")
        assert result is None

    def test_extract_milestone_invalid_format(self):
        """Test extracting milestone with invalid format fails gracefully."""
        result = extract_milestone_status_update("open closed")
        assert result is None

    def test_extract_milestone_empty_string(self):
        """Test extracting milestone from empty string returns None."""
        result = extract_milestone_status_update("")
        assert result is None

    def test_extract_milestone_github_state_mapping_closed_to_closed(self):
        """Test GitHub state mapping for closed milestone status."""
        result = extract_milestone_status_update("open -> closed")
        assert result is not None
        assert result["github_state"] == "closed"

    def test_extract_milestone_github_state_mapping_open_to_open(self):
        """Test GitHub state mapping for open milestone status."""
        result = extract_milestone_status_update("closed -> open")
        assert result is not None
        assert result["github_state"] == "open"

    def test_extract_all_valid_milestone_statuses(self):
        """Test extraction works for all valid milestone statuses."""
        for status in MilestoneStatus:
            result = extract_milestone_status_update(f"open -> {status.value}")
            assert result is not None
            assert result["status_enum"] == status
            # Verify github_state is correctly mapped
            expected_state = "closed" if status == MilestoneStatus.CLOSED else "open"
            assert result["github_state"] == expected_state


class TestStatusChangeHelperEdgeCases:
    """Test edge cases and integration between helpers."""

    def test_parse_then_extract_issue(self):
        """Test parsing then extracting issue status works end-to-end."""
        change_str = "todo -> in-progress"
        parsed = parse_status_change(change_str)
        assert parsed is not None
        assert parsed == "in-progress"

        extracted = extract_issue_status_update(change_str)
        assert extracted is not None
        assert extracted["status_enum"].value == parsed

    def test_parse_then_extract_milestone(self):
        """Test parsing then extracting milestone status works end-to-end."""
        change_str = "open -> closed"
        parsed = parse_status_change(change_str)
        assert parsed is not None
        assert parsed == "closed"

        extracted = extract_milestone_status_update(change_str)
        assert extracted is not None
        assert extracted["status_enum"].value == parsed

    def test_status_consistency_across_helpers(self):
        """Test all helpers handle the same input consistently."""
        change_str = "closed -> todo"

        parsed = parse_status_change(change_str)
        issue_extracted = extract_issue_status_update(change_str)

        assert parsed is not None
        assert issue_extracted is not None
        assert issue_extracted["status_enum"].value == parsed

    def test_none_propagation(self):
        """Test None is properly propagated through helper chain."""
        invalid_change = "invalid"

        parsed = parse_status_change(invalid_change)
        issue_extracted = extract_issue_status_update(invalid_change)
        milestone_extracted = extract_milestone_status_update(invalid_change)

        assert parsed is None
        assert issue_extracted is None
        assert milestone_extracted is None

    def test_issue_vs_milestone_different_mapping(self):
        """Test issue and milestone status changes map differently."""
        # For issues: closed -> closed, others -> open
        # For milestones: closed -> closed, open -> open

        # Both use "closed" value
        issue_result = extract_issue_status_update("todo -> closed")
        milestone_result = extract_milestone_status_update("open -> closed")

        # Both map to "closed" github_state
        assert issue_result is not None
        assert milestone_result is not None
        assert issue_result["github_state"] == "closed"
        assert milestone_result["github_state"] == "closed"

        # But their status enums are different types
        assert isinstance(issue_result["status_enum"], Status)
        assert isinstance(milestone_result["status_enum"], MilestoneStatus)

    def test_whitespace_normalization(self):
        """Test that whitespace is handled consistently."""
        variations = [
            "todo->closed",  # no spaces
            "todo -> closed",  # normal
            "todo  ->  closed",  # extra spaces
        ]

        # All should fail because the arrow format check uses " -> "
        results = [parse_status_change(v) for v in variations]
        assert results[0] is None  # no spaces - fails
        assert results[1] == "closed"  # normal - works
        assert results[2] == "closed"  # extra spaces - works (spaces around arrow)
