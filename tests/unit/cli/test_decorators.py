"""
Tests for Click command decorators - output support and formatting.
"""

import click
import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.decorators import add_output_flags, with_output_support
from roadmap.common.output_models import ColumnDef, ColumnType, TableData


class TestWithOutputSupport:
    """Tests for with_output_support decorator."""

    @pytest.fixture
    def sample_command(self):
        """Create a sample command with output support."""

        @click.command()
        @with_output_support(
            available_columns=["id", "name", "status"],
            column_types={
                "id": ColumnType.INTEGER,
                "name": ColumnType.STRING,
                "status": ColumnType.ENUM,
            },
        )
        def list_items():
            # Return sample table (don't accept the format/columns/sort_by/filter params)
            cols = [
                ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER),
                ColumnDef(name="name", display_name="Name", type=ColumnType.STRING),
                ColumnDef(name="status", display_name="Status", type=ColumnType.ENUM),
            ]
            rows = [
                [1, "Alice", "active"],
                [2, "Bob", "inactive"],
                [3, "Charlie", "active"],
            ]
            return TableData(columns=cols, rows=rows, title="Items")

        return list_items

    def test_decorator_adds_format_option(self, sample_command):
        """Test that decorator adds --format option."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--help"])
        assert "--format" in result.output

    def test_decorator_adds_columns_option(self, sample_command):
        """Test that decorator adds --columns option."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--help"])
        assert "--columns" in result.output

    def test_decorator_adds_sort_option(self, sample_command):
        """Test that decorator adds --sort-by option."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--help"])
        assert "--sort-by" in result.output

    def test_decorator_adds_filter_option(self, sample_command):
        """Test that decorator adds --filter option."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--help"])
        assert "--filter" in result.output

    def test_default_format_rich(self, sample_command):
        """Test default format is rich."""
        runner = CliRunner()
        result = runner.invoke(sample_command, [])
        assert result.exit_code == 0

    def test_format_plain_text(self, sample_command):
        """Test plain text format output."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--format", "plain"])
        assert result.exit_code == 0
        # Plain text should have ASCII characters
        assert "ID" in result.output or "id" in result.output.lower()

    def test_format_json(self, sample_command):
        """Test JSON format output."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--format", "json"])
        assert result.exit_code == 0
        # JSON should have JSON structure
        assert "{" in result.output or "[" in result.output

    def test_format_csv(self, sample_command):
        """Test CSV format output."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--format", "csv"])
        assert result.exit_code == 0
        # CSV should have comma-separated values
        assert "," in result.output

    def test_format_markdown(self, sample_command):
        """Test Markdown format output."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--format", "markdown"])
        assert result.exit_code == 0
        # Markdown should have pipe delimiters
        assert "|" in result.output

    def test_columns_selection(self, sample_command):
        """Test --columns flag."""
        runner = CliRunner()
        result = runner.invoke(
            sample_command, ["--format", "plain", "--columns", "id,name"]
        )
        assert result.exit_code == 0
        # Output should have selected columns
        lines = result.output.split("\n")
        header = [line for line in lines if "ID" in line or "Name" in line]
        assert len(header) > 0

    def test_sort_by(self, sample_command):
        """Test --sort-by flag."""
        runner = CliRunner()
        result = runner.invoke(
            sample_command, ["--format", "plain", "--sort-by", "name:asc"]
        )
        assert result.exit_code == 0

    def test_filter(self, sample_command):
        """Test --filter flag."""
        runner = CliRunner()
        result = runner.invoke(
            sample_command, ["--format", "plain", "--filter", "status=active"]
        )
        assert result.exit_code == 0

    def test_combined_options(self, sample_command):
        """Test using multiple options together."""
        runner = CliRunner()
        result = runner.invoke(
            sample_command,
            [
                "--format",
                "json",
                "--columns",
                "id,name",
                "--sort-by",
                "name:desc",
            ],
        )
        assert result.exit_code == 0

    def test_invalid_format(self, sample_command):
        """Test error on invalid format."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--format", "invalid"])
        assert result.exit_code != 0

    def test_invalid_column(self, sample_command):
        """Test error on invalid column."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--columns", "unknown"])
        assert result.exit_code != 0

    def test_invalid_sort_column(self, sample_command):
        """Test error on invalid sort column."""
        runner = CliRunner()
        result = runner.invoke(sample_command, ["--sort-by", "unknown"])
        assert result.exit_code != 0

    def test_non_table_return_passthrough(self):
        """Test that non-TableData return values pass through unchanged."""

        @click.command()
        @with_output_support(available_columns=["id"])
        def string_command():
            click.echo("simple string")

        runner = CliRunner()
        result = runner.invoke(string_command, [])
        assert result.exit_code == 0
        assert "simple string" in result.output


class TestAddOutputFlags:
    """Tests for add_output_flags decorator."""

    def test_decorator_adds_flags(self):
        """Test that decorator adds output flags."""

        @click.command()
        @add_output_flags(available_columns=["id", "name"])
        def my_command(format, columns, sort_by, filter):
            click.echo(f"Format: {format}, Columns: {columns}")

        runner = CliRunner()
        result = runner.invoke(my_command, ["--help"])
        assert "--format" in result.output
        assert "--columns" in result.output
        assert "--sort-by" in result.output
        assert "--filter" in result.output


class TestIntegrationWithRealCommands:
    """Integration tests with realistic command scenarios."""

    def test_issue_list_with_formatting(self):
        """Test issue-list-like command with all output options."""

        @click.command()
        @with_output_support(
            available_columns=["id", "title", "status", "created"],
            column_types={
                "id": ColumnType.INTEGER,
                "title": ColumnType.STRING,
                "status": ColumnType.ENUM,
                "created": ColumnType.DATETIME,
            },
        )
        def issue_list():
            cols = [
                ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER),
                ColumnDef(name="title", display_name="Title", type=ColumnType.STRING),
                ColumnDef(name="status", display_name="Status", type=ColumnType.ENUM),
                ColumnDef(
                    name="created", display_name="Created", type=ColumnType.DATETIME
                ),
            ]
            rows = [
                [1, "Fix bug", "open", "2025-01-01"],
                [2, "Add feature", "closed", "2025-01-02"],
                [3, "Update docs", "open", "2025-01-03"],
            ]
            return TableData(columns=cols, rows=rows, title="Issues")

        runner = CliRunner()

        # Test with default format
        result = runner.invoke(issue_list, [])
        assert result.exit_code == 0

        # Test with JSON export
        result = runner.invoke(issue_list, ["--format", "json"])
        assert result.exit_code == 0
        assert "{" in result.output

        # Test with CSV export
        result = runner.invoke(issue_list, ["--format", "csv"])
        assert result.exit_code == 0
        assert "," in result.output

        # Test with column selection
        result = runner.invoke(
            issue_list, ["--format", "plain", "--columns", "id,title"]
        )
        assert result.exit_code == 0

        # Test with sorting
        result = runner.invoke(
            issue_list, ["--format", "plain", "--sort-by", "title:asc"]
        )
        assert result.exit_code == 0

    def test_project_list_with_all_options(self):
        """Test project-list-like command using all options."""

        @click.command()
        @with_output_support(
            available_columns=["name", "status", "progress"],
            column_types={
                "name": ColumnType.STRING,
                "status": ColumnType.ENUM,
                "progress": ColumnType.INTEGER,
            },
        )
        def project_list():
            cols = [
                ColumnDef(name="name", display_name="Project", type=ColumnType.STRING),
                ColumnDef(name="status", display_name="Status", type=ColumnType.ENUM),
                ColumnDef(
                    name="progress", display_name="Progress %", type=ColumnType.INTEGER
                ),
            ]
            rows = [
                ["Project A", "active", 75],
                ["Project B", "planning", 20],
                ["Project C", "active", 90],
            ]
            return TableData(columns=cols, rows=rows, title="Projects")

        runner = CliRunner()

        # Test full workflow: select columns, sort, export to JSON
        result = runner.invoke(
            project_list,
            [
                "--format",
                "json",
                "--columns",
                "name,progress",
                "--sort-by",
                "progress:desc",
            ],
        )
        assert result.exit_code == 0
