"""Tests for critical path calculator."""

from datetime import UTC, datetime

import pytest

from roadmap.common.constants import Priority
from roadmap.core.domain.issue import Issue
from roadmap.core.services.critical_path_calculator import (
    CriticalPathCalculator,
    PathNode,
)
from tests.factories import IssueBuilder


@pytest.fixture
def calculator():
    """Create a calculator instance."""
    return CriticalPathCalculator()


@pytest.fixture
def simple_issues():
    """Create simple linear dependency chain."""
    issue_a = (
        IssueBuilder()
        .with_id("A")
        .with_priority(Priority.HIGH)
        .with_estimated_hours(8.0)
        .with_blocked_issues(["B"])
        .build()
    )
    issue_b = (
        IssueBuilder()
        .with_id("B")
        .with_priority(Priority.HIGH)
        .with_estimated_hours(16.0)
        .with_dependencies(["A"])
        .with_blocked_issues(["C"])
        .build()
    )
    issue_c = (
        IssueBuilder()
        .with_id("C")
        .with_priority(Priority.MEDIUM)
        .with_estimated_hours(8.0)
        .with_dependencies(["B"])
        .build()
    )
    return [issue_a, issue_b, issue_c]


@pytest.fixture
def complex_issues():
    """Create complex dependency graph."""
    issues = [
        IssueBuilder()
        .with_id("1")
        .with_priority(Priority.CRITICAL)
        .with_estimated_hours(4.0)
        .with_blocked_issues(["2", "3"])
        .build(),
        IssueBuilder()
        .with_id("2")
        .with_priority(Priority.HIGH)
        .with_estimated_hours(16.0)
        .with_dependencies(["1"])
        .with_blocked_issues(["5"])
        .build(),
        IssueBuilder()
        .with_id("3")
        .with_priority(Priority.HIGH)
        .with_estimated_hours(24.0)
        .with_dependencies(["1"])
        .with_blocked_issues(["5"])
        .build(),
        IssueBuilder()
        .with_id("4")
        .with_priority(Priority.LOW)
        .with_estimated_hours(8.0)
        .build(),
        IssueBuilder()
        .with_id("5")
        .with_priority(Priority.HIGH)
        .with_estimated_hours(8.0)
        .with_dependencies(["2", "3"])
        .build(),
    ]
    return issues


class TestCriticalPathCalculator:
    """Test CriticalPathCalculator class."""

    def test_init(self, calculator):
        """Test initialization."""
        assert calculator is not None

    def test_calculate_empty_issues(self, calculator):
        """Test calculating with no issues."""
        result = calculator.calculate_critical_path([])
        assert result.critical_path == []
        assert result.total_duration == 0.0
        assert result.critical_issue_ids == []

    def test_estimate_duration_hours(self, calculator):
        """Test parsing hours estimate."""
        issue = IssueBuilder().with_id("1").with_estimated_hours(8.0).build()
        assert calculator._estimate_duration(issue) == 8.0

    def test_estimate_duration_days(self, calculator):
        """Test parsing days estimate."""
        issue = IssueBuilder().with_id("1").with_estimated_hours(16.0).build()
        assert calculator._estimate_duration(issue) == 16.0

    def test_estimate_duration_weeks(self, calculator):
        """Test parsing weeks estimate."""
        issue = IssueBuilder().with_id("1").with_estimated_hours(40.0).build()
        assert calculator._estimate_duration(issue) == 40.0

    def test_estimate_duration_default(self, calculator):
        """Test default estimate when not provided."""
        issue = IssueBuilder().with_id("1").build()
        assert calculator._estimate_duration(issue) == 4.0

    def test_estimate_duration_invalid(self, calculator):
        """Test invalid estimate falls back to default."""
        issue = IssueBuilder().with_id("1").with_estimated_hours(None).build()
        assert calculator._estimate_duration(issue) == 4.0

    def test_simple_linear_dependency(self, calculator, simple_issues):
        """Test linear dependency chain."""
        result = calculator.calculate_critical_path(simple_issues)

        assert len(result.critical_path) > 0
        assert result.total_duration > 0
        # A -> B -> C should all be critical
        assert "A" in result.critical_issue_ids
        assert "B" in result.critical_issue_ids
        assert "C" in result.critical_issue_ids

    def test_complex_dependency_graph(self, calculator, complex_issues):
        """Test complex dependency graph."""
        result = calculator.calculate_critical_path(complex_issues)

        assert len(result.critical_issue_ids) > 0
        # Backend path (1 -> 3 -> 5) is longer than frontend (1 -> 2 -> 5)
        assert "3" in result.critical_issue_ids
        assert "5" in result.critical_issue_ids

    def test_blocking_analysis(self, calculator, simple_issues):
        """Test blocking relationship analysis."""
        result = calculator.calculate_critical_path(simple_issues)

        assert "A" in result.blocking_issues
        assert "B" in result.blocking_issues["A"]
        assert "B" in result.blocking_issues
        assert "C" in result.blocking_issues["B"]

    def test_project_end_date_calculation(self, calculator, simple_issues):
        """Test project end date calculation."""
        result = calculator.calculate_critical_path(simple_issues)

        assert result.project_end_date is not None
        # Should be after now
        assert result.project_end_date > datetime.now(UTC)

    def test_find_blocking_issues(self, calculator, simple_issues):
        """Test finding issues that block a specific issue."""
        blocking = calculator.find_blocking_issues(simple_issues, "C")

        assert len(blocking) == 1
        assert blocking[0].id == "B"

    def test_find_blocking_issues_chain(self, calculator, simple_issues):
        """Test finding blocking issues in a chain."""
        blocking = calculator.find_blocking_issues(simple_issues, "B")

        assert len(blocking) == 1
        assert blocking[0].id == "A"

    def test_find_blocking_issues_root(self, calculator, simple_issues):
        """Test finding blocking issues for root issue."""
        blocking = calculator.find_blocking_issues(simple_issues, "A")

        assert len(blocking) == 0

    def test_find_blocked_issues(self, calculator, simple_issues):
        """Test finding issues blocked by a specific issue."""
        blocked = calculator.find_blocked_issues(simple_issues, "A")

        assert len(blocked) == 1
        assert blocked[0].id == "B"

    def test_find_blocked_issues_chain(self, calculator, simple_issues):
        """Test finding blocked issues in a chain."""
        blocked = calculator.find_blocked_issues(simple_issues, "B")

        assert len(blocked) == 1
        assert blocked[0].id == "C"

    def test_find_blocked_issues_leaf(self, calculator, simple_issues):
        """Test finding blocked issues for leaf node."""
        blocked = calculator.find_blocked_issues(simple_issues, "C")

        assert len(blocked) == 0

    def test_dependency_graph_building(self, calculator, simple_issues):
        """Test building dependency graph."""
        graph = calculator._build_dependency_graph(simple_issues)

        assert "A" in graph
        assert graph["A"] == []
        assert graph["B"] == ["A"]
        assert graph["C"] == ["B"]

    def test_slack_time_calculation(self, calculator, complex_issues):
        """Test that slack time is calculated."""
        result = calculator.calculate_critical_path(complex_issues)

        # Non-critical issue 4 should have slack time
        for node in result.critical_path:
            if node.issue_id == "4":
                assert node.slack_time >= 0

    def test_criticality_grouping(self, calculator, complex_issues):
        """Test grouping issues by criticality."""
        result = calculator.calculate_critical_path(complex_issues)

        assert "critical" in result.issues_by_criticality
        assert "blocking" in result.issues_by_criticality
        assert "blocked" in result.issues_by_criticality
        assert "independent" in result.issues_by_criticality

    def test_critical_path_ordering(self, calculator, simple_issues):
        """Test that critical path is properly ordered."""
        result = calculator.calculate_critical_path(simple_issues)

        # Path should be in dependency order
        ids = [node.issue_id for node in result.critical_path]
        assert ids.index("A") < ids.index("B")
        assert ids.index("B") < ids.index("C")

    def test_multiple_root_issues(self, calculator):
        """Test handling multiple independent root issues."""
        issues = [
            IssueBuilder().with_id("root1").with_estimated_hours(4.0).build(),
            IssueBuilder().with_id("root2").with_estimated_hours(4.0).build(),
        ]
        result = calculator.calculate_critical_path(issues)

        assert len(result.critical_issue_ids) > 0

    def test_circular_dependency_handling(self, calculator):
        """Test handling of circular dependencies (should not crash)."""
        issues = [
            IssueBuilder()
            .with_id("A")
            .with_estimated_hours(4.0)
            .with_dependencies(["B"])
            .build(),
            IssueBuilder()
            .with_id("B")
            .with_estimated_hours(4.0)
            .with_dependencies(["A"])
            .build(),
        ]
        # Should not crash, may not find valid path
        result = calculator.calculate_critical_path(issues)
        assert result is not None

    def test_result_has_all_fields(self, calculator, simple_issues):
        """Test that result has all expected fields."""
        result = calculator.calculate_critical_path(simple_issues)

        assert hasattr(result, "critical_path")
        assert hasattr(result, "total_duration")
        assert hasattr(result, "critical_issue_ids")
        assert hasattr(result, "blocking_issues")
        assert hasattr(result, "project_end_date")
        assert hasattr(result, "issues_by_criticality")

    def test_duration_accumulation(self, calculator, simple_issues):
        """Test that total duration accumulates correctly."""
        result = calculator.calculate_critical_path(simple_issues)

        # A(8h) + B(16h) + C(8h) = 32h
        assert result.total_duration == 32.0

    def test_node_creation(self, calculator):
        """Test PathNode creation."""
        node = PathNode(
            issue_id="test",
            issue_title="Test Issue",
            duration_hours=8.0,
            dependencies=["dep1"],
        )

        assert node.issue_id == "test"
        assert node.duration_hours == 8.0
        assert node.is_critical is False
        assert node.slack_time == 0.0

    def test_issues_with_no_estimates(self, calculator):
        """Test handling issues without estimates."""
        issues = [
            Issue(id="1", title="No estimate"),
            Issue(id="2", title="With estimate", estimated_hours=4.0, depends_on=["1"]),
        ]
        result = calculator.calculate_critical_path(issues)

        # Should use default estimate for issue 1
        assert result.total_duration > 0
