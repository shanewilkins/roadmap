"""Data factories for building complex test scenarios.

Factories provide a fluent, DRY way to build test data scenarios without
repeating setup code. They handle initialization and return configured objects.
"""

from typing import Any

from click.testing import CliRunner

from .integration_helpers import IntegrationTestBase


class MilestoneScenarioFactory:
    """Factory for building milestone-based test scenarios."""

    def __init__(self, cli_runner: CliRunner):
        """Initialize factory with CLI runner.

        Args:
            cli_runner: Click CliRunner for executing CLI commands
        """
        self.cli_runner = cli_runner
        self.core = IntegrationTestBase.get_roadmap_core()

    def with_initialized_roadmap(
        self, project_name: str = "Test Project"
    ) -> "MilestoneScenarioFactory":
        """Initialize roadmap.

        Args:
            project_name: Name for the project

        Returns:
            Self for fluent chaining
        """
        IntegrationTestBase.init_roadmap(self.cli_runner, project_name)
        self.core = IntegrationTestBase.get_roadmap_core()
        return self

    def with_milestone(
        self,
        name: str,
        description: str = "",
        due_date: str | None = None,
    ) -> "MilestoneScenarioFactory":
        """Add a milestone to the scenario.

        Args:
            name: Milestone name
            description: Optional description
            due_date: Optional due date (YYYY-MM-DD)

        Returns:
            Self for fluent chaining
        """
        IntegrationTestBase.create_milestone(
            self.cli_runner,
            name=name,
            headline=description,
            due_date=due_date,
        )
        return self

    def with_multiple_milestones(
        self, count: int, name_prefix: str = "sprint"
    ) -> "MilestoneScenarioFactory":
        """Add multiple milestones.

        Args:
            count: Number of milestones to create
            name_prefix: Prefix for milestone names (e.g., "sprint-1", "sprint-2")

        Returns:
            Self for fluent chaining
        """
        for i in range(1, count + 1):
            self.with_milestone(f"{name_prefix}-{i}")
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the complete scenario.

        Returns:
            Dictionary with milestones and issues
        """
        return IntegrationTestBase.roadmap_state()


class IssueScenarioFactory:
    """Factory for building issue-based test scenarios."""

    def __init__(self, cli_runner: CliRunner):
        """Initialize factory with CLI runner.

        Args:
            cli_runner: Click CliRunner for executing CLI commands
        """
        self.cli_runner = cli_runner
        self.core = IntegrationTestBase.get_roadmap_core()

    def with_initialized_roadmap(
        self, project_name: str = "Test Project"
    ) -> "IssueScenarioFactory":
        """Initialize roadmap.

        Args:
            project_name: Name for the project

        Returns:
            Self for fluent chaining
        """
        IntegrationTestBase.init_roadmap(self.cli_runner, project_name)
        self.core = IntegrationTestBase.get_roadmap_core()
        return self

    def with_issue(
        self,
        title: str,
        description: str = "",
        priority: str | None = None,
        milestone: str | None = None,
    ) -> "IssueScenarioFactory":
        """Add an issue to the scenario.

        Args:
            title: Issue title
            description: Optional description
            priority: Optional priority level
            milestone: Optional milestone name

        Returns:
            Self for fluent chaining
        """
        IntegrationTestBase.create_issue(
            self.cli_runner,
            title=title,
            description=description,
            priority=priority,
            milestone=milestone,
        )
        return self

    def with_issues_by_priority(
        self,
        priorities: list[str] | None = None,
        milestone: str | None = None,
    ) -> "IssueScenarioFactory":
        """Add multiple issues, one for each priority level.

        Args:
            priorities: List of priority levels (default: all levels)
            milestone: Optional milestone for all issues

        Returns:
            Self for fluent chaining
        """
        if priorities is None:
            priorities = ["critical", "high", "medium", "low"]

        for priority in priorities:
            self.with_issue(
                title=f"{priority.title()} Priority Issue",
                priority=priority,
                milestone=milestone,
            )
        return self

    def with_bulk_issues(
        self,
        count: int,
        priority: str | None = None,
        milestone: str | None = None,
        title_prefix: str = "Issue",
    ) -> "IssueScenarioFactory":
        """Add multiple issues with similar properties.

        Args:
            count: Number of issues to create
            priority: Optional priority for all issues
            milestone: Optional milestone for all issues
            title_prefix: Prefix for issue titles

        Returns:
            Self for fluent chaining
        """
        for i in range(1, count + 1):
            self.with_issue(
                title=f"{title_prefix} {i}",
                priority=priority,
                milestone=milestone,
            )
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the complete scenario.

        Returns:
            Dictionary with issues and other state
        """
        return IntegrationTestBase.roadmap_state()


class ComplexWorkflowFactory:
    """Factory for building complete workflow scenarios."""

    def __init__(self, cli_runner: CliRunner):
        """Initialize factory with CLI runner.

        Args:
            cli_runner: Click CliRunner for executing CLI commands
        """
        self.cli_runner = cli_runner
        self.core = IntegrationTestBase.get_roadmap_core()
        self._milestone_factory: MilestoneScenarioFactory | None = None
        self._issue_factory: IssueScenarioFactory | None = None

    def with_initialized_roadmap(
        self, project_name: str = "Test Project"
    ) -> "ComplexWorkflowFactory":
        """Initialize roadmap.

        Args:
            project_name: Name for the project

        Returns:
            Self for fluent chaining
        """
        IntegrationTestBase.init_roadmap(self.cli_runner, project_name)
        self.core = IntegrationTestBase.get_roadmap_core()
        return self

    def with_release_plan(
        self,
        milestone_name: str = "v1-0",
        num_features: int = 3,
        num_bugs: int = 2,
    ) -> "ComplexWorkflowFactory":
        """Create a release planning scenario.

        Creates a milestone with feature and bug issues.

        Args:
            milestone_name: Name for the milestone
            num_features: Number of feature issues
            num_bugs: Number of bug issues

        Returns:
            Self for fluent chaining
        """
        # Create milestone
        IntegrationTestBase.create_milestone(
            self.cli_runner,
            name=milestone_name,
            headline=f"Release planning for {milestone_name}",
        )

        # Create feature issues (high priority)
        for i in range(1, num_features + 1):
            IntegrationTestBase.create_issue(
                self.cli_runner,
                title=f"Feature {i}",
                priority="high",
                milestone=milestone_name,
            )

        # Create bug fixes (medium priority)
        for i in range(1, num_bugs + 1):
            IntegrationTestBase.create_issue(
                self.cli_runner,
                title=f"Bug Fix {i}",
                priority="medium",
                milestone=milestone_name,
            )

        return self

    def with_sprint_planning(
        self,
        sprint_count: int = 3,
        issues_per_sprint: int = 5,
    ) -> "ComplexWorkflowFactory":
        """Create a sprint planning scenario.

        Creates multiple sprints with issues.

        Args:
            sprint_count: Number of sprints
            issues_per_sprint: Issues per sprint

        Returns:
            Self for fluent chaining
        """
        for sprint_num in range(1, sprint_count + 1):
            sprint_name = f"sprint-{sprint_num}"

            # Create sprint milestone
            IntegrationTestBase.create_milestone(
                self.cli_runner,
                name=sprint_name,
                headline=f"Sprint {sprint_num} work",
            )

            # Create issues for sprint
            for issue_num in range(1, issues_per_sprint + 1):
                priority = ["critical", "high", "medium", "low"][(issue_num - 1) % 4]
                IntegrationTestBase.create_issue(
                    self.cli_runner,
                    title=f"Task {issue_num} (Sprint {sprint_num})",
                    priority=priority,
                    milestone=sprint_name,
                )

        return self

    def with_backlog_items(self, count: int = 5) -> "ComplexWorkflowFactory":
        """Add unscheduled backlog items.

        Args:
            count: Number of backlog items

        Returns:
            Self for fluent chaining
        """
        for i in range(1, count + 1):
            IntegrationTestBase.create_issue(
                self.cli_runner,
                title=f"Backlog Item {i}",
                priority="low",
            )
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the complete workflow scenario.

        Returns:
            Dictionary with all state
        """
        return IntegrationTestBase.roadmap_state()


class TestDataBuilder:
    """Simple builder for one-off test data without factories."""

    @staticmethod
    def quick_setup(
        cli_runner: CliRunner,
        milestones: list[str] | None = None,
        issues_per_milestone: int = 0,
    ) -> dict[str, Any]:
        """Quick setup with milestones and optional issues.

        Args:
            cli_runner: Click CliRunner instance
            milestones: List of milestone names (creates them all)
            issues_per_milestone: Number of issues per milestone

        Returns:
            Complete roadmap state
        """
        IntegrationTestBase.init_roadmap(cli_runner)

        if milestones:
            for milestone in milestones:
                IntegrationTestBase.create_milestone(cli_runner, name=milestone)

                # Create issues if requested
                for i in range(1, issues_per_milestone + 1):
                    IntegrationTestBase.create_issue(
                        cli_runner,
                        title=f"Issue {i} for {milestone}",
                        milestone=milestone,
                    )

        return IntegrationTestBase.roadmap_state()

    @staticmethod
    def scenario_with_all_priorities(
        cli_runner: CliRunner,
        milestone: str | None = None,
    ) -> dict[str, Any]:
        """Create issues with all priority levels.

        Args:
            cli_runner: Click CliRunner instance
            milestone: Optional milestone to assign to

        Returns:
            Complete roadmap state
        """
        IntegrationTestBase.init_roadmap(cli_runner)

        for priority in ["critical", "high", "medium", "low"]:
            IntegrationTestBase.create_issue(
                cli_runner,
                title=f"{priority.title()} Priority",
                priority=priority,
                milestone=milestone,
            )

        return IntegrationTestBase.roadmap_state()
