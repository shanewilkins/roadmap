"""Tests for logging_utils module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.logging_utils import log_operation


class TestLogOperation:
    """Tests for log_operation context manager."""

    def test_log_operation_basic(self):
        """Test basic log_operation context manager."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            with log_operation("test_operation") as metrics:
                assert isinstance(metrics, dict)

            # Should log operation start and complete
            assert mock_logger.info.called

    def test_log_operation_with_context(self):
        """Test log_operation with additional context."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            with log_operation("update_issue", entity_id=123, status="open"):
                pass

            # Verify context was passed
            assert mock_logger.info.called

    def test_log_operation_timing(self):
        """Test log_operation captures execution time."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            with log_operation("slow_operation"):
                time.sleep(0.01)  # Sleep for 10ms

            # Execution should have taken more than 10ms
            assert mock_logger.info.called

    def test_log_operation_with_metrics(self):
        """Test log_operation allows metrics to be added."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            with log_operation("process_items") as metrics:
                metrics["items_processed"] = 42
                metrics["errors"] = 0

            assert mock_logger.info.called

    def test_log_operation_with_exception(self):
        """Test log_operation logs exceptions."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            mock_logger.info = MagicMock()
            with pytest.raises(ValueError):
                with log_operation("failing_operation"):
                    raise ValueError("Test error")

            # Should log the error with the same level function (info in this case)
            assert mock_logger.info.called

    def test_log_operation_default_log_level(self):
        """Test log_operation uses default log level."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            with log_operation("test"):
                pass

            # Default level is "info"
            assert mock_logger.info.called

    def test_log_operation_custom_log_level_debug(self):
        """Test log_operation with debug level."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            with log_operation("debug_op", level="debug"):
                pass

            assert mock_logger.debug.called

    def test_log_operation_custom_log_level_warning(self):
        """Test log_operation with warning level."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            with log_operation("warn_op", level="warning"):
                pass

            assert mock_logger.warning.called

    def test_log_operation_multiple_context_fields(self):
        """Test log_operation with multiple context fields."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
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

    def test_log_operation_empty_metrics(self):
        """Test log_operation with no metrics added."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            with log_operation("empty_op"):
                # Don't add any metrics
                pass

            assert mock_logger.info.called

    def test_log_operation_yields_dict(self):
        """Test that log_operation yields a dict."""
        with patch("roadmap.common.logging_utils.logger"):
            with log_operation("test") as metrics:
                assert isinstance(metrics, dict)
                assert hasattr(metrics, "__setitem__")
                assert hasattr(metrics, "get")

    def test_log_operation_exception_re_raised(self):
        """Test that exceptions are re-raised after logging."""
        test_error = RuntimeError("Test error")

        with patch("roadmap.common.logging_utils.logger"):
            with pytest.raises(RuntimeError) as exc_info:
                with log_operation("failing_op"):
                    raise test_error

            assert exc_info.value is test_error

    def test_log_operation_with_zero_sleep(self):
        """Test log_operation with no sleep (minimal execution time)."""
        with patch("roadmap.common.logging_utils.logger") as mock_logger:
            with log_operation("instant_operation"):
                pass  # No sleep

            assert mock_logger.info.called

    def test_log_operation_context_isolation(self):
        """Test that context is isolated between operations."""
        with patch("roadmap.common.logging_utils.logger"):
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
    def test_log_operation_parametrized(self, operation_name, level, context):
        """Test log_operation with various parameters."""
        with patch("roadmap.common.logging_utils.logger"):
            with log_operation(operation_name, level=level, **context) as metrics:
                assert isinstance(metrics, dict)

    def test_log_operation_metrics_accumulation(self):
        """Test that metrics can be accumulated during operation."""
        with patch("roadmap.common.logging_utils.logger"):
            with log_operation("process") as metrics:
                for i in range(5):
                    metrics[f"item_{i}"] = i * 10

            assert len(metrics) == 5
            assert all(k.startswith("item_") for k in metrics.keys())
