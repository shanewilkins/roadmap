"""Example integration tests using robust patterns.

Demonstrates best practices for integration testing:
  - Using IntegrationTestBase for common operations
  - Proper error context in assertions
  - API-based assertions instead of output parsing
  - Clean test isolation
"""

import pytest

from tests.fixtures import IntegrationTestBase


class TestIssueCreationRobust:
    """Example tests showing robust integration test patterns."""

    def test_create_single_issue(self, cli_runner):
        """Test creating a single issue with proper setup and assertions."""
        # Setup: Initialize roadmap
        IntegrationTestBase.init_roadmap(cli_runner)

        # Action: Create issue using helper
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Implement feature X",
            priority="high",
        )

        # Assert: Verify through data API (not text parsing)
        core = IntegrationTestBase.get_roadmap_core()
        issues = core.issues.list()
        assert len(issues) == 1, "Should have exactly one issue"
        assert issues[0].title == "Implement feature X"
        assert issues[0].priority.value == "high"

    def test_create_issue_with_milestone(self, cli_runner):
        """Test creating an issue assigned to a milestone."""
        # Setup
        IntegrationTestBase.init_roadmap(cli_runner)
        IntegrationTestBase.create_milestone(
            cli_runner,
            name="v1.0",
            headline="First release",
        )

        # Action
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Task for v1.0",
            milestone="v1.0",
            priority="medium",
        )

        # Assert: Verify issue is assigned to milestone
        core = IntegrationTestBase.get_roadmap_core()
        issues = core.issues.list()
        assert len(issues) == 1
        assert issues[0].milestone == "v1.0"

    def test_create_multiple_issues_with_varying_priorities(self, cli_runner):
        """Test creating multiple issues with different priorities."""
        IntegrationTestBase.init_roadmap(cli_runner)

        priorities = ["critical", "high", "medium", "low"]
        for priority in priorities:
            IntegrationTestBase.create_issue(
                cli_runner,
                title=f"Issue with {priority} priority",
                priority=priority,
            )

        # Assert: Verify all issues created with correct priorities
        core = IntegrationTestBase.get_roadmap_core()
        issues = core.issues.list()
        assert len(issues) == 4
        priorities_set = {issue.priority.value for issue in issues}
        assert priorities_set == set(priorities)


class TestMilestoneCreationRobust:
    """Example tests for milestone creation using robust patterns."""

    def test_create_milestone(self, cli_runner):
        """Test creating a milestone."""
        IntegrationTestBase.init_roadmap(cli_runner)

        IntegrationTestBase.create_milestone(
            cli_runner,
            name="v1.0.0",
            headline="Initial release",
        )

        # Assert through API
        core = IntegrationTestBase.get_roadmap_core()
        milestones = core.milestones.list()
        assert len(milestones) == 1
        assert milestones[0].name == "v1.0.0"

    def test_create_milestone_with_date(self, cli_runner):
        """Test creating a milestone with due date."""
        IntegrationTestBase.init_roadmap(cli_runner)

        IntegrationTestBase.create_milestone(
            cli_runner,
            name="Q1 2024",
            due_date="2024-03-31",
        )

        # Assert
        core = IntegrationTestBase.get_roadmap_core()
        milestones = core.milestones.list()
        assert len(milestones) == 1
        assert milestones[0].name == "Q1 2024"


class TestWorkflowRobust:
    """Example tests for complete workflows using robust patterns."""

    def test_complete_workflow_create_milestone_and_issues(self, cli_runner):
        """Test a complete workflow: create milestone, then add issues to it."""
        # Setup
        IntegrationTestBase.init_roadmap(cli_runner)

        # Action: Create milestone
        IntegrationTestBase.create_milestone(
            cli_runner,
            name="Beta Release",
            headline="Beta version of the product",
        )

        # Action: Create several issues for the milestone
        issue_count = 3
        for i in range(issue_count):
            IntegrationTestBase.create_issue(
                cli_runner,
                title=f"Feature {i + 1}",
                milestone="Beta Release",
                priority=["critical", "high", "medium"][i],
            )

        # Assert: Verify complete state
        state = IntegrationTestBase.roadmap_state()
        assert len(state["milestones"]) == 1
        assert len(state["issues"]) == issue_count

        # Verify all issues are in milestone
        core = IntegrationTestBase.get_roadmap_core()
        for issue in core.issues.list():
            assert issue.milestone == "Beta Release"

    def test_workflow_with_error_context(self, cli_runner):
        """Test that error context is captured properly."""
        IntegrationTestBase.init_roadmap(cli_runner)

        # Create a milestone
        IntegrationTestBase.create_milestone(cli_runner, name="v2.0")

        # Create issue in milestone
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Task 1",
            milestone="v2.0",
        )

        # Verify state with detailed error messages if assertions fail
        core = IntegrationTestBase.get_roadmap_core()
        issues = core.issues.list()
        assert len(issues) == 1, "Expected exactly 1 issue"
        assert issues[0].milestone == "v2.0", "Issue should be in v2.0 milestone"


class TestErrorHandlingRobust:
    """Tests demonstrating robust error handling patterns."""

    def test_init_creates_proper_structure(self, cli_runner):
        """Test that init creates proper directory structure."""
        core = IntegrationTestBase.init_roadmap(cli_runner)

        # Assert: Verify the roadmap was properly initialized
        assert core is not None
        state = IntegrationTestBase.roadmap_state()
        assert "issues" in state
        assert "milestones" in state

    def test_roadmap_state_access(self, cli_runner):
        """Test accessing roadmap state."""
        IntegrationTestBase.init_roadmap(cli_runner)

        state = IntegrationTestBase.roadmap_state()
        assert isinstance(state, dict)
        assert "issues" in state
        assert "milestones" in state
        assert "projects" in state
        assert isinstance(state["issues"], list)
        assert isinstance(state["milestones"], list)


@pytest.mark.parametrize(
    "priority,expected_count",
    [
        ("critical", 1),
        ("high", 2),
        ("medium", 3),
        ("low", 4),
    ],
)
def test_create_issues_parametrized(cli_runner, priority, expected_count):
    """Test creating multiple issues with parametrized priorities."""
    IntegrationTestBase.init_roadmap(cli_runner)

    for i in range(expected_count):
        IntegrationTestBase.create_issue(
            cli_runner,
            title=f"Issue {i + 1} with {priority}",
            priority=priority,
        )

    core = IntegrationTestBase.get_roadmap_core()
    issues = [issue for issue in core.issues.list() if issue.priority.value == priority]
    assert len(issues) == expected_count
