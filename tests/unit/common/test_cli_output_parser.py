"""Tests for CLIOutputParser utilities."""

import json

import pytest

from tests.common.cli_test_helpers import CLIOutputParser


class TestExtractJson:
    """Test JSON extraction from output."""

    def test_extract_json_single_line(self):
        """Test extracting JSON from single line."""
        json_obj = {"id": 1, "name": "test"}
        output = f"Some log\n{json.dumps(json_obj)}"
        result = CLIOutputParser.extract_json(output)
        assert result == json_obj

    def test_extract_json_multiple_lines(self):
        """Test extracting multiline JSON."""
        json_obj = {"id": 1, "items": [1, 2, 3]}
        json_str = json.dumps(json_obj, indent=2)
        output = f"Some log\n{json_str}"
        result = CLIOutputParser.extract_json(output)
        assert result == json_obj

    def test_extract_json_no_json(self):
        """Test error when no JSON found."""
        output = "Just plain text"
        with pytest.raises(ValueError, match="No valid JSON found"):
            CLIOutputParser.extract_json(output)

    def test_extract_json_invalid_json(self):
        """Test error on invalid JSON."""
        output = "Some log\n{invalid json}"
        with pytest.raises(ValueError, match="No valid JSON found"):
            CLIOutputParser.extract_json(output)


class TestExtractFromTabledata:
    """Test TableData extraction utilities."""

    def test_extract_from_tabledata_exact_match(self):
        """Test extracting ID when name exactly matches."""
        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ],
            "rows": [
                [1, "Test Project"],
                [2, "Another Project"],
            ],
        }

        result = CLIOutputParser.extract_from_tabledata(
            table_data, "name", "Test Project", "id"
        )
        assert result == "1"

    def test_extract_from_tabledata_not_found(self):
        """Test error when value not found in column."""
        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ],
            "rows": [[1, "Test Project"]],
        }

        with pytest.raises(ValueError, match="not found"):
            CLIOutputParser.extract_from_tabledata(
                table_data, "name", "Missing Project", "id"
            )

    def test_extract_from_tabledata_column_not_found(self):
        """Test error when column name doesn't exist."""
        table_data = {
            "columns": [{"name": "id", "type": "integer"}],
            "rows": [[1]],
        }

        with pytest.raises(ValueError, match="Column 'missing' not found"):
            CLIOutputParser.extract_from_tabledata(table_data, "missing", "value", "id")

    def test_extract_from_tabledata_custom_id_column(self):
        """Test with custom ID column name."""
        table_data = {
            "columns": [
                {"name": "project_id", "type": "integer"},
                {"name": "title", "type": "string"},
            ],
            "rows": [[42, "My Project"]],
        }

        result = CLIOutputParser.extract_from_tabledata(
            table_data, "title", "My Project", "project_id"
        )
        assert result == "42"

    def test_extract_value_from_tabledata(self):
        """Test extracting any value by column match."""
        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
                {"name": "status", "type": "string"},
            ],
            "rows": [
                [1, "Test Project", "active"],
                [2, "Another Project", "inactive"],
            ],
        }

        result = CLIOutputParser.extract_value_from_tabledata(
            table_data, "name", "Test Project", "status"
        )
        assert result == "active"

    def test_extract_value_from_tabledata_target_not_found(self):
        """Test error when target column doesn't exist."""
        table_data = {
            "columns": [{"name": "id", "type": "integer"}],
            "rows": [[1]],
        }

        with pytest.raises(ValueError, match="not found"):
            CLIOutputParser.extract_value_from_tabledata(
                table_data, "id", "1", "missing"
            )


class TestClickTestHelperExtractIssueId:
    """Test ClickTestHelper issue ID extraction."""

    def test_extract_issue_id_from_json(self):
        """Test extracting issue ID from JSON output."""
        from tests.fixtures.click_testing import ClickTestHelper

        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "title", "type": "string"},
            ],
            "rows": [[42, "Test Issue"]],
        }
        output = f"Issue created\n{json.dumps(table_data)}"

        result = ClickTestHelper.extract_issue_id(output)
        assert result == "42"

    def test_extract_issue_id_from_legacy_log(self):
        """Test extracting issue ID from legacy log format."""
        from tests.fixtures.click_testing import ClickTestHelper

        output = "Creating issue...\nissue_id=99\nDone"

        result = ClickTestHelper.extract_issue_id(output)
        assert result == "99"

    def test_extract_issue_id_fallback_bracket(self):
        """Test extracting issue ID from bracket format."""
        from tests.fixtures.click_testing import ClickTestHelper

        output = "Creating issue...\nCreated [123]\nDone"

        result = ClickTestHelper.extract_issue_id(output)
        assert result == "123"

    def test_extract_issue_id_no_format_fails(self):
        """Test error when no issue ID found."""
        from tests.fixtures.click_testing import ClickTestHelper

        output = "No issue ID here"

        with pytest.raises(ValueError, match="Could not extract"):
            ClickTestHelper.extract_issue_id(output)


class TestClickTestHelperExtractProjectId:
    """Test ClickTestHelper project ID extraction."""

    def test_extract_project_id_by_name(self):
        """Test extracting project ID by project name."""
        from tests.fixtures.click_testing import ClickTestHelper

        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ],
            "rows": [
                [1, "Project A"],
                [2, "Project B"],
            ],
        }
        output = f"Projects:\n{json.dumps(table_data)}"

        result = ClickTestHelper.extract_project_id(output, "Project B")
        assert result == "2"

    def test_extract_project_id_first_row(self):
        """Test extracting first project ID when name not provided."""
        from tests.fixtures.click_testing import ClickTestHelper

        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ],
            "rows": [[1, "Only Project"]],
        }
        output = f"Projects:\n{json.dumps(table_data)}"

        result = ClickTestHelper.extract_project_id(output)
        assert result == "1"

    def test_extract_project_id_not_found(self):
        """Test error when project name not found."""
        from tests.fixtures.click_testing import ClickTestHelper

        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ],
            "rows": [[1, "Project A"]],
        }
        output = f"Projects:\n{json.dumps(table_data)}"

        with pytest.raises(ValueError, match="not found"):
            ClickTestHelper.extract_project_id(output, "Missing Project")


class TestClickTestHelperExtractMilestoneId:
    """Test ClickTestHelper milestone ID extraction."""

    def test_extract_milestone_id_by_name(self):
        """Test extracting milestone ID by milestone name."""
        from tests.fixtures.click_testing import ClickTestHelper

        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ],
            "rows": [
                [1, "v1.0"],
                [2, "v2.0"],
            ],
        }
        output = f"Milestones:\n{json.dumps(table_data)}"

        result = ClickTestHelper.extract_milestone_id(output, "v2.0")
        assert result == "2"

    def test_extract_milestone_id_first_row(self):
        """Test extracting first milestone ID when name not provided."""
        from tests.fixtures.click_testing import ClickTestHelper

        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ],
            "rows": [[1, "v1.0"]],
        }
        output = f"Milestones:\n{json.dumps(table_data)}"

        result = ClickTestHelper.extract_milestone_id(output)
        assert result == "1"

    def test_extract_milestone_id_not_found(self):
        """Test error when milestone name not found."""
        from tests.fixtures.click_testing import ClickTestHelper

        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ],
            "rows": [[1, "v1.0"]],
        }
        output = f"Milestones:\n{json.dumps(table_data)}"

        with pytest.raises(ValueError, match="not found"):
            ClickTestHelper.extract_milestone_id(output, "v3.0")
