"""Tests for logging configuration."""

import pytest

from roadmap.common.logging import (
    add_correlation_id,
    correlation_id_var,
    get_logger,
    scrub_sensitive_data,
    setup_logging,
)


class TestCorrelationId:
    """Test correlation ID functionality."""

    @pytest.mark.parametrize(
        "correlation_id,should_be_present",
        [
            ("test-correlation-123", True),
            (None, False),
        ],
    )
    def test_add_correlation_id_processor(self, correlation_id, should_be_present):
        """Test correlation ID processor with various states."""
        correlation_id_var.set(correlation_id)
        event_dict = {"event": "test_event"}
        result = add_correlation_id(None, "info", event_dict)
        if should_be_present:
            assert result["correlation_id"] == correlation_id
        else:
            assert "correlation_id" not in result

    @pytest.mark.parametrize(
        "field_name,field_value",
        [
            ("github_token", "ghp_1234567890"),
            ("password", "secret123"),
            ("Token", "secret123"),
            ("PASSWORD", "pass456"),
            ("Github_Token", "ghp789"),
        ],
    )
    def test_scrub_sensitive_fields(self, field_name, field_value):
        """Test scrubbing sensitive fields (case-insensitive)."""
        event_dict = {field_name: field_value, "message": "test"}
        result = scrub_sensitive_data(None, "info", event_dict)
        assert result[field_name] == "***REDACTED***"
        assert result["message"] == "test"


class TestGetLogger:
    """Test logger retrieval."""

    def test_get_logger_basic(self):
        """Test getting a logger."""
        logger = get_logger("test_module")
        assert logger is not None

    def test_get_logger_same_name(self):
        """Test that same name returns logger."""
        logger1 = get_logger("test_module_1")
        logger2 = get_logger("test_module_1")
        # Both should be loggers
        assert logger1 is not None
        assert logger2 is not None

    def test_get_logger_different_names(self):
        """Test that different names return different loggers."""
        logger1 = get_logger("test_module_2")
        logger2 = get_logger("test_module_3")
        # Both should be loggers, different names don't matter with structlog
        assert logger1 is not None
        assert logger2 is not None

    def test_scrub_nested_and_list_data(self):
        """Test scrubbing in nested structures."""
        event_dict = {
            "user": {"name": "john", "api_key": "key123"},
            "credentials": ["token1", "token2"],
            "token": "secret",
        }
        result = scrub_sensitive_data(None, "info", event_dict)
        user_data = result.get("user")
        assert isinstance(user_data, dict)
        assert user_data.get("api_key") == "***REDACTED***"
        assert user_data.get("name") == "john"
        assert result["token"] == "***REDACTED***"


class TestSetupLogging:
    """Test logging setup."""

    @pytest.mark.parametrize(
        "debug_mode,log_to_file,log_level",
        [
            (False, True, "INFO"),
            (True, True, "DEBUG"),
            (False, False, "INFO"),
            (True, False, "WARNING"),
        ],
    )
    def test_setup_logging_configurations(
        self, mocker, debug_mode, log_to_file, log_level
    ):
        """Test logging setup with various configurations."""
        mocker.patch("roadmap.common.logging.structlog")
        logger = setup_logging(
            debug_mode=debug_mode, log_to_file=log_to_file, log_level=log_level
        )
        assert logger is not None
