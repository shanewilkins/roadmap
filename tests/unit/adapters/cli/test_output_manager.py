"""Tests for CLI output manager."""

from roadmap.adapters.cli.output_manager import OutputManager


class TestOutputManager:
    """Test OutputManager class."""

    def test_init_default(self):
        """Test OutputManager initialization with defaults."""
        manager = OutputManager()
        assert manager.format == "table"
        assert manager.output_file is None

    def test_init_with_format(self):
        """Test OutputManager initialization with custom format."""
        manager = OutputManager(format="json")
        assert manager.format == "json"

    def test_init_with_output_file(self, tmp_path):
        """Test OutputManager initialization with output file."""
        output_file = tmp_path / "output.json"
        manager = OutputManager(format="json", output_file=output_file)
        assert manager.output_file == output_file

    def test_output_manager_with_different_formats(self):
        """Test OutputManager with different output formats."""
        for fmt in ["table", "plain", "json", "csv", "markdown"]:
            manager = OutputManager(format=fmt)
            assert manager.format == fmt

    def test_output_manager_has_render_method(self):
        """Test that OutputManager has render_table method."""
        manager = OutputManager()
        assert hasattr(manager, "render_table")
        assert callable(manager.render_table)
