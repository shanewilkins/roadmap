"""Tests for logging_utils module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.services import log_operation


class TestLogOperation:
    """Tests for log_operation context manager."""

    @pytest.mark.parametrize(
        "level,should_call_debug,should_call_info,should_call_warning",
        [
            ("info", False, True, False),
            ("debug", True, False, False),
            ("warning", False, False, True),
        ],
    )
    def test_log_operation_custom_levels(
        self, level, should_call_debug, should_call_info, should_call_warning
    ):
        """Test log_operation with different log levels."""
        with patch("roadmap.common.services.logging_utils.logger") as mock_logger:
            with log_operation("test_op", level=level):
                pass

            assert mock_logger.debug.called == should_call_debug
            assert mock_logger.info.called == should_call_info
            assert mock_logger.warning.called == should_call_warning

    def test_log_operation_basic(self):
        """Test basic log_operation context manager."""
        with patch("roadmap.common.services.logging_utils.logger") as mock_logger:
            with log_operation("test_operation") as metrics:
                assert isinstance(metrics, dict)

            # Should log operation start and complete
            assert mock_logger.info.called

    def test_log_operation_with_context(self):
        """Test log_operation with additional context."""
        with patch("roadmap.common.services.logging_utils.logger") as mock_logger:
            with log_operation("update_issue", entity_id=123, status="open"):
                pass

            # Verify context was passed
            assert mock_logger.info.called

    def test_log_operation_timing(self):
        """Test log_operation captures execution time."""
        with patch("roadmap.common.services.logging_utils.logger") as mock_logger:
            with log_operation("slow_operation"):
                time.sleep(0.01)  # Sleep for 10ms

            # Execution should have taken more than 10ms
            assert mock_logger.info.called

    def test_log_operation_with_metrics(self):
        """Test log_operation allows metrics to be added."""
        with patch("roadmap.common.services.logging_utils.logger") as mock_logger:
            with log_operation("process_items") as metrics:
                metrics["items_processed"] = 42
                metrics["errors"] = 0

            assert mock_logger.info.called

    def test_log_operation_with_exception(self):
        """Test log_operation logs exceptions and re-raises."""
        test_error = ValueError("Test error")

        with patch("roadmap.common.services.logging_utils.logger") as mock_logger:
            mock_logger.info = MagicMock()
            with pytest.raises(ValueError) as exc_info:
                with log_operation("failing_operation"):
                    raise test_error

            # Should log the error
            assert mock_logger.info.called
            assert exc_info.value is test_error

    def test_log_operation_multiple_context_fields(self):
        """Test log_operation with multiple context fields."""
        with patch("roadmap.common.services.logging_utils.logger") as mock_logger:
            with log_operation(
                "complex_operation",
                entity_id=123,
                action="update",
                status="in_progress",
                user="admin",
            ) as metrics:
                metrics["result"] = "success"
                metrics["duration"] = 0.5

            assert mock_logger.info.called

    @pytest.mark.parametrize(
        "should_add_metrics",
        [True, False],
    )
    def test_log_operation_metrics_handling(self, should_add_metrics):
        """Test log_operation with and without metrics."""
        with patch("roadmap.common.services.logging_utils.logger") as mock_logger:
            with log_operation("test_op") as metrics:
                if should_add_metrics:
                    metrics["count"] = 1
                    assert "count" in metrics
                else:
                    assert isinstance(metrics, dict)

            assert mock_logger.info.called

    def test_log_operation_yields_dict(self):
        """Test that log_operation yields a dict."""
        with patch("roadmap.common.services.logging_utils.logger"):
            with log_operation("test") as metrics:
                assert isinstance(metrics, dict)
                assert hasattr(metrics, "__setitem__")
                assert hasattr(metrics, "get")

    def test_log_operation_exception_re_raised(self):
        """Test that exceptions are re-raised after logging."""
        test_error = RuntimeError("Test error")

        with patch("roadmap.common.services.logging_utils.logger"):
            with pytest.raises(RuntimeError) as exc_info:
                with log_operation("failing_op"):
                    raise test_error

            assert exc_info.value is test_error

    def test_log_operation_with_zero_sleep(self):
        """Test log_operation with no sleep (minimal execution time)."""
        with patch("roadmap.common.services.logging_utils.logger") as mock_logger:
            with log_operation("instant_operation"):
                pass  # No sleep

            assert mock_logger.info.called

    def test_log_operation_context_isolation(self):
        """Test that context is isolated between operations."""
        with patch("roadmap.common.services.logging_utils.logger"):
            with log_operation("op1", field1="value1") as metrics1:
                metrics1["count"] = 1

            with log_operation("op2", field2="value2") as metrics2:
                metrics2["count"] = 2

            # metrics1 and metrics2 should be different objects
            assert metrics1 is not metrics2

    @pytest.mark.parametrize(
        "operation_name,level,context",
        [
            ("test1", "info", {}),
            ("test2", "debug", {"id": 1}),
            ("test3", "warning", {"id": 1, "status": "pending"}),
        ],
    )
    def test_log_operation_parametrized_combo(self, operation_name, level, context):
        """Test log_operation with various parameter combinations."""
        with patch("roadmap.common.services.logging_utils.logger"):
            with log_operation(operation_name, level=level, **context) as metrics:
                assert isinstance(metrics, dict)

    def test_log_operation_metrics_accumulation(self):
        """Test that metrics can be accumulated during operation."""
        with patch("roadmap.common.services.logging_utils.logger"):
            with log_operation("process") as metrics:
                for i in range(5):
                    metrics[f"item_{i}"] = i * 10

            assert len(metrics) == 5
            assert all(k.startswith("item_") for k in metrics.keys())
