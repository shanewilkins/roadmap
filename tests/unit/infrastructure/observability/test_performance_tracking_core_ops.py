"""Comprehensive unit tests for performance tracking module.

Tests cover operation timing context managers, database tracking,
file I/O tracking, sync operations, and the OperationTimer class.
"""

import time
from unittest.mock import patch

import pytest

from roadmap.common.logging.performance_tracking import (
    track_database_operation,
    track_operation_time,
)


class TestTrackOperationTime:
    """Test track_operation_time context manager."""

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_operation_time_basic(self, mock_logger):
        """Test basic operation timing."""
        with track_operation_time("test_operation") as result:
            time.sleep(0.01)

        assert "duration_ms" in result
        assert result["duration_ms"] >= 10  # At least 10ms for sleep
        assert not result["exceeded_threshold"]
        assert mock_logger.debug.called

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_operation_time_with_warning(self, mock_logger):
        """Test operation timing with threshold exceeded."""
        with track_operation_time(
            "slow_operation",
            warn_threshold_ms=10,
        ) as result:
            time.sleep(0.02)

        assert result["exceeded_threshold"]
        assert result["duration_ms"] >= 20
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "operation_slow"
        assert "slow_operation" in call_args[1]["operation_name"]

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_operation_time_no_warning_when_fast(self, mock_logger):
        """Test that no warning is logged for fast operations."""
        with track_operation_time(
            "fast_operation",
            warn_threshold_ms=5000,
        ) as result:
            pass  # No sleep

        assert not result["exceeded_threshold"]
        mock_logger.warning.assert_not_called()
        mock_logger.debug.assert_called_once()

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_operation_time_with_info_level(self, mock_logger):
        """Test operation timing with info log level."""
        with track_operation_time(
            "info_operation",
            log_level="info",
        ) as result:
            pass

        assert not result["exceeded_threshold"]
        mock_logger.info.assert_called_once()

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_operation_time_result_dict(self, mock_logger):
        """Test that result dictionary is properly populated."""
        with track_operation_time("test_op") as result:
            assert result["duration_ms"] == 0  # Before operation
            assert "exceeded_threshold" in result

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_operation_time_with_exception(self, mock_logger):
        """Test that timing is recorded even when exception occurs."""
        try:
            with track_operation_time("error_operation") as result:
                time.sleep(0.01)
                raise ValueError("Test error")
        except ValueError:
            pass

        assert result["duration_ms"] >= 10
        assert mock_logger.debug.called or mock_logger.warning.called

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_operation_time_custom_threshold(self, mock_logger):
        """Test custom warning threshold."""
        with track_operation_time(
            "custom_op",
            warn_threshold_ms=1,
        ) as result:
            time.sleep(0.01)

        assert result["exceeded_threshold"]
        mock_logger.warning.assert_called_once()

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_operation_time_logs_correct_name(self, mock_logger):
        """Test that operation name is logged correctly."""
        with track_operation_time("my_operation"):
            pass

        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "operation_completed"
        assert call_args[1]["operation_name"] == "my_operation"


class TestTrackDatabaseOperation:
    """Test track_database_operation context manager."""

    @pytest.mark.parametrize(
        "operation,entity_type",
        [
            ("create", "issue"),
            ("read", "issue"),
            ("update", "milestone"),
            ("delete", "project"),
        ],
    )
    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_database_operation_basic(self, mock_logger, operation, entity_type):
        """Test database operation tracking with various operations and entities."""
        with track_database_operation(operation, entity_type) as result:
            pass

        assert "duration_ms" in result
        assert not result["exceeded_threshold"]
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[1]["operation"] == operation
        assert call_args[1]["entity_type"] == entity_type

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_database_operation_with_entity_id(self, mock_logger):
        """Test database operation tracking with entity ID."""
        with track_database_operation("read", "issue", entity_id="issue-123"):
            pass

        call_args = mock_logger.debug.call_args
        assert call_args[1]["entity_id"] == "issue-123"

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_database_operation_slow_warning(self, mock_logger):
        """Test warning when database operation is slow."""
        with track_database_operation(
            "update",
            "milestone",
            warn_threshold_ms=10,
        ) as result:
            time.sleep(0.02)

        assert result["exceeded_threshold"]
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[1]["operation"] == "update"
        assert call_args[1]["entity_type"] == "milestone"

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_database_operation_custom_threshold(self, mock_logger):
        """Test custom warning threshold for database operations."""
        with track_database_operation(
            "create",
            "issue",
            warn_threshold_ms=1,
        ) as result:
            time.sleep(0.01)

        assert result["exceeded_threshold"]
        mock_logger.warning.assert_called_once()

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_database_operation_exception_handling(self, mock_logger):
        """Test that timing is recorded even with exceptions."""
        try:
            with track_database_operation("delete", "issue") as result:
                time.sleep(0.01)
                raise RuntimeError("DB error")
        except RuntimeError:
            pass

        assert result["duration_ms"] >= 10
        assert mock_logger.debug.called or mock_logger.warning.called
