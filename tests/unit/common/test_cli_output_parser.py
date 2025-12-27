"""Tests for CLIOutputParser utilities."""

import json

import pytest

from tests.common.cli_test_helpers import CLIOutputParser


class TestExtractJson:
    """Test JSON extraction from output."""

    @pytest.mark.parametrize(
        "output_type,expected_result",
        [
            ("single", {"id": 1, "name": "test"}),
            ("multiline", {"id": 1, "items": [1, 2, 3]}),
        ],
    )
    def test_extract_json_success(self, output_type, expected_result):
        """Test extracting JSON from various output formats."""
        if output_type == "single":
            output = f"Some log\n{json.dumps(expected_result)}"
        else:
            json_str = json.dumps(expected_result, indent=2)
            output = f"Some log\n{json_str}"

        result = CLIOutputParser.extract_json(output)
        assert result == expected_result

    @pytest.mark.parametrize(
        "output_content,error_pattern",
        [
            ("Just plain text", "No valid JSON found"),
            ("Some log\n{invalid json}", "No valid JSON found"),
        ],
    )
    def test_extract_json_error(self, output_content, error_pattern):
        """Test error cases for JSON extraction."""
        with pytest.raises(ValueError, match=error_pattern):
            CLIOutputParser.extract_json(output_content)


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

    @pytest.mark.parametrize(
        "search_col,search_val,result_col,error_match",
        [
            ("name", "Missing Project", "id", "not found"),
            ("missing", "value", "id", "Column 'missing' not found"),
        ],
    )
    def test_extract_from_tabledata_errors(
        self, search_col, search_val, result_col, error_match
    ):
        """Test error cases for tabledata extraction."""
        table_data = {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "string"},
            ],
            "rows": [[1, "Test Project"]],
        }

        with pytest.raises(ValueError, match=error_match):
            CLIOutputParser.extract_from_tabledata(
                table_data, search_col, search_val, result_col
            )

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


class TestClickTestHelperExtractIds:
    """Test ClickTestHelper ID extraction methods."""

    @pytest.mark.parametrize(
        "entity_type,table_data,search_name,expected_id",
        [
            (
                "issue",
                {"columns": [{"name": "id", "type": "integer"}], "rows": [[42]]},
                None,
                "42",
            ),
            (
                "project",
                {
                    "columns": [
                        {"name": "id", "type": "integer"},
                        {"name": "name", "type": "string"},
                    ],
                    "rows": [[1, "Project A"], [2, "Project B"]],
                },
                "Project B",
                "2",
            ),
            (
                "milestone",
                {
                    "columns": [
                        {"name": "id", "type": "integer"},
                        {"name": "name", "type": "string"},
                    ],
                    "rows": [[1, "v1.0"], [2, "v2.0"]],
                },
                "v2.0",
                "2",
            ),
        ],
    )
    def test_extract_entity_id_from_json(
        self, entity_type, table_data, search_name, expected_id
    ):
        """Test extracting entity IDs from JSON output."""
        from tests.fixtures.click_testing import ClickTestHelper

        output = f"{entity_type}s:\n{json.dumps(table_data)}"

        if entity_type == "issue":
            result = ClickTestHelper.extract_issue_id(output)
        elif entity_type == "project":
            result = ClickTestHelper.extract_project_id(output, search_name)
        else:
            result = ClickTestHelper.extract_milestone_id(output, search_name)

        assert result == expected_id

    def test_extract_issue_id_legacy_format(self):
        """Test extracting issue ID from legacy log format."""
        from tests.fixtures.click_testing import ClickTestHelper

        output = "Creating issue...\nissue_id=99\nDone"
        result = ClickTestHelper.extract_issue_id(output)
        assert result == "99"

    def test_extract_issue_id_bracket_format(self):
        """Test extracting issue ID from bracket format."""
        from tests.fixtures.click_testing import ClickTestHelper

        output = "Creating issue...\nCreated [123]\nDone"
        result = ClickTestHelper.extract_issue_id(output)
        assert result == "123"

    @pytest.mark.parametrize(
        "entity_type,output_content",
        [
            ("issue", "No issue ID here"),
            ("project", "No project found"),
            ("milestone", "No milestone here"),
        ],
    )
    def test_extract_id_not_found(self, entity_type, output_content):
        """Test error when entity ID not found."""
        from tests.fixtures.click_testing import ClickTestHelper

        with pytest.raises(ValueError, match="Could not extract|not found"):
            if entity_type == "issue":
                ClickTestHelper.extract_issue_id(output_content)
            elif entity_type == "project":
                ClickTestHelper.extract_project_id(output_content, "Missing")
            else:
                ClickTestHelper.extract_milestone_id(output_content, "Missing")
