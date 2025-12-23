"""Tests for handling large datasets - tests service logic, not CLI output parsing."""

from roadmap.core.domain import Issue, Milestone, Priority, Status


class TestLargeDatasetHandling:
    """Test handling of large datasets in services."""

    def test_large_issue_creation(self):
        """Test creating many issues efficiently."""
        num_issues = 50
        issues = []

        for i in range(num_issues):
            priority = [Priority.LOW, Priority.MEDIUM, Priority.HIGH][i % 3]
            issue = Issue(title=f"Issue {i+1}", priority=priority)
            issues.append(issue)

        # Verify all created
        assert len(issues) == num_issues

        # Verify priorities distributed correctly
        low_count = sum(1 for issue in issues if issue.priority == Priority.LOW)
        medium_count = sum(1 for issue in issues if issue.priority == Priority.MEDIUM)
        high_count = sum(1 for issue in issues if issue.priority == Priority.HIGH)

        assert low_count == num_issues // 3 or low_count == (num_issues // 3) + 1
        assert medium_count == num_issues // 3 or medium_count == (num_issues // 3) + 1
        assert high_count == num_issues // 3 or high_count == (num_issues // 3) + 1

    def test_milestone_assignment_large_dataset(self):
        """Test assigning many issues to milestones."""
        num_issues = 50
        num_milestones = 10

        # Create milestones
        milestones = [Milestone(name=f"Milestone {i+1}") for i in range(num_milestones)]

        # Create issues and assign to milestones
        issues = []
        for i in range(num_issues):
            milestone_name = milestones[i % len(milestones)].name
            issue = Issue(
                title=f"Issue {i+1}",
                milestone=milestone_name,
                priority=[Priority.LOW, Priority.MEDIUM, Priority.HIGH][i % 3],
            )
            issues.append(issue)

        # Verify all assigned
        assert len(issues) == num_issues
        assert all(issue.milestone is not None for issue in issues)

        # Verify distribution across milestones
        for milestone in milestones:
            issues_for_milestone = [i for i in issues if i.milestone == milestone.name]
            assert len(issues_for_milestone) == num_issues // num_milestones

    def test_status_counting_large_dataset(self):
        """Test counting issues by status in large dataset."""
        num_issues = 50

        # Create issues with various statuses
        issues = []
        for i in range(num_issues):
            # Distribute statuses: 20 TODO, 15 IN_PROGRESS, 15 CLOSED
            if i < 20:
                status = Status.TODO
            elif i < 35:
                status = Status.IN_PROGRESS
            else:
                status = Status.CLOSED

            issue = Issue(title=f"Issue {i+1}", status=status)
            issues.append(issue)

        # Count by status
        todo_count = sum(1 for issue in issues if issue.status == Status.TODO)
        in_progress_count = sum(
            1 for issue in issues if issue.status == Status.IN_PROGRESS
        )
        closed_count = sum(1 for issue in issues if issue.status == Status.CLOSED)

        assert todo_count == 20
        assert in_progress_count == 15
        assert closed_count == 15
        assert todo_count + in_progress_count + closed_count == num_issues

    def test_mixed_operations_large_dataset(self):
        """Test mixed operations on large dataset."""
        # Create 50 issues with various properties
        issues = [
            Issue(
                title=f"Issue {i+1}",
                milestone=f"v{(i % 10) + 1}.0",
                status=[Status.TODO, Status.IN_PROGRESS, Status.CLOSED][i % 3],
                priority=[Priority.LOW, Priority.MEDIUM, Priority.HIGH][i % 3],
                estimated_hours=(i % 8) + 1
                if i % 5 != 0
                else None,  # 80% have estimates
            )
            for i in range(50)
        ]

        # Verify totals
        assert len(issues) == 50
        assert len({issue.milestone for issue in issues}) == 10  # 10 unique milestones

        # Verify status distribution
        todo_count = sum(1 for issue in issues if issue.status == Status.TODO)
        assert todo_count > 0

        # Verify estimate distribution
        estimated_count = sum(
            1 for issue in issues if issue.estimated_hours is not None
        )
        assert estimated_count == 40  # 80% of 50
