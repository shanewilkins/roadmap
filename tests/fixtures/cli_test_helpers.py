"""Helpers for robust CLI testing without regex parsing.

Provides utilities for extracting structured data from CLI output
without relying on fragile regex patterns. Prefers JSON output format
for machine-readable, maintainable tests.

Architecture:
- CLIOutputParser: Infrastructure layer - pure JSON/table parsing utilities
- Test files: Use extract_json() for JSON, or use ClickTestHelper for command-specific helpers
"""

import json
import re
from typing import Any


class CLIOutputParser:
    """Parse CLI output in a robust, maintainable way.

    Pure infrastructure layer - no test-specific logic, only parsing utilities.
    """

    @staticmethod
    def extract_json(output: str) -> dict[str, Any] | list[Any]:
        """Extract JSON from CLI output.

        Handles cases where JSON is preceded by logs or other output.

        Args:
            output: CLI output that contains JSON

        Returns:
            Parsed JSON as dict or list

        Raises:
            ValueError: If no valid JSON found in output
        """
        # Remove leading log lines to find JSON start
        lines = output.split("\n")

        # Find first line that looks like JSON start
        json_start_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                json_start_idx = i
                break

        if json_start_idx == -1:
            raise ValueError(f"No valid JSON found in output. Output was:\n{output}")

        # Try to parse JSON starting from that line
        json_str = "\n".join(lines[json_start_idx:])

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # If that didn't work, try to find a complete JSON object/array
            json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", json_str)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                f"No valid JSON found in output. Output was:\n{output}"
            ) from e

    @staticmethod
    def extract_from_tabledata(
        json_output: dict[str, Any],
        column_name: str,
        search_value: str,
        id_column: str = "id",
    ) -> str:
        """Extract an ID from TableData JSON by matching a column value.

        TableData is the structure returned by list commands with --format json.
        It has 'columns' (list of column definitions) and 'rows' (list of row data).

        Args:
            json_output: The parsed TableData JSON object
            column_name: Name of the column to search in (e.g., "title")
            search_value: Value to match
            id_column: Name of the column containing the ID (default: "id")

        Returns:
            The ID value as a string

        Raises:
            ValueError: If column_name or id_column not found, or value not found
        """
        if not isinstance(json_output, dict):
            raise ValueError(f"Expected dict, got {type(json_output).__name__}")

        rows = json_output.get("rows", [])
        columns = json_output.get("columns", [])

        if not rows or not columns:
            raise ValueError("TableData is empty (no rows or columns)")

        # Find column indices
        search_col_idx = None
        id_col_idx = None

        for i, col in enumerate(columns):
            col_name = col.get("name")
            if col_name == column_name:
                search_col_idx = i
            if col_name == id_column:
                id_col_idx = i

        if search_col_idx is None:
            raise ValueError(
                f"Column '{column_name}' not found in TableData. "
                f"Available columns: {[c.get('name') for c in columns]}"
            )

        if id_col_idx is None:
            raise ValueError(
                f"ID column '{id_column}' not found in TableData. "
                f"Available columns: {[c.get('name') for c in columns]}"
            )

        # Find row with matching column value
        for row in rows:
            if search_col_idx < len(row) and row[search_col_idx] == search_value:
                if id_col_idx < len(row):
                    return str(row[id_col_idx])

        raise ValueError(
            f"Value '{search_value}' not found in column '{column_name}'. "
            f"Available values: {[row[search_col_idx] for row in rows if search_col_idx < len(row)]}"
        )

    @staticmethod
    def extract_value_from_tabledata(
        json_output: dict[str, Any],
        match_column: str,
        match_value: str,
        target_column: str,
    ) -> str:
        """Extract a value from TableData by matching another column.

        Generalized version of extract_from_tabledata for any column.

        Args:
            json_output: The parsed TableData JSON object
            match_column: Column to match on
            match_value: Value to search for
            target_column: Column to extract from

        Returns:
            The target value as a string

        Raises:
            ValueError: If columns not found or value not found
        """
        if not isinstance(json_output, dict):
            raise ValueError(f"Expected dict, got {type(json_output).__name__}")

        rows = json_output.get("rows", [])
        columns = json_output.get("columns", [])

        if not rows or not columns:
            raise ValueError("TableData is empty (no rows or columns)")

        # Find column indices
        match_col_idx = None
        target_col_idx = None

        for i, col in enumerate(columns):
            col_name = col.get("name")
            if col_name == match_column:
                match_col_idx = i
            if col_name == target_column:
                target_col_idx = i

        if match_col_idx is None:
            raise ValueError(
                f"Match column '{match_column}' not found in TableData. "
                f"Available: {[c.get('name') for c in columns]}"
            )

        if target_col_idx is None:
            raise ValueError(
                f"Target column '{target_column}' not found in TableData. "
                f"Available: {[c.get('name') for c in columns]}"
            )

        # Find row and extract value
        for row in rows:
            if match_col_idx < len(row) and row[match_col_idx] == match_value:
                if target_col_idx < len(row):
                    return str(row[target_col_idx])

        raise ValueError(
            f"Value '{match_value}' not found in column '{match_column}'. "
            f"Available values: {[row[match_col_idx] for row in rows if match_col_idx < len(row)]}"
        )


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI color codes from text.

    Args:
        text: Text with potential ANSI codes

    Returns:
        Text without ANSI codes
    """
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)
