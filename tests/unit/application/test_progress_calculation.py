"""
Tests for automatic progress calculation functionality.

Tests the core progress calculation engine for milestones and projects
as specified in issue 515a927c.
"""

from roadmap.application.services.progress_service import ProgressCalculationEngine
from roadmap.domain import (
    Issue,
    Milestone,
    MilestoneStatus,
    Project,
    ProjectStatus,
    Status,
)


class TestProgressCalculationEngine:
    """Test the progress calculation engine."""

    def test_milestone_progress_calculation_count_based(self):
        """Test count-based milestone progress calculation."""
        engine = ProgressCalculationEngine(method="count_based")

        # Create test issues
        issues = [
            Issue(
                id="1", title="Issue 1", status=Status.DONE, milestone="test-milestone"
            ),
            Issue(
                id="2",
                title="Issue 2",
                status=Status.IN_PROGRESS,
                milestone="test-milestone",
            ),
            Issue(
                id="3", title="Issue 3", status=Status.TODO, milestone="test-milestone"
            ),
        ]

        # Create test milestone
        milestone = Milestone(name="test-milestone", description="Test milestone")

        # Update milestone progress
        engine.update_milestone_progress(milestone, issues)

        # Should be 33.33% (1 out of 3 issues done)
        assert abs(milestone.calculated_progress - 33.33) < 0.1
        assert milestone.status == MilestoneStatus.OPEN  # Not fully complete

    def test_milestone_progress_calculation_effort_weighted(self):
        """Test effort-weighted milestone progress calculation."""
        engine = ProgressCalculationEngine(method="effort_weighted")

        # Create test issues with different effort levels
        issues = [
            Issue(
                id="1",
                title="Issue 1",
                status=Status.DONE,
                milestone="test-milestone",
                estimated_hours=8.0,
            ),
            Issue(
                id="2",
                title="Issue 2",
                status=Status.IN_PROGRESS,
                milestone="test-milestone",
                estimated_hours=4.0,
            ),
            Issue(
                id="3",
                title="Issue 3",
                status=Status.TODO,
                milestone="test-milestone",
                estimated_hours=4.0,
            ),
        ]

        # Create test milestone
        milestone = Milestone(name="test-milestone", description="Test milestone")

        # Update milestone progress
        engine.update_milestone_progress(milestone, issues)

        # Should be 50% (8 hours out of 16 total hours done)
        assert abs(milestone.calculated_progress - 50.0) < 0.1

    def test_milestone_completion_status_propagation(self):
        """Test that milestone status updates when all issues are complete."""
        engine = ProgressCalculationEngine(method="effort_weighted")

        # Create test issues - all complete
        issues = [
            Issue(
                id="1",
                title="Issue 1",
                status=Status.DONE,
                milestone="complete-milestone",
                estimated_hours=4.0,
            ),
            Issue(
                id="2",
                title="Issue 2",
                status=Status.DONE,
                milestone="complete-milestone",
                estimated_hours=4.0,
            ),
        ]

        # Create test milestone
        milestone = Milestone(
            name="complete-milestone", description="Complete milestone"
        )

        # Update milestone progress
        engine.update_milestone_progress(milestone, issues)

        # Should be 100% complete and status should be closed
        assert milestone.calculated_progress == 100.0
        assert milestone.status == MilestoneStatus.CLOSED
        assert milestone.actual_end_date is not None

    def test_project_progress_calculation(self):
        """Test project progress calculation from milestones."""
        engine = ProgressCalculationEngine(method="effort_weighted")

        # Create test issues
        issues = [
            Issue(
                id="1",
                title="Issue 1",
                status=Status.DONE,
                milestone="m1",
                estimated_hours=8.0,
            ),
            Issue(
                id="2",
                title="Issue 2",
                status=Status.TODO,
                milestone="m1",
                estimated_hours=8.0,
            ),
            Issue(
                id="3",
                title="Issue 3",
                status=Status.DONE,
                milestone="m2",
                estimated_hours=4.0,
            ),
            Issue(
                id="4",
                title="Issue 4",
                status=Status.DONE,
                milestone="m2",
                estimated_hours=4.0,
            ),
        ]

        # Create test milestones
        milestones = [
            Milestone(name="m1", description="Milestone 1"),
            Milestone(name="m2", description="Milestone 2"),
        ]

        # Update milestone progress first
        for milestone in milestones:
            engine.update_milestone_progress(milestone, issues)

        # Create test project
        project = Project(
            id="test-project",
            name="Test Project",
            description="Test project",
            milestones=["m1", "m2"],
        )

        # Update project progress
        engine.update_project_progress(project, milestones, issues)

        # m1 should be 50% (8 out of 16 hours), m2 should be 100% (8 out of 8 hours)
        # Weighted average: (16 * 0.5 + 8 * 1.0) / 24 = 16/24 = 66.67%
        assert abs(project.calculated_progress - 66.67) < 0.1

    def test_project_completion_status_propagation(self):
        """Test that project status updates based on progress."""
        engine = ProgressCalculationEngine(method="effort_weighted")

        # Create completed milestones
        milestones = [
            Milestone(
                name="m1", description="Milestone 1", status=MilestoneStatus.CLOSED
            ),
            Milestone(
                name="m2", description="Milestone 2", status=MilestoneStatus.CLOSED
            ),
        ]

        # Mock the milestones to have 100% progress
        for milestone in milestones:
            milestone.calculated_progress = 100.0

        # Create test project
        project = Project(
            id="complete-project",
            name="Complete Project",
            description="Complete project",
            milestones=["m1", "m2"],
        )

        # Update project progress
        engine.update_project_progress(project, milestones, [])

        # Should be 100% complete and status should be completed
        assert project.calculated_progress == 100.0
        assert project.status == ProjectStatus.COMPLETED
        assert project.actual_end_date is not None

    def test_issue_dependency_updates(self):
        """Test that updating an issue triggers milestone and project updates."""
        engine = ProgressCalculationEngine(method="effort_weighted")

        # Create test data
        issue = Issue(
            id="1",
            title="Test Issue",
            status=Status.DONE,
            milestone="test-milestone",
            estimated_hours=8.0,
        )
        milestone = Milestone(name="test-milestone", description="Test milestone")
        project = Project(
            id="test-project", name="Test Project", milestones=["test-milestone"]
        )

        all_issues = [issue]
        all_milestones = [milestone]
        all_projects = [project]

        # Update dependencies
        updated_milestones, updated_projects = engine.update_issue_dependencies(
            issue, all_issues, all_milestones, all_projects
        )

        # Should update both milestone and project
        assert len(updated_milestones) == 1
        assert len(updated_projects) == 1
        assert updated_milestones[0].name == "test-milestone"
        assert updated_projects[0].id == "test-project"

    def test_recalculate_all_progress(self):
        """Test bulk recalculation of all progress."""
        engine = ProgressCalculationEngine(method="effort_weighted")

        # Create test data
        issues = [
            Issue(
                id="1",
                title="Issue 1",
                status=Status.DONE,
                milestone="m1",
                estimated_hours=4.0,
            ),
        ]
        milestones = [
            Milestone(name="m1", description="Milestone 1"),
        ]
        projects = [
            Project(id="p1", name="Project 1", milestones=["m1"]),
        ]

        # Recalculate all
        results = engine.recalculate_all_progress(issues, milestones, projects)

        # Should update both milestone and project
        assert results["milestones"] == 1
        assert results["projects"] == 1

    def test_progress_with_partial_completion(self):
        """Test progress calculation with partially completed issues."""
        engine = ProgressCalculationEngine(method="effort_weighted")

        # Create test issues with progress percentages
        issues = [
            Issue(
                id="1",
                title="Issue 1",
                status=Status.DONE,
                milestone="test-milestone",
                estimated_hours=4.0,
            ),
            Issue(
                id="2",
                title="Issue 2",
                status=Status.IN_PROGRESS,
                milestone="test-milestone",
                estimated_hours=4.0,
                progress_percentage=75.0,
            ),
        ]

        milestone = Milestone(name="test-milestone", description="Test milestone")

        # Update milestone progress
        engine.update_milestone_progress(milestone, issues)

        # Should be 87.5% (4.0 + 3.0) / 8.0 * 100
        assert abs(milestone.calculated_progress - 87.5) < 0.1


class TestEventSystem:
    """Test the progress event system."""

    def test_issue_update_event_handling(self):
        """Test that issue updates trigger proper events."""
        from roadmap.application.services.progress_service import ProgressEventSystem

        engine = ProgressCalculationEngine(method="effort_weighted")
        event_system = ProgressEventSystem(engine)

        # Create test data
        issue = Issue(
            id="1",
            title="Test Issue",
            status=Status.IN_PROGRESS,
            milestone="test-milestone",
        )
        milestone = Milestone(name="test-milestone", description="Test milestone")

        all_issues = [issue]
        all_milestones = [milestone]
        all_projects = []

        # Simulate issue status change
        changes = {"status": Status.DONE}

        # Handle the update event
        results = event_system.on_issue_updated(
            issue, changes, all_issues, all_milestones, all_projects
        )

        # Should return information about updates
        assert "milestones_updated" in results
        assert "projects_updated" in results

    def test_non_progress_affecting_change(self):
        """Test that non-progress changes don't trigger unnecessary updates."""
        from roadmap.application.services.progress_service import ProgressEventSystem

        engine = ProgressCalculationEngine(method="effort_weighted")
        event_system = ProgressEventSystem(engine)

        # Create test data
        issue = Issue(
            id="1", title="Test Issue", status=Status.TODO, milestone="test-milestone"
        )

        # Simulate non-progress affecting change (title change)
        changes = {"title": "Updated Title"}

        # Handle the update event
        results = event_system.on_issue_updated(issue, changes, [], [], [])

        # Should not trigger any updates
        assert len(results["milestones_updated"]) == 0
        assert len(results["projects_updated"]) == 0
