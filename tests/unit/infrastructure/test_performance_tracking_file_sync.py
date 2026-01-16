"""Comprehensive unit tests for performance tracking module.

Tests cover operation timing context managers, database tracking,
file I/O tracking, sync operations, and the OperationTimer class.
"""

import time
from unittest.mock import patch

import pytest

from roadmap.common.logging.performance_tracking import (
    OperationTimer,
    track_database_operation,
    track_file_operation,
    track_operation_time,
    track_sync_operation,
)


class TestTrackFileOperation:
    """Test track_file_operation context manager."""

    @pytest.mark.parametrize(
        "operation,file_path",
        [
            ("read", "/path/to/file.md"),
            ("write", "/path/to/output.md"),
            ("sync", "/path/to/sync.md"),
        ],
    )
    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_file_operation(self, mock_logger, operation, file_path):
        """Test file operation tracking with different operations."""
        with track_file_operation(operation, file_path) as result:
            pass

        assert "duration_ms" in result
        assert not result["exceeded_threshold"]
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[1]["operation"] == operation
        assert call_args[1]["file_path"] == file_path

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_file_operation_slow_warning(self, mock_logger):
        """Test warning when file operation is slow."""
        with track_file_operation(
            "read",
            "/large/file.md",
            warn_threshold_ms=10,
        ) as result:
            time.sleep(0.02)

        assert result["exceeded_threshold"]
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[1]["operation"] == "read"
        assert call_args[1]["file_path"] == "/large/file.md"

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_file_operation_custom_threshold(self, mock_logger):
        """Test custom warning threshold for file operations."""
        with track_file_operation(
            "write",
            "/path/file.md",
            warn_threshold_ms=1,
        ) as result:
            time.sleep(0.01)

        assert result["exceeded_threshold"]
        mock_logger.warning.assert_called_once()

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_file_operation_exception_handling(self, mock_logger):
        """Test that timing is recorded even with exceptions."""
        try:
            with track_file_operation("read", "/missing/file.md") as result:
                time.sleep(0.01)
                raise FileNotFoundError("File not found")
        except FileNotFoundError:
            pass

        assert result["duration_ms"] >= 10


class TestTrackSyncOperation:
    """Test track_sync_operation context manager."""

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_sync_operation_basic(self, mock_logger):
        """Test basic sync operation tracking."""
        with track_sync_operation("github_sync") as result:
            pass

        assert "duration_ms" in result
        assert "exceeded_threshold" in result
        assert "throughput_items_per_sec" in result
        assert result["throughput_items_per_sec"] == 0  # No entity count
        mock_logger.info.assert_called_once()

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_sync_operation_with_entity_count(self, mock_logger):
        """Test sync operation tracking with entity count."""
        with track_sync_operation("github_sync", entity_count=10) as result:
            time.sleep(0.01)

        assert result["throughput_items_per_sec"] > 0
        call_args = mock_logger.info.call_args
        assert call_args[1]["entity_count"] == 10

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_sync_operation_throughput_calculation(self, mock_logger):
        """Test that throughput is correctly calculated."""
        with track_sync_operation(
            "sync",
            entity_count=100,
            warn_threshold_ms=5000,
        ) as result:
            time.sleep(0.1)  # 100ms

        # 100 entities in 100ms = 1000 items per second
        expected_throughput = (100 * 1000) / (result["duration_ms"])
        assert abs(result["throughput_items_per_sec"] - expected_throughput) < 1

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_sync_operation_slow_warning(self, mock_logger):
        """Test warning when sync operation is slow."""
        with track_sync_operation(
            "slow_sync",
            entity_count=50,
            warn_threshold_ms=10,
        ) as result:
            time.sleep(0.02)

        assert result["exceeded_threshold"]
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[1]["entity_count"] == 50
        assert "throughput_items_per_sec" in call_args[1]

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_sync_operation_no_warning_when_fast(self, mock_logger):
        """Test no warning for fast sync operations."""
        with track_sync_operation(
            "fast_sync",
            entity_count=100,
            warn_threshold_ms=5000,
        ) as result:
            time.sleep(0.001)  # Sleep slightly to avoid division by zero

        assert not result["exceeded_threshold"]
        mock_logger.warning.assert_not_called()
        mock_logger.info.assert_called_once()

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_sync_operation_zero_entity_count(self, mock_logger):
        """Test sync operation with zero entity count."""
        with track_sync_operation("empty_sync", entity_count=0) as result:
            pass

        # 0 entities should give 0 throughput
        assert result["throughput_items_per_sec"] == 0

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_track_sync_operation_exception_handling(self, mock_logger):
        """Test that timing is recorded even with exceptions."""
        try:
            with track_sync_operation("failing_sync", entity_count=10) as result:
                time.sleep(0.01)
                raise ConnectionError("Sync failed")
        except ConnectionError:
            pass

        assert result["duration_ms"] >= 10


class TestOperationTimer:
    """Test OperationTimer class for multi-step operations."""

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_basic(self, mock_logger):
        """Test basic operation timer usage."""
        timer = OperationTimer("data_sync")
        assert timer.operation_name == "data_sync"
        assert timer.steps == {}
        assert timer.current_step is None

    @pytest.mark.parametrize(
        "operation_name,num_steps,step_configs",
        [
            ("single_step_op", 1, [("fetch_data", 0.01)]),
            ("multi_step_op", 3, [("step1", 0.01), ("step2", 0.01), ("step3", 0.01)]),
            (
                "complex_workflow",
                5,
                [
                    ("setup", 0.01),
                    ("process_item_1", 0.01),
                    ("process_item_2", 0.01),
                    ("process_item_3", 0.01),
                    ("cleanup", 0.01),
                ],
            ),
        ],
    )
    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_step_execution(
        self, mock_logger, operation_name, num_steps, step_configs
    ):
        """Test operation timer with various step configurations."""
        timer = OperationTimer(operation_name)

        for step_name, sleep_time in step_configs:
            timer.start_step(step_name)
            time.sleep(sleep_time)
            if step_name != step_configs[-1][0]:
                timer.start_step("next")  # Implicitly end previous step

        if operation_name != "single_step_op":
            timer.end_step()

        assert len(timer.steps) >= num_steps - 1

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_finish(self, mock_logger):
        """Test operation timer finish method."""
        timer = OperationTimer("finish_op")
        timer.start_step("setup")
        time.sleep(0.01)
        timer.end_step()

        result = timer.finish()

        assert result["operation"] == "finish_op"
        assert "total_duration_ms" in result
        assert "steps" in result
        assert result["total_duration_ms"] >= 10
        mock_logger.info.assert_called_once()

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_finish_with_active_step(self, mock_logger):
        """Test that finish() ends current step if active."""
        timer = OperationTimer("active_finish_op")
        timer.start_step("ongoing_step")
        time.sleep(0.01)

        result = timer.finish()

        assert "ongoing_step" in timer.steps
        assert timer.current_step is None
        assert result["total_duration_ms"] >= 10

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_step_timing_accuracy(self, mock_logger):
        """Test that step timing is reasonably accurate."""
        timer = OperationTimer("timing_test_op")

        timer.start_step("slow_step")
        time.sleep(0.02)
        timer.end_step()

        assert timer.steps["slow_step"] >= 20

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_total_time_includes_all_steps(self, mock_logger):
        """Test that total time includes all step times."""
        timer = OperationTimer("total_time_op")

        timer.start_step("step1")
        time.sleep(0.01)
        timer.start_step("step2")
        time.sleep(0.01)
        timer.end_step()

        result = timer.finish()

        # Total should be at least sum of step times
        total_steps_time = sum(timer.steps.values())
        assert result["total_duration_ms"] >= total_steps_time - 5  # Allow 5ms variance

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_logs_step_completion(self, mock_logger):
        """Test that step completion is logged."""
        timer = OperationTimer("log_test_op")
        timer.start_step("tracked_step")
        timer.end_step()

        # Should log step completion
        step_log_calls = [
            call
            for call in mock_logger.debug.call_args_list
            if "step_completed" in str(call)
        ]
        assert len(step_log_calls) > 0

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_logs_finish(self, mock_logger):
        """Test that finish is logged."""
        timer = OperationTimer("finish_log_op")
        timer.finish()

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "finish_log_op_finished" in str(call_args)

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_edge_cases(self, mock_logger):
        """Test operation timer edge cases: no steps and repeated finish."""
        # Test with no steps
        timer1 = OperationTimer("no_steps_op")
        time.sleep(0.001)
        result1 = timer1.finish()

        assert result1["steps"] == {}
        assert result1["total_duration_ms"] > 0

        # Test repeated finish
        timer2 = OperationTimer("multi_finish_op")
        timer2.start_step("step")
        timer2.end_step()

        result2_a = timer2.finish()
        result2_b = timer2.finish()

        assert result2_a["total_duration_ms"] <= result2_b["total_duration_ms"]


class TestPerformanceTrackingIntegration:
    """Integration tests for performance tracking."""

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_nested_operations(self, mock_logger):
        """Test nested operation tracking."""
        with track_operation_time("outer") as outer_result:
            time.sleep(0.01)
            with track_operation_time("inner") as inner_result:
                time.sleep(0.01)

        assert outer_result["duration_ms"] >= inner_result["duration_ms"]
        assert outer_result["duration_ms"] >= 20

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_operation_timer_with_context_managers(self, mock_logger):
        """Test combining OperationTimer with context managers."""
        timer = OperationTimer("combined_tracking")

        with track_operation_time("phase1"):
            timer.start_step("db_write")
            time.sleep(0.01)
            timer.end_step()

        with track_operation_time("phase2"):
            timer.start_step("file_sync")
            time.sleep(0.01)
            timer.end_step()

        result = timer.finish()
        assert len(result["steps"]) == 2

    @patch("roadmap.common.logging.performance_tracking.logger")
    def test_multiple_operation_types(self, mock_logger):
        """Test tracking different operation types together."""
        operations = [
            track_operation_time("general"),
            track_database_operation("create", "issue"),
            track_file_operation("write", "/file.md"),
            track_sync_operation("github_sync", entity_count=10),
        ]

        for op_context in operations:
            with op_context as result:
                time.sleep(0.01)
                assert "duration_ms" in result

        # All operations should be logged
        assert mock_logger.debug.call_count >= 2
        assert mock_logger.info.call_count >= 1
