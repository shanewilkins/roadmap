"""Unit tests for table formatting and conversion."""

from unittest.mock import Mock

from roadmap.common.formatters.tables import (
    IssueTableFormatter,
    MilestoneTableFormatter,
    ProjectTableFormatter,
)
from roadmap.core.domain import Issue, Priority, Status


class TestIssueTableFormatter:
    """Test issue table formatting."""

    def create_sample_issue(self, **kwargs):
        """Create a sample issue for testing."""
        defaults = {
            "id": "ISS-123",
            "title": "Test Issue",
            "status": Status.TODO,
            "priority": Priority.MEDIUM,
            "assignee": "testuser",
            "estimated_hours": 8.0,
            "milestone_name": "v1.0",
            "progress_display": "50%",
            "progress_percentage": 50,
            "estimated_time_display": "1d",
            "is_backlog": False,
        }
        defaults.update(kwargs)
        return Mock(spec=Issue, **defaults)

    def test_issues_to_table_data(self):
        """Test converting issues to TableData."""
        issue = self.create_sample_issue()
        table_data = IssueTableFormatter.issues_to_table_data(
            [issue], title="Test Issues"
        )

        assert table_data is not None
        assert table_data.title == "Test Issues"
        assert len(table_data.rows) == 1
        assert (
            len(table_data.columns) == 9
        )  # 9 columns defined (including comment_count)

    def test_issues_to_table_data_with_multiple_issues(self):
        """Test converting multiple issues to TableData."""
        issues = [
            self.create_sample_issue(id="ISS-1", title="First"),
            self.create_sample_issue(id="ISS-2", title="Second"),
            self.create_sample_issue(id="ISS-3", title="Third"),
        ]
        table_data = IssueTableFormatter.issues_to_table_data(issues)

        assert len(table_data.rows) == 3
        assert table_data.total_count == 3
        assert table_data.returned_count == 3

    def test_issues_to_table_data_empty_list(self):
        """Test converting empty issue list."""
        table_data = IssueTableFormatter.issues_to_table_data([], title="Empty")

        assert table_data.title == "Empty"
        assert len(table_data.rows) == 0
        assert table_data.total_count == 0

    def test_issues_to_table_data_column_definitions(self):
        """Test that column definitions are correct - core columns."""
        issue = self.create_sample_issue()
        table_data = IssueTableFormatter.issues_to_table_data([issue])

        # Check column names
        column_names = [col.name for col in table_data.columns]
        assert "id" in column_names
        assert "title" in column_names
        assert "priority" in column_names
        assert "status" in column_names

    def test_issues_to_table_data_column_definitions_progress(self):
        """Test that column definitions are correct - progress and assignee."""
        issue = self.create_sample_issue()
        table_data = IssueTableFormatter.issues_to_table_data([issue])

        # Check column names
        column_names = [col.name for col in table_data.columns]
        assert "progress" in column_names
        assert "assignee" in column_names

    def test_issues_to_table_data_column_definitions_time_and_milestone(self):
        """Test that column definitions are correct - estimate and milestone."""
        issue = self.create_sample_issue()
        table_data = IssueTableFormatter.issues_to_table_data([issue])

        # Check column names
        column_names = [col.name for col in table_data.columns]
        assert "estimate" in column_names
        assert "milestone" in column_names

    def test_issues_to_table_data_row_content(self):
        """Test that row content matches issue data."""
        issue = self.create_sample_issue(
            id="ISS-123", title="Test Issue", assignee="alice"
        )
        table_data = IssueTableFormatter.issues_to_table_data([issue])

        row = table_data.rows[0]
        assert row[0] == "ISS-123"  # id
        assert row[1] == "Test Issue"  # title
        assert row[5] == "alice"  # assignee

    def test_issues_to_table_data_with_none_assignee(self):
        """Test handling of None assignee."""
        issue = self.create_sample_issue(assignee=None)
        table_data = IssueTableFormatter.issues_to_table_data([issue])

        row = table_data.rows[0]
        assert row[5] == "Unassigned"  # Should show "Unassigned"

    def test_display_issues_not_available(self):
        """Test display_issues method exists."""
        # Just verify the method is callable
        assert hasattr(IssueTableFormatter, "display_issues")
        assert callable(IssueTableFormatter.display_issues)


class TestMilestoneTableFormatter:
    """Test milestone table formatting."""

    def create_sample_milestone(self, **kwargs):
        """Create a sample milestone for testing."""
        defaults = {
            "name": "v1.0",
            "description": "First release",
            "status": Mock(value="open"),
            "due_date": None,
            "calculated_progress": 50,
        }
        defaults.update(kwargs)
        return Mock(**defaults)

    def test_milestones_to_table_data(self):
        """Test converting milestones to TableData."""
        milestone = self.create_sample_milestone()
        table_data = MilestoneTableFormatter.milestones_to_table_data(
            [milestone], title="Test Milestones"
        )

        assert table_data is not None
        assert table_data.title == "Test Milestones"
        assert len(table_data.rows) == 1

    def test_milestones_to_table_data_multiple(self):
        """Test converting multiple milestones."""
        milestones = [
            self.create_sample_milestone(name="v1.0"),
            self.create_sample_milestone(name="v2.0"),
        ]
        table_data = MilestoneTableFormatter.milestones_to_table_data(milestones)

        assert len(table_data.rows) == 2
        assert table_data.total_count == 2

    def test_milestones_to_table_data_empty(self):
        """Test converting empty milestone list."""
        table_data = MilestoneTableFormatter.milestones_to_table_data([])

        assert len(table_data.rows) == 0
        assert table_data.total_count == 0


class TestProjectTableFormatter:
    """Test project table formatting."""

    def test_projects_to_table_data_with_dict(self):
        """Test converting project dicts to TableData."""
        projects = [
            {
                "id": "proj-1",
                "name": "Project 1",
                "status": "active",
                "priority": "high",
                "owner": "alice",
            },
        ]
        table_data = ProjectTableFormatter.projects_to_table_data(
            projects, title="Projects"
        )

        assert table_data is not None
        assert table_data.title == "Projects"
        assert len(table_data.rows) == 1

    def test_projects_to_table_data_with_objects(self):
        """Test converting project objects to TableData."""
        project = Mock()
        project.id = "proj-1"
        project.name = "Project 1"
        project.status = "active"
        project.priority = "high"
        project.owner = "alice"

        table_data = ProjectTableFormatter.projects_to_table_data([project])

        assert len(table_data.rows) == 1

    def test_projects_to_table_data_with_enum_values(self):
        """Test converting projects with enum status/priority."""
        project = Mock()
        project.id = "proj-1"
        project.name = "Project 1"
        project.status = Mock(value="active")  # Enum
        project.priority = Mock(value="high")  # Enum
        project.owner = "alice"

        table_data = ProjectTableFormatter.projects_to_table_data([project])

        row = table_data.rows[0]
        # Should extract .value from enums
        assert "active" in row or row[2] == "active"

    def test_projects_to_table_data_empty(self):
        """Test converting empty project list."""
        table_data = ProjectTableFormatter.projects_to_table_data([])

        assert len(table_data.rows) == 0
        assert table_data.total_count == 0
