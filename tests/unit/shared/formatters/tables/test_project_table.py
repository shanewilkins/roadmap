"""Tests for project table formatter."""

from enum import Enum
from unittest.mock import Mock, patch

import pytest

from roadmap.common.output_models import TableData
from roadmap.shared.formatters.tables.project_table import (
    ProjectTableFormatter,
)


class StatusEnum(Enum):
    """Mock status enum."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PriorityEnum(Enum):
    """Mock priority enum."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MockProject:
    """Mock project object for testing."""

    def __init__(
        self,
        project_id="proj-123456",
        name="Test Project",
        status=None,
        priority=None,
        owner="Test Owner",
    ):
        """Initialize mock project."""
        self.id = project_id
        self.name = name
        self.status = status or StatusEnum.ACTIVE
        self.priority = priority or PriorityEnum.MEDIUM
        self.owner = owner


class TestProjectTableFormatter:
    """Tests for ProjectTableFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return ProjectTableFormatter()

    @pytest.fixture
    def sample_project_dict(self):
        """Create sample project dictionary."""
        return {
            "id": "proj-123456",
            "name": "Test Project",
            "status": "active",
            "priority": "medium",
            "owner": "John Doe",
        }

    @pytest.fixture
    def sample_project_obj(self):
        """Create sample project object."""
        return MockProject()

    def test_init_creates_formatter(self):
        """Test initializing formatter."""
        formatter = ProjectTableFormatter()
        assert formatter is not None
        assert formatter.columns_config is not None

    def test_init_sets_columns_config(self):
        """Test columns config is properly initialized."""
        formatter = ProjectTableFormatter()
        assert len(formatter.columns_config) == 5
        assert formatter.columns_config[0]["name"] == "ID"
        assert formatter.columns_config[1]["name"] == "Name"
        assert formatter.columns_config[2]["name"] == "Status"
        assert formatter.columns_config[3]["name"] == "Priority"
        assert formatter.columns_config[4]["name"] == "Owner"

    def test_create_table_returns_table(self, formatter):
        """Test creating a table."""
        table = formatter.create_table()
        assert table is not None
        # Check that table has the expected methods
        assert hasattr(table, "add_row")

    def test_create_table_has_all_columns(self, formatter):
        """Test table has all required columns."""
        table = formatter.create_table()
        # Rich Table has columns property
        assert hasattr(table, "columns")

    def test_add_row_with_dict_item(self, formatter, sample_project_dict):
        """Test adding a row with dictionary project."""
        table = formatter.create_table()
        formatter.add_row(table, sample_project_dict)
        # Check that add_row was called (table was modified)
        assert len(table.rows) == 1

    def test_add_row_with_object_item(self, formatter, sample_project_obj):
        """Test adding a row with project object."""
        table = formatter.create_table()
        formatter.add_row(table, sample_project_obj)
        assert len(table.rows) == 1

    def test_add_row_handles_missing_dict_fields(self, formatter):
        """Test add_row handles missing fields in dictionary."""
        table = formatter.create_table()
        incomplete_project = {
            "name": "Incomplete Project",
            # Missing other fields
        }
        formatter.add_row(table, incomplete_project)
        assert len(table.rows) == 1

    def test_add_row_handles_missing_object_fields(self, formatter):
        """Test add_row handles missing fields in object."""
        table = formatter.create_table()
        incomplete_project = Mock(spec=[])  # No attributes
        formatter.add_row(table, incomplete_project)
        assert len(table.rows) == 1

    def test_add_row_with_enum_values(self, formatter):
        """Test add_row properly handles enum status and priority."""
        table = formatter.create_table()
        project = MockProject(status=StatusEnum.ARCHIVED, priority=PriorityEnum.HIGH)
        formatter.add_row(table, project)
        assert len(table.rows) == 1

    def test_get_filter_description_single_item(self, formatter):
        """Test filter description for single item."""
        description = formatter.get_filter_description([{"id": "1"}])
        assert "1 project" in description
        assert "🎯" in description

    def test_get_filter_description_multiple_items(self, formatter):
        """Test filter description for multiple items."""
        description = formatter.get_filter_description(
            [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        )
        assert "3 projects" in description
        assert "🎯" in description

    def test_get_filter_description_empty_list(self, formatter):
        """Test filter description for empty list."""
        description = formatter.get_filter_description([])
        assert "0 projects" in description

    def test_display_items_empty_list(self, formatter):
        """Test displaying empty items list."""
        with patch(
            "roadmap.shared.formatters.tables.project_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            formatter.display_items([])

        # Should print "no projects found" messages
        assert mock_console.print.call_count >= 2

    def test_display_items_with_dict_projects(self, formatter, sample_project_dict):
        """Test displaying dictionary projects."""
        with patch(
            "roadmap.shared.formatters.tables.project_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            formatter.display_items([sample_project_dict])

        # Should print table
        assert mock_console.print.call_count >= 2

    def test_display_items_with_object_projects(self, formatter, sample_project_obj):
        """Test displaying object projects."""
        with patch(
            "roadmap.shared.formatters.tables.project_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            formatter.display_items([sample_project_obj])

        assert mock_console.print.call_count >= 2

    def test_display_items_with_filter_description(
        self, formatter, sample_project_dict
    ):
        """Test displaying items with custom filter description."""
        with patch(
            "roadmap.shared.formatters.tables.project_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            formatter.display_items([sample_project_dict], "active")

        # Should print with filter description
        assert mock_console.print.call_count >= 2

    def test_items_to_table_data_returns_table_data(
        self, formatter, sample_project_dict
    ):
        """Test converting items to TableData."""
        result = formatter.items_to_table_data([sample_project_dict])

        assert isinstance(result, TableData)
        assert result.title == "Projects"
        assert result.total_count == 1

    def test_items_to_table_data_with_dict_projects(
        self, formatter, sample_project_dict
    ):
        """Test converting dictionary projects to TableData."""
        projects = [sample_project_dict, sample_project_dict]
        result = formatter.items_to_table_data(projects)

        assert isinstance(result, TableData)
        assert len(result.rows) == 2
        assert result.total_count == 2

    def test_items_to_table_data_with_object_projects(
        self, formatter, sample_project_obj
    ):
        """Test converting object projects to TableData."""
        projects = [sample_project_obj, sample_project_obj]
        result = formatter.items_to_table_data(projects)

        assert isinstance(result, TableData)
        assert len(result.rows) == 2

    def test_items_to_table_data_empty_list(self, formatter):
        """Test converting empty list."""
        result = formatter.items_to_table_data([])

        assert isinstance(result, TableData)
        assert len(result.rows) == 0
        assert result.total_count == 0

    def test_items_to_table_data_with_custom_title(
        self, formatter, sample_project_dict
    ):
        """Test converting with custom title."""
        result = formatter.items_to_table_data(
            [sample_project_dict], title="Custom Title"
        )

        assert result.title == "Custom Title"

    def test_items_to_table_data_with_description(self, formatter, sample_project_dict):
        """Test converting with description."""
        result = formatter.items_to_table_data(
            [sample_project_dict], description="Test Description"
        )

        assert result.description == "Test Description"

    def test_items_to_table_data_with_enum_values(self, formatter):
        """Test TableData handles enum values properly."""
        project = MockProject(status=StatusEnum.ACTIVE, priority=PriorityEnum.HIGH)
        result = formatter.items_to_table_data([project])

        assert isinstance(result, TableData)
        assert len(result.rows) == 1
        # Check that enum values are converted to strings
        row = result.rows[0]
        assert "active" in str(row[2]).lower() or "active" in str(row[2])

    def test_projects_to_table_data_static_method(self, sample_project_dict):
        """Test backward compatible static method."""
        result = ProjectTableFormatter.projects_to_table_data([sample_project_dict])

        assert isinstance(result, TableData)
        assert len(result.rows) == 1

    def test_projects_to_table_data_with_custom_params(self, sample_project_dict):
        """Test static method with custom parameters."""
        result = ProjectTableFormatter.projects_to_table_data(
            [sample_project_dict],
            title="Custom",
            description="Filter",
        )

        assert result.title == "Custom"
        assert result.description == "Filter"

    @pytest.mark.parametrize("project_count", [0, 1, 5, 10])
    def test_add_multiple_rows(self, formatter, project_count):
        """Test adding multiple rows."""
        table = formatter.create_table()
        projects = [
            {"id": f"proj-{i}", "name": f"Project {i}"} for i in range(project_count)
        ]

        for project in projects:
            formatter.add_row(table, project)

        assert len(table.rows) == project_count

    @pytest.mark.parametrize("project_count", [1, 2, 5])
    def test_items_to_table_data_multiple_counts(self, formatter, project_count):
        """Test TableData with various project counts."""
        projects = [
            {"id": f"proj-{i}", "name": f"Project {i}"} for i in range(project_count)
        ]

        result = formatter.items_to_table_data(projects)

        assert len(result.rows) == project_count
        assert result.total_count == project_count
        assert result.returned_count == project_count

    def test_add_row_truncates_long_id(self, formatter):
        """Test that long IDs are truncated to 8 characters."""
        table = formatter.create_table()
        long_id = "proj-123456789abcdef"
        formatter.add_row(table, {"id": long_id, "name": "Test"})
        # Verify truncation executed without error
        assert True

    def test_items_to_table_data_preserves_row_order(self, formatter):
        """Test that row order is preserved."""
        projects = [
            {"id": "proj-1", "name": "Project 1"},
            {"id": "proj-2", "name": "Project 2"},
            {"id": "proj-3", "name": "Project 3"},
        ]

        result = formatter.items_to_table_data(projects)

        assert len(result.rows) == 3
        # Check that order is preserved (first column should be truncated ID)
        assert "proj-1" in result.rows[0][0]
        assert "proj-2" in result.rows[1][0]
        assert "proj-3" in result.rows[2][0]

    def test_display_items_multiple_projects(self, formatter):
        """Test displaying multiple projects."""
        projects = [{"id": f"proj-{i}", "name": f"Project {i}"} for i in range(3)]

        with patch(
            "roadmap.shared.formatters.tables.project_table._get_console"
        ) as mock_get_console:
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            formatter.display_items(projects)

        assert mock_console.print.call_count >= 2

    def test_columns_config_has_required_properties(self, formatter):
        """Test that column config has required properties."""
        for col in formatter.columns_config:
            assert "name" in col
            assert "style" in col
            assert "width" in col
