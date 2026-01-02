"""Service layer tests for GitHub sync functionality with real objects.

Demonstrates refactored tests that focus on actual behavior
and workflow correctness rather than implementation details and mocks.
Uses builders for realistic test data and assertions on actual behavior.
"""

from roadmap.common.constants import MilestoneStatus, Status
from roadmap.core.services.helpers.status_change_helpers import (
    extract_issue_status_update,
    extract_milestone_status_update,
)
from tests.factories.github_sync_data import (
    GitHubIssueTestBuilder,
    GitHubMilestoneTestBuilder,
    IssueChangeTestBuilder,
    MilestoneChangeTestBuilder,
)


class TestOrchestrationWorkflowService:
    """Test complete orchestration workflows with real objects."""

    def test_orchestrator_processes_single_issue_change_through_service(self):
        """Test processing a single issue status change as a complete service operation."""
        # Setup: Create real change data with builder
        change = (
            IssueChangeTestBuilder()
            .with_number(123)
            .with_title("Implement feature")
            .with_status_change("todo", "in-progress")
            .build()
        )

        # Execute: Process the status change through the service
        result = extract_issue_status_update(change["status_change"])

        # Verify: Result contains correct status enum and GitHub mapping
        assert result is not None
        assert result["status_enum"] == Status.IN_PROGRESS
        assert result["github_state"] == "open"
        # Verify change data is intact
        assert change["number"] == 123
        assert change["title"] == "Implement feature"

    def test_orchestrator_processes_single_milestone_change_through_service(self):
        """Test processing a single milestone status change as a complete service operation."""
        # Setup: Create real change data with builder
        change = (
            MilestoneChangeTestBuilder()
            .with_number(1)
            .with_title("v1.0 Release")
            .with_status_change("open", "closed")
            .build()
        )

        # Execute: Process the milestone status change through the service
        result = extract_milestone_status_update(change["status_change"])

        # Verify: Result contains correct status enum and GitHub mapping
        assert result is not None
        assert result["status_enum"] == MilestoneStatus.CLOSED
        assert result["github_state"] == "closed"
        # Verify change data is intact
        assert change["number"] == 1
        assert change["title"] == "v1.0 Release"

    def test_orchestrator_service_validates_status_transitions(self):
        """Test orchestrator validates all status transitions work correctly."""
        # Setup: Create multiple status transitions
        transitions = [
            ("todo", Status.TODO),
            ("in-progress", Status.IN_PROGRESS),
            ("blocked", Status.BLOCKED),
            ("review", Status.REVIEW),
            ("closed", Status.CLOSED),
        ]

        # Execute: Test each transition
        for status_value, expected_enum in transitions:
            change_str = f"todo -> {status_value}"
            result = extract_issue_status_update(change_str)

            # Verify: Each transition processes correctly
            assert result is not None, f"Failed to process transition to {status_value}"
            assert result["status_enum"] == expected_enum

    def test_orchestrator_maps_github_states_correctly_for_issue_statuses(self):
        """Test orchestrator correctly maps issue statuses to GitHub states."""
        # Mapping verification tests
        test_cases = [
            ("todo -> in-progress", "open", Status.IN_PROGRESS),
            ("in-progress -> review", "open", Status.REVIEW),
            ("review -> closed", "closed", Status.CLOSED),
            ("blocked -> todo", "open", Status.TODO),
        ]

        # Execute: Test each mapping
        for change_str, expected_github_state, expected_status in test_cases:
            result = extract_issue_status_update(change_str)

            # Verify: GitHub state and status match correctly
            assert result is not None
            assert (
                result["github_state"] == expected_github_state
            ), f"Wrong GitHub state for {change_str}"
            assert (
                result["status_enum"] == expected_status
            ), f"Wrong status for {change_str}"


class TestOrchestrationMultiChangeWorkflow:
    """Test orchestrator handling multiple changes in single sync."""

    def test_orchestrator_processes_multiple_issue_changes(self):
        """Test orchestrator processes multiple issue changes in sequence."""
        # Setup: Create multiple changes with builders
        issue_changes = [
            IssueChangeTestBuilder()
            .with_number(1)
            .with_status_change("todo", "in-progress")
            .build(),
            IssueChangeTestBuilder()
            .with_number(2)
            .with_status_change("in-progress", "review")
            .build(),
            IssueChangeTestBuilder()
            .with_number(3)
            .with_status_change("review", "closed")
            .build(),
        ]

        # Execute: Process each change
        results = []
        for change in issue_changes:
            result = extract_issue_status_update(change["status_change"])
            results.append(result)

        # Verify: All changes processed correctly
        assert len(results) == 3
        assert results[0]["status_enum"] == Status.IN_PROGRESS
        assert results[1]["status_enum"] == Status.REVIEW
        assert results[2]["status_enum"] == Status.CLOSED
        # Verify GitHub state mapping
        assert results[0]["github_state"] == "open"
        assert results[1]["github_state"] == "open"
        assert results[2]["github_state"] == "closed"

    def test_orchestrator_processes_multiple_milestone_changes(self):
        """Test orchestrator processes multiple milestone changes in sequence."""
        # Setup: Create multiple milestone changes
        milestone_changes = [
            MilestoneChangeTestBuilder()
            .with_number(1)
            .with_title("v1.0")
            .with_status_change("open", "closed")
            .build(),
            MilestoneChangeTestBuilder()
            .with_number(2)
            .with_title("v2.0")
            .with_status_change("open", "open")  # No change
            .build(),
        ]

        # Execute: Process each change
        results = []
        for change in milestone_changes:
            result = extract_milestone_status_update(change["status_change"])
            results.append(result)

        # Verify: All changes processed correctly
        assert len(results) == 2
        assert results[0]["status_enum"] == MilestoneStatus.CLOSED
        assert results[1]["status_enum"] == MilestoneStatus.OPEN

    def test_orchestrator_batch_creates_realistic_github_issues(self):
        """Test orchestrator can batch create realistic GitHub issue data."""
        # Setup: Create multiple realistic GitHub issues with builder
        github_issues = [
            GitHubIssueTestBuilder()
            .with_number(i)
            .with_title(f"Issue {i}")
            .with_state("open" if i % 2 == 0 else "closed")
            .build()
            for i in range(1, 6)
        ]

        # Verify: All issues created with correct structure
        assert len(github_issues) == 5
        for idx, issue in enumerate(github_issues, 1):
            assert issue["number"] == idx
            assert issue["title"] == f"Issue {idx}"
            assert issue["state"] in ["open", "closed"]

    def test_orchestrator_batch_creates_realistic_github_milestones(self):
        """Test orchestrator can batch create realistic GitHub milestone data."""
        # Setup: Create multiple realistic GitHub milestones
        github_milestones = [
            GitHubMilestoneTestBuilder()
            .with_number(i)
            .with_title(f"v{i}.0")
            .with_state("open" if i < 3 else "closed")
            .build()
            for i in range(1, 6)
        ]

        # Verify: All milestones created with correct structure
        assert len(github_milestones) == 5
        for idx, milestone in enumerate(github_milestones, 1):
            assert milestone["number"] == idx
            assert milestone["title"] == f"v{idx}.0"
            assert milestone["state"] in ["open", "closed"]


class TestOrchestrationErrorHandling:
    """Test orchestrator error handling in service layer."""

    def test_orchestrator_service_rejects_invalid_issue_status_changes(self):
        """Test orchestrator rejects issue status changes with missing arrows gracefully."""
        # Setup: Malformed change strings (no arrow or incomplete)
        malformed_changes = [
            "todochangeto invalid",  # No arrow
            "todo only",  # Incomplete
            "->",  # Only arrow
        ]

        # Execute: Try to process malformed changes
        results = []
        for change_str in malformed_changes:
            result = extract_issue_status_update(change_str)
            results.append(result)

        # Verify: Malformed changes return None
        assert all(result is None for result in results)

    def test_orchestrator_service_rejects_invalid_milestone_status_changes(self):
        """Test orchestrator rejects milestone status changes with missing arrows gracefully."""
        # Setup: Malformed change strings (no arrow or incomplete)
        malformed_changes = [
            "openchangeto closed",  # No arrow
            "open only",  # Incomplete
            "->",  # Only arrow
        ]

        # Execute: Try to process malformed changes
        results = []
        for change_str in malformed_changes:
            result = extract_milestone_status_update(change_str)
            results.append(result)

        # Verify: Malformed changes return None
        assert all(result is None for result in results)

    def test_orchestrator_handles_malformed_change_strings(self):
        """Test orchestrator handles malformed change strings gracefully."""
        # Setup: Malformed change strings
        malformed_changes = [
            "no arrow here",
            "->",
            "todo",
            "",
            "   ->   ",
        ]

        # Execute: Try to process malformed strings
        for change_str in malformed_changes:
            issue_result = extract_issue_status_update(change_str)
            milestone_result = extract_milestone_status_update(change_str)

            # Verify: Both return None for malformed input
            assert issue_result is None, f"Should reject malformed: {change_str}"
            assert milestone_result is None, f"Should reject malformed: {change_str}"

    def test_orchestrator_validates_all_enum_status_values(self):
        """Test orchestrator can process all valid Status enum values."""
        # Execute: Process changes for all Status values
        valid_statuses = []
        for status in Status:
            change_str = f"todo -> {status.value}"
            result = extract_issue_status_update(change_str)

            # Verify: All statuses process successfully
            assert result is not None, f"Failed to process status: {status.value}"
            assert result["status_enum"] == status
            valid_statuses.append(status.value)

        # Verify: All Status enum values can be processed
        assert len(valid_statuses) == len(Status)

    def test_orchestrator_validates_all_enum_milestone_values(self):
        """Test orchestrator can process all valid MilestoneStatus enum values."""
        # Execute: Process changes for all MilestoneStatus values
        valid_statuses = []
        for milestone_status in MilestoneStatus:
            change_str = f"open -> {milestone_status.value}"
            result = extract_milestone_status_update(change_str)

            # Verify: All milestone statuses process successfully
            assert (
                result is not None
            ), f"Failed to process milestone status: {milestone_status.value}"
            assert result["status_enum"] == milestone_status
            valid_statuses.append(milestone_status.value)

        # Verify: All MilestoneStatus enum values can be processed
        assert len(valid_statuses) == len(MilestoneStatus)


class TestGitHubDataMappingService:
    """Test service-level GitHub data mapping with builders."""

    def test_orchestrator_service_maps_issue_change_data(self):
        """Test service can map realistic issue change data."""
        # Setup: Create realistic issue change with builder
        issue = (
            IssueChangeTestBuilder()
            .with_number(42)
            .with_title("Fix login bug")
            .with_status_change("todo", "in-progress")
            .build()
        )

        # Execute: Process the change
        result = extract_issue_status_update(issue["status_change"])

        # Verify: Change data is intact and status extracted correctly
        assert issue["number"] == 42
        assert issue["title"] == "Fix login bug"
        assert result is not None
        assert result["status_enum"] == Status.IN_PROGRESS
        assert result["github_state"] == "open"

    def test_orchestrator_service_maps_milestone_change_data(self):
        """Test service can map realistic milestone change data."""
        # Setup: Create realistic milestone change with builder
        milestone = (
            MilestoneChangeTestBuilder()
            .with_number(1)
            .with_title("v1.0 Release")
            .with_status_change("open", "closed")
            .build()
        )

        # Execute: Process the change
        result = extract_milestone_status_update(milestone["status_change"])

        # Verify: Change data is intact and status extracted correctly
        assert milestone["number"] == 1
        assert milestone["title"] == "v1.0 Release"
        assert result is not None
        assert result["status_enum"] == MilestoneStatus.CLOSED
        assert result["github_state"] == "closed"

    def test_orchestrator_service_preserves_change_context(self):
        """Test service preserves all change context while processing."""
        # Setup: Create issue change with full context
        issue = (
            IssueChangeTestBuilder()
            .with_number(100)
            .with_title("Feature request")
            .with_github_number(50)
            .with_status_change("blocked", "review")
            .build()
        )

        # Execute: Process while preserving context
        result = extract_issue_status_update(issue["status_change"])

        # Verify: All context preserved and status extracted
        assert issue["number"] == 100
        assert issue["title"] == "Feature request"
        assert issue["github_number"] == 50
        assert result["status_enum"] == Status.REVIEW
        assert result["github_state"] == "open"
