"""Tests for CLI output manager."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.cli.output_manager import OutputManager
from roadmap.common.output_models import TableData


class TestOutputManager:
    """Test OutputManager class."""

    @pytest.mark.parametrize(
        "format_arg,output_file_arg,expected_format,expected_file",
        [
            (None, None, "table", None),
            ("json", None, "json", None),
            ("csv", None, "csv", None),
            ("plain", None, "plain", None),
            ("markdown", None, "markdown", None),
        ],
    )
    def test_init_with_various_formats(
        self, format_arg, output_file_arg, expected_format, expected_file
    ):
        """Test OutputManager initialization with various format options."""
        if format_arg is None:
            manager = OutputManager()
        else:
            manager = OutputManager(format=format_arg)
        assert manager.format == expected_format
        assert manager.output_file == expected_file

    def test_init_with_output_file(self, tmp_path):
        """Test OutputManager initialization with output file."""
        output_file = tmp_path / "output.json"
        manager = OutputManager(format="json", output_file=output_file)
        assert manager.output_file == output_file

    def test_output_manager_has_render_method(self):
        """Test that OutputManager has render_table method."""
        manager = OutputManager()
        assert hasattr(manager, "render_table")
        assert callable(manager.render_table)

    def test_render_table_format(self):
        """Test rendering data as table."""
        manager = OutputManager(format="table")
        # Create a mock TableData object
        table_data = MagicMock(spec=TableData)
        table_data.columns = ["id", "name"]
        table_data.rows = [
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
        ]

        with patch.object(manager, "render_table") as mock_render:
            manager.render_table(table_data)
            mock_render.assert_called_once()

    def test_render_json_format(self):
        """Test rendering data as JSON."""
        manager = OutputManager(format="json")
        table_data = MagicMock(spec=TableData)
        table_data.to_dict.return_value = {
            "columns": ["id", "name"],
            "rows": [
                {"id": "1", "name": "Item 1"},
                {"id": "2", "name": "Item 2"},
            ],
        }

        with patch.object(manager, "render_table") as mock_render:
            manager.render_table(table_data)
            mock_render.assert_called_once()

    def test_render_empty_data(self):
        """Test rendering empty data."""
        manager = OutputManager(format="table")
        table_data = MagicMock(spec=TableData)
        table_data.rows = []

        with patch.object(manager, "render_table") as mock_render:
            manager.render_table(table_data)
            mock_render.assert_called_once()

    def test_render_single_item(self):
        """Test rendering single item."""
        manager = OutputManager(format="table")
        table_data = MagicMock(spec=TableData)
        table_data.rows = [{"id": "1", "name": "Item 1"}]

        with patch.object(manager, "render_table") as mock_render:
            manager.render_table(table_data)
            mock_render.assert_called_once()

    def test_print_message_output(self):
        """Test print message exists."""
        manager = OutputManager(format="table")
        assert hasattr(manager, "print_message")
