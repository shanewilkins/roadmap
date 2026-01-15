"""Tests for archive_utils module.

Tests shared utility functions for archive and restore operations.
Covers error handling and validation patterns used across all entity types.
"""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.cli.archive_operations import (
    handle_archive_parse_error,
    handle_restore_parse_error,
)


class TestHandleArchiveParseError:
    """Test handle_archive_parse_error function."""

    def test_error_handling_with_console(self):
        """Test error handling with provided console."""
        error = ValueError("Test error")
        mock_console = MagicMock()

        with patch("roadmap.adapters.cli.archive_operations.handle_cli_error"):
            handle_archive_parse_error(
                error=error,
                entity_type="issue",
                entity_id="issue-1",
                archive_dir="/tmp/archive",
                console=mock_console,
            )

        # Verify console was called to print error
        assert mock_console.print.called

    def test_error_handling_without_console(self):
        """Test error handling uses default console when none provided."""
        error = ValueError("Test error")

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_archive_parse_error(
                    error=error,
                    entity_type="issue",
                    entity_id="issue-1",
                    archive_dir="/tmp/archive",
                )

        assert mock_handle.called

    def test_error_context_building(self):
        """Test that error context is built correctly."""
        error = ValueError("Test error")
        archive_dir = "/tmp/archive"

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_archive_parse_error(
                    error=error,
                    entity_type="issue",
                    entity_id="issue-1",
                    archive_dir=archive_dir,
                )

        # Verify handle_cli_error was called with correct context
        call_args = mock_handle.call_args
        context = call_args.kwargs.get("context", {})
        assert context["archive_dir"] == archive_dir

    def test_error_context_with_extra_context(self):
        """Test error context merges with extra_context parameter."""
        error = ValueError("Test error")
        extra_context = {"user": "test_user", "timestamp": "2025-12-26"}

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_archive_parse_error(
                    error=error,
                    entity_type="issue",
                    entity_id="issue-1",
                    archive_dir="/tmp/archive",
                    extra_context=extra_context,
                )

        call_args = mock_handle.call_args
        context = call_args.kwargs.get("context", {})
        assert context["user"] == "test_user"
        assert context["timestamp"] == "2025-12-26"
        assert context["archive_dir"] == "/tmp/archive"

    @pytest.mark.parametrize(
        "entity_type,entity_id",
        [
            ("issue", "issue-1"),
            ("milestone", "v1.0"),
            ("project", "myproject"),
        ],
    )
    def test_error_handling_different_entity_types(self, entity_type, entity_id):
        """Test error handling works for different entity types."""
        error = ValueError("Test error")

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_archive_parse_error(
                    error=error,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    archive_dir="/tmp/archive",
                )

        call_args = mock_handle.call_args
        assert call_args.kwargs["entity_type"] == entity_type
        assert call_args.kwargs["entity_id"] == entity_id

    def test_operation_name_format(self):
        """Test operation name is formatted correctly."""
        error = ValueError("Test error")

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_archive_parse_error(
                    error=error,
                    entity_type="issue",
                    entity_id="issue-1",
                    archive_dir="/tmp/archive",
                )

        call_args = mock_handle.call_args
        operation = call_args.kwargs["operation"]
        assert operation == "parse_archived_issue"


class TestHandleRestoreParseError:
    """Test handle_restore_parse_error function."""

    def test_error_handling_with_console(self):
        """Test error handling with provided console."""
        error = ValueError("Test error")
        mock_console = MagicMock()

        with patch("roadmap.adapters.cli.archive_operations.handle_cli_error"):
            handle_restore_parse_error(
                error=error,
                entity_type="issue",
                entity_id="issue-1",
                archive_dir="/tmp/archive",
                console=mock_console,
            )

        # Verify console was called to print error
        assert mock_console.print.called

    def test_error_handling_without_console(self):
        """Test error handling uses default console when none provided."""
        error = ValueError("Test error")

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_restore_parse_error(
                    error=error,
                    entity_type="issue",
                    entity_id="issue-1",
                    archive_dir="/tmp/archive",
                )

        assert mock_handle.called

    def test_error_context_building(self):
        """Test that error context is built correctly."""
        error = ValueError("Test error")
        archive_dir = "/tmp/archive"

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_restore_parse_error(
                    error=error,
                    entity_type="issue",
                    entity_id="issue-1",
                    archive_dir=archive_dir,
                )

        # Verify handle_cli_error was called with correct context
        call_args = mock_handle.call_args
        context = call_args.kwargs.get("context", {})
        assert context["archive_dir"] == archive_dir

    def test_error_context_with_extra_context(self):
        """Test error context merges with extra_context parameter."""
        error = ValueError("Test error")
        extra_context = {"user": "test_user", "attempt": 1}

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_restore_parse_error(
                    error=error,
                    entity_type="milestone",
                    entity_id="v1.0",
                    archive_dir="/tmp/archive",
                    extra_context=extra_context,
                )

        call_args = mock_handle.call_args
        context = call_args.kwargs.get("context", {})
        assert context["user"] == "test_user"
        assert context["attempt"] == 1
        assert context["archive_dir"] == "/tmp/archive"

    @pytest.mark.parametrize(
        "entity_type,entity_id",
        [
            ("issue", "issue-1"),
            ("milestone", "v1.0"),
            ("project", "myproject"),
        ],
    )
    def test_error_handling_different_entity_types(self, entity_type, entity_id):
        """Test error handling works for different entity types."""
        error = ValueError("Test error")

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_restore_parse_error(
                    error=error,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    archive_dir="/tmp/archive",
                )

        call_args = mock_handle.call_args
        assert call_args.kwargs["entity_type"] == entity_type
        assert call_args.kwargs["entity_id"] == entity_id

    def test_operation_name_format(self):
        """Test operation name is formatted correctly."""
        error = ValueError("Test error")

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_handle:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_restore_parse_error(
                    error=error,
                    entity_type="issue",
                    entity_id="issue-1",
                    archive_dir="/tmp/archive",
                )

        call_args = mock_handle.call_args
        operation = call_args.kwargs["operation"]
        assert operation == "restore_issue"

    def test_restore_vs_archive_operation_names(self):
        """Test that restore and archive use different operation names."""
        error = ValueError("Test error")

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_archive:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_archive_parse_error(
                    error=error,
                    entity_type="issue",
                    entity_id="issue-1",
                    archive_dir="/tmp/archive",
                )

        with patch(
            "roadmap.adapters.cli.archive_operations.handle_cli_error"
        ) as mock_restore:
            with patch("roadmap.adapters.cli.archive_operations.get_console"):
                handle_restore_parse_error(
                    error=error,
                    entity_type="issue",
                    entity_id="issue-1",
                    archive_dir="/tmp/archive",
                )

        archive_op = mock_archive.call_args.kwargs["operation"]
        restore_op = mock_restore.call_args.kwargs["operation"]

        assert "parse_archived" in archive_op
        assert "restore_" in restore_op
        assert archive_op != restore_op
