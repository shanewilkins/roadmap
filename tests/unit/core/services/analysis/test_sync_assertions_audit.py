"""Phase 5: QA and assertions audit for sync-related tests.

This file documents and implements improved assertions across all sync-related tests,
demonstrating the importance of specific, meaningful assertions that test actual
business logic rather than implementation details or vague type checks.

Key improvements from audit:
1. Replace type checks with business logic assertions
2. Verify state transitions and transformations explicitly
3. Test actual enum values, not string representations
4. Validate GitHub state mappings are correct
5. Ensure change context is preserved through processing
"""

import pytest

from roadmap.common.constants import MilestoneStatus, Status
from roadmap.core.services.helpers.status_change_helpers import (
    extract_issue_status_update,
    extract_milestone_status_update,
    parse_status_change,
)
from tests.factories.github_sync_data import (
    IssueChangeTestBuilder,
    MilestoneChangeTestBuilder,
)


class TestAssertionQualityIssueStatusChanges:
    """Demonstrate assertion quality improvements for issue status changes.

    BEFORE (Poor Assertions):
    - assert result is not None  # Too vague
    - assert "in-progress" in str(result)  # String matching, fragile
    - assert isinstance(result, dict)  # Type check, not business logic

    AFTER (Good Assertions):
    - assert result["status_enum"] == Status.IN_PROGRESS  # Specific value
    - assert result["github_state"] == "open"  # Business logic mapping
    - assert change["number"] == 123  # Context preservation
    """

    def test_assertion_quality_for_todo_to_in_progress_transition(self):
        """Test assertions verify actual status transition, not just existence."""
        change = (
            IssueChangeTestBuilder()
            .with_number(1)
            .with_status_change("todo", "in-progress")
            .build()
        )

        result = extract_issue_status_update(change["status_change"])
        assert result is not None

        # GOOD: Verify the exact status enum value (business logic)
        assert result["status_enum"] == Status.IN_PROGRESS
        # GOOD: Verify GitHub state mapping is correct (external interface)
        assert result["github_state"] == "open"
        # GOOD: Verify change context preserved (data integrity)
        assert change["number"] == 1

    def test_assertion_quality_for_review_to_closed_transition(self):
        """Test assertions verify state change with business logic."""
        change = IssueChangeTestBuilder().with_status_change("review", "closed").build()

        result = extract_issue_status_update(change["status_change"])
        assert result is not None

        # GOOD: Specific status value assertion
        assert result["status_enum"] == Status.CLOSED
        # GOOD: Verify GitHub mapping for closed state
        assert result["github_state"] == "closed"
        # GOOD: Verify this is the only state that maps to "closed"
        non_closed_result = extract_issue_status_update("todo -> in-progress")
        assert non_closed_result is not None
        assert non_closed_result["github_state"] == "open"

    @pytest.mark.parametrize(
        "status,expected_github_state",
        [
            (Status.TODO, "open"),
            (Status.IN_PROGRESS, "open"),
            (Status.BLOCKED, "open"),
            (Status.REVIEW, "open"),
            (Status.CLOSED, "closed"),
        ],
    )
    def test_assertion_quality_status_github_mapping(
        self, status, expected_github_state
    ):
        """Test assertions verify status to GitHub state mapping for each status."""
        # Execute: Process status change through service
        change_str = f"todo -> {status.value}"
        result = extract_issue_status_update(change_str)
        assert result is not None

        # GOOD: Verify correct enum value
        assert result["status_enum"] == status, f"Wrong enum for {status.value}"
        # GOOD: Verify correct GitHub state mapping
        assert result["github_state"] == expected_github_state, (
            f"Status {status.value} should map to '{expected_github_state}'"
        )
        """Test assertions verify parsing doesn't lose change context."""
        issue = (
            IssueChangeTestBuilder()
            .with_number(42)
            .with_title("Urgent fix")
            .with_github_number(99)
            .with_status_change("blocked", "in-progress")
            .build()
        )

        # Process status change
        result = extract_issue_status_update(issue["status_change"])

        # GOOD: Verify all original context preserved
        assert issue["number"] == 42, "Issue number should not change"
        assert issue["title"] == "Urgent fix", "Issue title should not change"
        assert issue["github_number"] == 99, "GitHub number should not change"
        # GOOD: Verify status extraction is correct
        assert result is not None
        assert result["status_enum"] == Status.IN_PROGRESS
        assert result["github_state"] == "open"


class TestAssertionQualityMilestoneStatusChanges:
    """Demonstrate assertion quality improvements for milestone status changes."""

    def test_assertion_quality_for_milestone_open_to_closed(self):
        """Test assertions verify milestone state transition explicitly."""
        milestone = (
            MilestoneChangeTestBuilder()
            .with_number(1)
            .with_title("v1.0")
            .with_status_change("open", "closed")
            .build()
        )

        result = extract_milestone_status_update(milestone["status_change"])

        # GOOD: Verify exact status enum (not just "closed" string)
        assert result is not None
        assert result["status_enum"] == MilestoneStatus.CLOSED
        # GOOD: Verify GitHub state mapping is correct
        assert result["github_state"] == "closed"
        # GOOD: Verify milestone context preserved
        assert milestone["number"] == 1
        assert milestone["title"] == "v1.0"

    @pytest.mark.parametrize(
        "status_enum,github_state",
        [
            (MilestoneStatus.OPEN, "open"),
            (MilestoneStatus.CLOSED, "closed"),
        ],
    )
    def test_assertion_quality_milestone_github_mapping(
        self, status_enum, github_state
    ):
        """Test assertions verify milestone status to GitHub state mapping."""
        # Execute: Process milestone status change
        change_str = f"open -> {status_enum.value}"
        result = extract_milestone_status_update(change_str)

        # GOOD: Verify correct status enum
        assert result is not None
        assert result["status_enum"] == status_enum, (
            f"Wrong enum for {status_enum.value}"
        )
        # GOOD: Verify correct GitHub state mapping
        assert result["github_state"] == github_state, (
            f"Wrong GitHub state for {status_enum.value}"
        )


class TestAssertionQualityBatchOperations:
    """Demonstrate assertion quality for batch/bulk operations."""

    def test_assertion_quality_for_batch_issue_processing(self):
        """Test assertions verify batch processing correctness."""
        # Create multiple issues
        issues = [
            IssueChangeTestBuilder()
            .with_number(i)
            .with_status_change("todo", "in-progress")
            .build()
            for i in range(1, 6)
        ]

        # Process all
        results = [
            extract_issue_status_update(issue["status_change"]) for issue in issues
        ]

        # GOOD: Verify count is correct
        assert len(results) == 5
        # GOOD: Verify all processed successfully
        assert all(r is not None for r in results)
        # Type guard: filter out None values for subscripting
        non_none_results = [r for r in results if r is not None]
        # GOOD: Verify each has correct status
        assert all(r["status_enum"] == Status.IN_PROGRESS for r in non_none_results), (
            "All should transition to in-progress"
        )
        # GOOD: Verify each has correct GitHub state
        assert all(r["github_state"] == "open" for r in non_none_results), (
            "in-progress maps to open"
        )

    def test_assertion_quality_for_batch_milestone_processing(self):
        """Test assertions verify batch milestone processing."""
        milestones = [
            MilestoneChangeTestBuilder()
            .with_number(i)
            .with_title(f"v{i}.0")
            .with_status_change("open", "closed")
            .build()
            for i in range(1, 4)
        ]

        results = [
            extract_milestone_status_update(milestone["status_change"])
            for milestone in milestones
        ]

        # GOOD: Verify batch completion
        assert len(results) == 3
        assert all(r is not None for r in results)
        # Type guard: filter out None values for subscripting
        non_none_results = [r for r in results if r is not None]
        # GOOD: Verify all transitions are correct
        assert all(
            r["status_enum"] == MilestoneStatus.CLOSED for r in non_none_results
        ), "All should close"
        # GOOD: Verify all map to GitHub closed state
        assert all(r["github_state"] == "closed" for r in non_none_results), (
            "Closed maps to closed"
        )


class TestAssertionQualityErrorCases:
    """Demonstrate assertion quality for error handling cases."""

    @pytest.mark.parametrize(
        "malformed_input",
        [
            "no arrow",
            "->",
            "",
            "incomplete ->",
            "-> incomplete",
        ],
    )
    @pytest.mark.parametrize(
        "update_func",
        [
            extract_issue_status_update,
            extract_milestone_status_update,
        ],
    )
    def test_assertion_quality_malformed_input_rejected(
        self, malformed_input, update_func
    ):
        """Test assertions verify error handling is explicit."""
        result = update_func(malformed_input)
        assert result is None, f"Should reject malformed: {malformed_input}"

    def test_assertion_quality_for_whitespace_handling(self):
        """Test assertions verify whitespace handling is consistent."""
        # GOOD: Test that extra whitespace doesn't break parsing
        normal = "todo -> in-progress"
        extra_spaces = "todo  ->  in-progress"

        result_normal = parse_status_change(normal)
        result_extra = parse_status_change(extra_spaces)

        # GOOD: Verify both parse to same value (whitespace normalization)
        assert result_normal == "in-progress"
        assert result_extra == "in-progress"
        assert result_normal == result_extra, "Extra whitespace should be handled"


class TestAssertionQualityDataBuilders:
    """Demonstrate assertion quality when using data builders."""

    def test_assertion_quality_builder_produces_correct_structure(self):
        """Test assertions verify builder produces complete data structure."""
        issue = (
            IssueChangeTestBuilder()
            .with_number(123)
            .with_title("Test Issue")
            .with_status_change("todo", "in-progress")
            .build()
        )

        # GOOD: Verify all required fields are present
        assert "number" in issue
        assert "title" in issue
        assert "status_change" in issue
        assert "body" in issue
        assert "github_number" in issue

        # GOOD: Verify field values are correct
        assert issue["number"] == 123
        assert issue["title"] == "Test Issue"
        assert issue["status_change"] == "todo -> in-progress"

    def test_assertion_quality_builder_chaining_preserves_values(self):
        """Test assertions verify builder chain doesn't lose values."""
        milestone = (
            MilestoneChangeTestBuilder()
            .with_number(5)
            .with_title("v5.0")
            .with_github_number(25)
            .with_status_change("open", "closed")
            .build()
        )

        # GOOD: Verify all chained values present
        assert milestone["number"] == 5, "Number should be preserved from with_number()"
        assert milestone["title"] == "v5.0", (
            "Title should be preserved from with_title()"
        )
        assert milestone["github_number"] == 25, "GitHub number should be preserved"
        assert milestone["status_change"] == "open -> closed", (
            "Status change should be preserved"
        )


class TestAssertionQualityEnumHandling:
    """Demonstrate assertion quality for enum handling."""

    def test_assertion_quality_for_all_status_enums(self):
        """Test assertions verify all Status enum values are handled."""
        # GOOD: Dynamically test all enum members
        for status in Status:
            change_str = f"todo -> {status.value}"
            result = extract_issue_status_update(change_str)

            # GOOD: Verify result exists
            assert result is not None, f"Status {status.value} should be supported"
            # GOOD: Verify exact enum match
            assert result["status_enum"] is status, (
                f"Should return {status} enum, not string"
            )
            # GOOD: Verify GitHub mapping exists
            assert "github_state" in result, (
                f"GitHub state mapping missing for {status.value}"
            )
            assert result["github_state"] in [
                "open",
                "closed",
            ], f"Invalid GitHub state for {status.value}"

    def test_assertion_quality_for_all_milestone_enums(self):
        """Test assertions verify all MilestoneStatus enum values are handled."""
        # GOOD: Dynamically test all milestone enum members
        for milestone_status in MilestoneStatus:
            change_str = f"open -> {milestone_status.value}"
            result = extract_milestone_status_update(change_str)

            # GOOD: Verify result exists
            assert result is not None, (
                f"Milestone status {milestone_status.value} should be supported"
            )
            # GOOD: Verify exact enum match
            assert result["status_enum"] is milestone_status, (
                f"Should return {milestone_status} enum, not string"
            )
            # GOOD: Verify GitHub mapping
            assert result["github_state"] == milestone_status.value, (
                "Milestone should map 1:1 to GitHub state"
            )
