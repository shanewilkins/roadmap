"""Example tests using data factories.

Demonstrates how to use factories to build complex test scenarios with minimal
boilerplate and maximum clarity.
"""

import pytest

from tests.fixtures import (
    ComplexWorkflowFactory,
    IssueScenarioFactory,
    MilestoneScenarioFactory,
    TestDataBuilder,
)


class TestMilestoneScenarioFactory:
    """Examples using MilestoneScenarioFactory."""

    def test_single_milestone_with_fluent_api(self, cli_runner):
        """Test building single milestone using fluent API."""
        scenario = (
            MilestoneScenarioFactory(cli_runner)
            .with_initialized_roadmap()
            .with_milestone("v1-0", description="First release")
            .build()
        )

        assert len(scenario["milestones"]) == 1
        assert scenario["milestones"][0].name == "v1-0"

    def test_multiple_milestones_fluent(self, cli_runner):
        """Test building multiple milestones with one method call."""
        scenario = (
            MilestoneScenarioFactory(cli_runner)
            .with_initialized_roadmap()
            .with_multiple_milestones(count=3, name_prefix="sprint")
            .build()
        )

        assert len(scenario["milestones"]) == 3
        assert all(m.name.startswith("sprint-") for m in scenario["milestones"])

    def test_chaining_different_milestone_methods(self, cli_runner):
        """Test combining different milestone creation methods."""
        scenario = (
            MilestoneScenarioFactory(cli_runner)
            .with_initialized_roadmap()
            .with_milestone("v1-0", description="Current release")
            .with_multiple_milestones(count=2, name_prefix="sprint")
            .build()
        )

        assert len(scenario["milestones"]) == 3
        milestone_names = [m.name for m in scenario["milestones"]]
        assert "v1-0" in milestone_names
        assert any("sprint-" in name for name in milestone_names)


class TestIssueScenarioFactory:
    """Examples using IssueScenarioFactory."""

    def test_single_issue_with_fluent_api(self, cli_runner):
        """Test building single issue using fluent API."""
        scenario = (
            IssueScenarioFactory(cli_runner)
            .with_initialized_roadmap()
            .with_issue("My Task", priority="high")
            .build()
        )

        assert len(scenario["issues"]) == 1
        assert scenario["issues"][0].title == "My Task"

    def test_issues_by_priority(self, cli_runner):
        """Test creating one issue for each priority level."""
        scenario = (
            IssueScenarioFactory(cli_runner)
            .with_initialized_roadmap()
            .with_issues_by_priority()
            .build()
        )

        assert len(scenario["issues"]) == 4  # critical, high, medium, low
        priorities = {issue.priority.value for issue in scenario["issues"]}
        assert priorities == {"critical", "high", "medium", "low"}

    def test_issues_by_priority_with_milestone(self, cli_runner):
        """Test creating priority issues assigned to milestone."""
        from tests.fixtures import IntegrationTestBase

        (
            IssueScenarioFactory(cli_runner)
            .with_initialized_roadmap()
            .with_issue("Create milestone", milestone="v1-0")
        )

        # Manually create milestone (factory only creates issues)
        IntegrationTestBase.create_milestone(cli_runner, name="v1-0")

        # Now create issues for milestone
        scenario = (
            IssueScenarioFactory(cli_runner)
            .with_issues_by_priority(milestone="v1-0")
            .build()
        )

        assert all(issue.milestone == "v1-0" for issue in scenario["issues"])

    def test_bulk_issues(self, cli_runner):
        """Test creating many issues at once."""
        scenario = (
            IssueScenarioFactory(cli_runner)
            .with_initialized_roadmap()
            .with_bulk_issues(count=10, title_prefix="Task")
            .build()
        )

        assert len(scenario["issues"]) == 10
        titles = [issue.title for issue in scenario["issues"]]
        assert all("Task" in title for title in titles)

    def test_combining_issue_creation_methods(self, cli_runner):
        """Test combining different issue creation methods."""
        scenario = (
            IssueScenarioFactory(cli_runner)
            .with_initialized_roadmap()
            .with_issue("Critical Issue", priority="critical")
            .with_bulk_issues(count=3, priority="high", title_prefix="Feature")
            .with_bulk_issues(count=2, priority="low", title_prefix="Tech Debt")
            .build()
        )

        assert len(scenario["issues"]) == 6
        critical_issues = [
            i for i in scenario["issues"] if i.priority.value == "critical"
        ]
        assert len(critical_issues) == 1


class TestComplexWorkflowFactory:
    """Examples using ComplexWorkflowFactory for realistic scenarios."""

    def test_release_planning_workflow(self, cli_runner):
        """Test complete release planning scenario."""
        scenario = (
            ComplexWorkflowFactory(cli_runner)
            .with_initialized_roadmap()
            .with_release_plan(milestone_name="v2-0", num_features=4, num_bugs=2)
            .build()
        )

        assert len(scenario["milestones"]) == 1
        assert scenario["milestones"][0].name == "v2-0"
        assert len(scenario["issues"]) == 6  # 4 features + 2 bugs

        # Verify issues assigned correctly
        v2_issues = [i for i in scenario["issues"] if i.milestone == "v2-0"]
        assert len(v2_issues) == 6
        high_priority = [i for i in v2_issues if i.priority.value == "high"]
        assert len(high_priority) == 4  # Features

    def test_sprint_planning_workflow(self, cli_runner):
        """Test complete sprint planning scenario."""
        scenario = (
            ComplexWorkflowFactory(cli_runner)
            .with_initialized_roadmap()
            .with_sprint_planning(sprint_count=3, issues_per_sprint=5)
            .build()
        )

        assert len(scenario["milestones"]) == 3
        assert len(scenario["issues"]) == 15  # 3 sprints * 5 issues

        # Verify each sprint has issues
        for sprint_num in range(1, 4):
            sprint_issues = [
                i for i in scenario["issues"] if i.milestone == f"sprint-{sprint_num}"
            ]
            assert len(sprint_issues) == 5

    def test_complete_workflow_with_backlog(self, cli_runner):
        """Test workflow combining sprints and backlog."""
        scenario = (
            ComplexWorkflowFactory(cli_runner)
            .with_initialized_roadmap()
            .with_sprint_planning(sprint_count=2, issues_per_sprint=3)
            .with_backlog_items(count=5)
            .build()
        )

        assert len(scenario["milestones"]) == 2  # Just sprints
        assert len(scenario["issues"]) == 11  # 6 in sprints + 5 backlog

        # Verify backlog items have no milestone
        backlog = [i for i in scenario["issues"] if i.milestone is None]
        assert len(backlog) == 5


class TestQuickSetupBuilder:
    """Examples using TestDataBuilder for quick, simple setups."""

    def test_quick_setup_with_milestones(self, cli_runner):
        """Test quick setup with just milestones."""
        scenario = TestDataBuilder.quick_setup(
            cli_runner,
            milestones=["v1-0", "v2-0", "v3-0"],
        )

        assert len(scenario["milestones"]) == 3
        names = {m.name for m in scenario["milestones"]}
        assert names == {"v1-0", "v2-0", "v3-0"}

    def test_quick_setup_with_issues_per_milestone(self, cli_runner):
        """Test quick setup creating issues for each milestone."""
        scenario = TestDataBuilder.quick_setup(
            cli_runner,
            milestones=["v1-0", "v2-0"],
            issues_per_milestone=3,
        )

        assert len(scenario["milestones"]) == 2
        assert len(scenario["issues"]) == 6  # 2 milestones * 3 issues

    def test_scenario_with_all_priorities(self, cli_runner):
        """Test quick scenario with one issue per priority."""
        scenario = TestDataBuilder.scenario_with_all_priorities(cli_runner)

        assert len(scenario["issues"]) == 4
        priorities = {i.priority.value for i in scenario["issues"]}
        assert priorities == {"critical", "high", "medium", "low"}

    def test_scenario_with_all_priorities_in_milestone(self, cli_runner):
        """Test priority scenario assigned to milestone."""
        from tests.fixtures import IntegrationTestBase

        IntegrationTestBase.init_roadmap(cli_runner)
        IntegrationTestBase.create_milestone(cli_runner, name="TestMilestone")

        scenario = TestDataBuilder.scenario_with_all_priorities(
            cli_runner,
            milestone="TestMilestone",
        )

        # Note: Builder creates new init, so milestone was overwritten
        # This shows the limitation - builder is for simple cases
        assert len(scenario["issues"]) == 4


@pytest.mark.parametrize(
    "sprint_count,issues_per_sprint",
    [
        (1, 5),
        (2, 3),
        (3, 4),
    ],
)
def test_parametrized_sprint_planning(cli_runner, sprint_count, issues_per_sprint):
    """Test sprint planning with different parameters."""
    scenario = (
        ComplexWorkflowFactory(cli_runner)
        .with_initialized_roadmap()
        .with_sprint_planning(
            sprint_count=sprint_count,
            issues_per_sprint=issues_per_sprint,
        )
        .build()
    )

    assert len(scenario["milestones"]) == sprint_count
    assert len(scenario["issues"]) == sprint_count * issues_per_sprint
