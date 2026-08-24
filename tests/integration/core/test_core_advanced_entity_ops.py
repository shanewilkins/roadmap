"""Additional comprehensive tests for core roadmap functionality - targeting remaining uncovered areas."""

from datetime import UTC, datetime, timedelta

import pytest

from roadmap.core.domain import (
    Priority,
)
from roadmap.infrastructure.coordination.core import RoadmapCore

pytestmark = pytest.mark.unit


class TestRoadmapCoreAdvancedIssueOperations:
    """Test advanced issue operations and filtering."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create and initialize RoadmapCore for testing."""
        core = RoadmapCore(temp_dir)
        core.initialize()
        return core

    @pytest.mark.parametrize(
        "milestone_names,assign_rules,expected_unassigned_count",
        [
            (
                ["Milestone 1", "Milestone 2"],
                {
                    0: 0,
                    1: 0,
                    2: 1,
                },  # Assign issues 0,1 to milestone 0; issue 2 to milestone 1
                1,
            ),
            (
                ["Single Milestone"],
                {0: 0, 1: 0},  # Assign issues 0,1 to milestone 0
                2,
            ),
            (
                [],
                {},  # No milestones, no assignments
                4,
            ),
        ],
    )
    def test_get_issues_grouped_by_milestone(
        self, core, milestone_names, assign_rules, expected_unassigned_count
    ):
        """Test getting issues grouped by milestone with various configurations."""
        # Create milestones
        for name in milestone_names:
            core.milestones.create(name, f"Description for {name}")

        # Create issues
        created_issues = []
        issue_titles = ["Issue 1", "Issue 2", "Issue 3", "Backlog Issue"]
        priorities = [Priority.HIGH, Priority.MEDIUM, Priority.LOW, Priority.LOW]
        for title, priority in zip(issue_titles, priorities, strict=False):
            created_issues.append(core.issues.create(title=title, priority=priority))

        # Assign issues to milestones
        for issue_idx, milestone_idx in assign_rules.items():
            if milestone_idx < len(milestone_names):
                core.issues.assign_to_milestone(
                    created_issues[issue_idx].id, milestone_names[milestone_idx]
                )

        # Get grouped issues
        grouped = core.issues.get_grouped_by_milestone()

        assert "Backlog" in grouped
        assert len(grouped["Backlog"]) == expected_unassigned_count

        # Verify correct assignments if milestones exist
        if milestone_names:
            assert milestone_names[0] in grouped

    @pytest.mark.parametrize(
        "target_milestone,should_succeed",
        [
            ("Milestone 1", True),
            ("Milestone 2", True),
            (None, True),
            ("nonexistent-id", False),
        ],
    )
    def test_move_issue_to_milestone(self, core, target_milestone, should_succeed):
        """Test moving issues to different milestones."""
        # Create milestones
        core.milestones.create("Milestone 1", "Description 1")
        core.milestones.create("Milestone 2", "Description 2")

        # Create issue
        issue = core.issues.create(title="Test Issue", priority=Priority.MEDIUM)

        # Attempt to move to milestone
        result = core.issues.move_to_milestone(issue.id, target_milestone)
        assert result == should_succeed

        if should_succeed:
            updated_issue = core.issues.get(issue.id)
            assert updated_issue.milestone == target_milestone

    @pytest.mark.parametrize(
        "create_milestones,expected_result",
        [
            (
                [
                    ("Next Milestone", datetime.now(UTC) + timedelta(days=10)),
                    (
                        "Later Milestone",
                        datetime.now(UTC) + timedelta(days=20),
                    ),
                ],
                "Next Milestone",
            ),
            (
                [("Milestone Without Due Date", None)],
                None,
            ),
            (
                [
                    ("Milestone 1", None),
                    ("Milestone 2", None),
                ],
                None,
            ),
        ],
    )
    def test_get_next_milestone(self, core, create_milestones, expected_result):
        """Test getting the next upcoming milestone with various configurations."""
        # Create milestones
        for name, due_date in create_milestones:
            core.milestones.create(
                name=name, headline=f"Headline for {name}", due_date=due_date
            )

        # Get next milestone
        next_milestone = core.milestones.get_next()

        if expected_result is None:
            assert next_milestone is None
        else:
            assert next_milestone is not None
            assert next_milestone.name == expected_result
