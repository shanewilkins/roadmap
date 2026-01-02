"""Service layer tests for GitHub sync service with real objects.

Demonstrates refactored tests using real domain objects instead of mocks,
with specific assertions testing actual behavior rather than mock calls.
"""

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


class TestStatusChangeServiceLayer:
    """Test status change helpers as a service layer."""

    def test_service_parses_all_issue_status_changes(self):
        """Test service can parse all valid issue status changes."""
        # Use real Status enum values
        status_changes = [
            "todo",
            "in-progress",
            "blocked",
            "review",
            "closed",
        ]

        for change_str in status_changes:
            parsed = parse_status_change(f"todo -> {change_str}")
            # Specific assertion on actual value
            assert parsed == change_str, f"Failed to parse {change_str}"

    def test_service_extracts_issue_status_with_correct_github_mapping(self):
        """Test service extracts issue status and maps to GitHub state correctly."""
        # Test closed mapping
        result = extract_issue_status_update("todo -> closed")
        assert result is not None
        assert result["status_enum"] == Status.CLOSED
        assert result["github_state"] == "closed"  # Specific assertion on mapping

        # Test open mapping
        result = extract_issue_status_update("blocked -> in-progress")
        assert result is not None
        assert result["status_enum"] == Status.IN_PROGRESS
        assert result["github_state"] == "open"  # Specific assertion on mapping

    def test_service_extracts_milestone_status_with_correct_github_mapping(self):
        """Test service extracts milestone status and maps to GitHub state correctly."""
        # Test closed mapping
        result = extract_milestone_status_update("open -> closed")
        assert result is not None
        assert result["status_enum"] == MilestoneStatus.CLOSED
        assert result["github_state"] == "closed"

        # Test open mapping
        result = extract_milestone_status_update("closed -> open")
        assert result is not None
        assert result["status_enum"] == MilestoneStatus.OPEN
        assert result["github_state"] == "open"

    def test_service_validates_invalid_status_changes(self):
        """Test service rejects invalid status changes."""
        # Invalid status values
        invalid_changes = [
            "todo -> invalid-status",
            "fake -> real",
            "in-progress -> unknown",
        ]

        for change_str in invalid_changes:
            result = extract_issue_status_update(change_str)
            # Specific assertion: result must be None for invalid changes
            assert result is None, f"Should reject invalid change: {change_str}"

    def test_service_handles_malformed_change_strings(self):
        """Test service gracefully handles malformed change strings."""
        malformed = [
            "no arrow here",
            "->",
            "todo",
            "",
            "   ->   ",
        ]

        for change_str in malformed:
            result = extract_issue_status_update(change_str)
            # Specific assertion: result must be None for malformed strings
            assert result is None, f"Should reject malformed: {change_str}"


class TestStatusChangeServiceWithBuilders:
    """Test status change service using realistic test data builders."""

    def test_service_processes_real_issue_change_data(self):
        """Test service processes realistic issue change data from builders."""
        # Use the builder to create realistic test data
        change_data = (
            IssueChangeTestBuilder()
            .with_number(42)
            .with_title("Implement authentication")
            .with_status_change("in-progress", "review")
            .build()
        )

        # Extract the status change portion
        status_result = extract_issue_status_update(change_data["status_change"])

        # Specific assertions on actual behavior
        assert status_result is not None
        assert status_result["status_enum"] == Status.REVIEW
        assert status_result["github_state"] == "open"
        # Verify the change data is still intact
        assert change_data["number"] == 42
        assert change_data["title"] == "Implement authentication"

    def test_service_processes_real_milestone_change_data(self):
        """Test service processes realistic milestone change data from builders."""
        # Use the builder to create realistic test data
        change_data = (
            MilestoneChangeTestBuilder()
            .with_number(1)
            .with_title("v1.0 Release")
            .with_status_change("open", "closed")
            .build()
        )

        # Extract the status change portion
        status_result = extract_milestone_status_update(change_data["status_change"])

        # Specific assertions on actual behavior
        assert status_result is not None
        assert status_result["status_enum"] == MilestoneStatus.CLOSED
        assert status_result["github_state"] == "closed"
        # Verify the change data is still intact
        assert change_data["number"] == 1
        assert change_data["title"] == "v1.0 Release"

    def test_service_batch_processes_multiple_changes(self):
        """Test service can batch process multiple changes correctly."""
        # Create multiple changes
        changes = [
            IssueChangeTestBuilder().with_status_change("todo", "in-progress").build(),
            IssueChangeTestBuilder()
            .with_status_change("in-progress", "review")
            .build(),
            IssueChangeTestBuilder().with_status_change("review", "closed").build(),
        ]

        results = []
        for change in changes:
            result = extract_issue_status_update(change["status_change"])
            # Specific assertion: all must succeed
            assert result is not None
            results.append(result)

        # Specific assertions on batch results
        assert len(results) == 3
        assert results[0]["status_enum"] == Status.IN_PROGRESS
        assert results[1]["status_enum"] == Status.REVIEW
        assert results[2]["status_enum"] == Status.CLOSED
        # Verify GitHub state mapping is correct for each
        assert results[0]["github_state"] == "open"
        assert results[1]["github_state"] == "open"
        assert results[2]["github_state"] == "closed"


class TestStatusChangeServiceConsistency:
    """Test consistency and edge cases in status change service."""

    def test_service_handles_whitespace_consistently(self):
        """Test service handles various whitespace consistently."""
        test_cases = [
            ("todo -> in-progress", "in-progress"),
            ("todo  ->  in-progress", "in-progress"),  # Extra spaces
            (" todo -> in-progress ", "in-progress"),  # Leading/trailing
            ("todo-> in-progress", None),  # No space before arrow (invalid)
        ]

        for change_str, expected in test_cases:
            parsed = parse_status_change(change_str)
            # Specific assertion on whitespace handling
            assert (
                parsed == expected
            ), f"Inconsistent whitespace handling for: {change_str}"

    def test_service_produces_consistent_github_mappings(self):
        """Test service produces consistent mappings across multiple calls."""
        change_str = "in-progress -> closed"

        # Call multiple times
        results = [extract_issue_status_update(change_str) for _ in range(5)]

        # Specific assertions on consistency
        for result in results:
            assert result is not None
            assert result["status_enum"] == Status.CLOSED
            assert result["github_state"] == "closed"

    def test_service_all_enum_values_map_correctly(self):
        """Test service maps all Status enum values to GitHub states correctly."""
        for status in Status:
            # Build a change to that status
            change_str = f"todo -> {status.value}"
            result = extract_issue_status_update(change_str)

            # Specific assertions
            assert result is not None, f"Failed to process {status.value}"
            assert result["status_enum"] == status
            # Verify mapping logic
            expected_state = "closed" if status == Status.CLOSED else "open"
            assert (
                result["github_state"] == expected_state
            ), f"Wrong mapping for {status.value}"

    def test_service_all_milestone_values_map_correctly(self):
        """Test service maps all MilestoneStatus enum values to GitHub states correctly."""
        for milestone_status in MilestoneStatus:
            # Build a change to that status
            change_str = f"open -> {milestone_status.value}"
            result = extract_milestone_status_update(change_str)

            # Specific assertions
            assert result is not None, f"Failed to process {milestone_status.value}"
            assert result["status_enum"] == milestone_status
            # Verify mapping logic
            expected_state = milestone_status.value  # Milestones map 1:1
            assert result["github_state"] == expected_state
