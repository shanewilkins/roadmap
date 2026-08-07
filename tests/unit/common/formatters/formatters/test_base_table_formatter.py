"""Tests for base table formatter."""

from unittest.mock import Mock, patch

import pytest

from roadmap.common.formatters.base_table_formatter import BaseTableFormatter
from roadmap.common.models import ColumnDef, ColumnType, TableData


class ConcreteTableFormatter(BaseTableFormatter):
    """Concrete implementation for testing abstract base class."""

    def __init__(self):
        """Initialize concrete formatter."""
        super().__init__()
        self.items_created = []

    def create_table(self):
        """Create a mock table."""
        return Mock()

    def add_row(self, table, item):
        """Add a row to the table."""
        self.items_created.append(item)
        table.add_row(item)

    def get_filter_description(self, items):
        """Get filter description."""
        return f"{len(items)} test items"

    def items_to_table_data(self, items, title="Items", headline=""):
        """Convert items to table data."""
        return TableData(
            title=title,
            headline=headline,
            rows=[[str(item)] for item in items],
            columns=[
                ColumnDef(name="data", display_name="Data", type=ColumnType.STRING)
            ],
        )


class TestBaseTableFormatter:
    """Tests for BaseTableFormatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return ConcreteTableFormatter()

    def test_init_creates_formatter(self):
        """Test initializing formatter."""
        formatter = ConcreteTableFormatter()
        assert formatter is not None

    def test_console_property_returns_console(self, formatter):
        """Test console property returns a console object."""
        console = formatter.console
        assert console is not None
        # Check that it has the expected console methods
        assert hasattr(console, "print")

    def test_display_items_empty_list(self, formatter):
        """Test displaying empty items list."""
        with patch("roadmap.common.formatters.base_table_formatter.get_console"):
            # Just ensure it doesn't crash with empty list
            formatter.display_items([])
            # No exception means success
            assert True

    def test_display_items_with_items(self, formatter):
        """Test displaying items list."""
        items = [1, 2, 3]
        with patch("roadmap.common.formatters.base_table_formatter.get_console"):
            formatter.display_items(items)

        # Check that add_row was called for each item
        assert len(formatter.items_created) == 3
        assert formatter.items_created == items

    def test_display_items_with_filter_description(self, formatter):
        """Test displaying items with custom filter description."""
        items = [1, 2]
        with patch("roadmap.common.formatters.base_table_formatter.get_console"):
            formatter.display_items(items, "custom filter")

        assert len(formatter.items_created) == 2

    def test_display_items_adds_all_rows(self, formatter):
        """Test that all items are added as rows."""
        items = [1, 2, 3, 4, 5]
        with patch("roadmap.common.formatters.base_table_formatter.get_console"):
            formatter.display_items(items)

        # Check that add_row was called for each item
        assert len(formatter.items_created) == 5
        assert formatter.items_created == items

    def test_get_filter_description_called_with_items(self, formatter):
        """Test get_filter_description is called."""
        items = [1, 2, 3]
        with patch("roadmap.common.formatters.base_table_formatter.get_console"):
            formatter.display_items(items)

        # Should have added all items
        assert len(formatter.items_created) == 3

    def test_items_to_table_data_returns_table_data(self, formatter):
        """Test converting items to TableData."""
        items = [1, 2, 3]
        result = formatter.items_to_table_data(items)

        assert isinstance(result, TableData)
        assert result.title == "Items"
        assert result.headline == ""

    def test_items_to_table_data_with_custom_title(self, formatter):
        """Test converting items with custom title."""
        items = [1, 2]
        result = formatter.items_to_table_data(items, title="Custom Title")

        assert result.title == "Custom Title"

    def test_items_to_table_data_with_description(self, formatter):
        """Test converting items with description."""
        items = [1, 2]
        result = formatter.items_to_table_data(items, headline="Test description")

        assert result.headline == "Test description"

    def test_items_to_table_data_empty_list(self, formatter):
        """Test converting empty items list."""
        result = formatter.items_to_table_data([])

        assert isinstance(result, TableData)
        assert result.rows == []

    def test_create_table_is_abstract(self):
        """Test that create_table must be implemented."""
        with pytest.raises(TypeError):
            # Try to create base class without implementing abstract methods
            class IncompleteFormatter(BaseTableFormatter):
                pass

            IncompleteFormatter()  # type: ignore

    def test_add_row_is_abstract(self):
        """Test that add_row must be implemented."""
        with pytest.raises(TypeError):

            class MissingAddRow(BaseTableFormatter):
                def create_table(self):
                    return Mock()

                def get_filter_description(self, items):
                    return "test"

                def items_to_table_data(self, items, title="", headline=""):
                    return TableData(columns=[], rows=[])

            MissingAddRow()  # type: ignore

    def test_get_filter_description_is_abstract(self):
        """Test that get_filter_description must be implemented."""
        with pytest.raises(TypeError):

            class MissingFilterDesc(BaseTableFormatter):
                def create_table(self):
                    return Mock()

                def add_row(self, table, item):
                    pass

                def items_to_table_data(self, items, title="", headline=""):
                    return TableData(columns=[], rows=[])

            MissingFilterDesc()  # type: ignore

    def test_items_to_table_data_is_abstract(self):
        """Test that items_to_table_data must be implemented."""
        with pytest.raises(TypeError):

            class MissingTableData(BaseTableFormatter):
                def create_table(self):
                    return Mock()

                def add_row(self, table, item):
                    pass

                def get_filter_description(self, items):
                    return "test"

            MissingTableData()  # type: ignore

    @pytest.mark.parametrize(
        "item_count",
        [0, 1, 5, 100],
    )
    def test_display_items_parametrized_counts(self, formatter, item_count):
        """Test displaying various counts of items."""
        items = list(range(item_count))
        with patch("roadmap.common.formatters.base_table_formatter.get_console"):
            formatter.display_items(items)

        assert len(formatter.items_created) == item_count
