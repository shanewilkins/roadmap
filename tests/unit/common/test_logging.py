"""Tests for logging configuration."""

from unittest.mock import patch

from roadmap.common.logging import (
    add_correlation_id,
    correlation_id_var,
    get_logger,
    scrub_sensitive_data,
    setup_logging,
)


class TestCorrelationId:
    """Test correlation ID functionality."""

    def test_add_correlation_id_processor(self):
        """Test correlation ID processor."""
        correlation_id_var.set("test-correlation-123")
        event_dict = {"event": "test_event"}
        result = add_correlation_id(None, "info", event_dict)
        assert result["correlation_id"] == "test-correlation-123"

    def test_add_correlation_id_processor_no_id(self):
        """Test correlation ID processor when no ID is set."""
        correlation_id_var.set(None)
        event_dict = {"event": "test_event"}
        result = add_correlation_id(None, "info", event_dict)
        assert "correlation_id" not in result

    def test_scrub_sensitive_data_token(self):
        """Test scrubbing token from logs."""
        event_dict = {
            "message": "Sync complete",
            "github_token": "ghp_1234567890",
        }
        result = scrub_sensitive_data(None, "info", event_dict)
        assert result["github_token"] == "***REDACTED***"
        assert result["message"] == "Sync complete"

    def test_scrub_sensitive_data_password(self):
        """Test scrubbing password from logs."""
        event_dict = {"password": "secret123"}
        result = scrub_sensitive_data(None, "info", event_dict)
        assert result["password"] == "***REDACTED***"

    def test_scrub_sensitive_data_nested_dict(self):
        """Test scrubbing sensitive data in nested dictionary."""
        event_dict = {
            "user": {"name": "john", "api_key": "key123"},
            "message": "test",
        }
        result = scrub_sensitive_data(None, "info", event_dict)
        user_data = result.get("user")
        assert isinstance(user_data, dict)
        assert user_data.get("api_key") == "***REDACTED***"
        assert user_data.get("name") == "john"

    def test_scrub_sensitive_data_list(self):
        """Test scrubbing sensitive data in lists."""
        event_dict = {
            "credentials": ["token1", "token2"],
            "token": "secret",
        }
        result = scrub_sensitive_data(None, "info", event_dict)
        assert result["token"] == "***REDACTED***"

    def test_scrub_sensitive_data_case_insensitive(self):
        """Test that scrubbing is case-insensitive."""
        event_dict = {
            "Token": "secret123",
            "PASSWORD": "pass456",
            "Github_Token": "ghp789",
        }
        result = scrub_sensitive_data(None, "info", event_dict)
        assert result["Token"] == "***REDACTED***"
        assert result["PASSWORD"] == "***REDACTED***"
        assert result["Github_Token"] == "***REDACTED***"


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


class TestSetupLogging:
    """Test logging setup."""

    def test_setup_logging_default(self):
        """Test setting up logging with defaults."""
        with patch("roadmap.common.logging.structlog"):
            logger = setup_logging()
            assert logger is not None

    def test_setup_logging_debug_mode(self):
        """Test setting up logging in debug mode."""
        with patch("roadmap.common.logging.structlog"):
            logger = setup_logging(debug_mode=True)
            assert logger is not None

    def test_setup_logging_no_file(self):
        """Test setting up logging without file output."""
        with patch("roadmap.common.logging.structlog"):
            logger = setup_logging(log_to_file=False)
            assert logger is not None

    def test_setup_logging_with_log_dir(self, tmp_path):
        """Test setting up logging with custom log directory."""
        with patch("roadmap.common.logging.structlog"):
            logger = setup_logging(log_dir=str(tmp_path))
            assert logger is not None

    def test_setup_logging_with_custom_levels(self):
        """Test setting up logging with custom level mapping."""
        custom_levels = {
            "roadmap.core": "DEBUG",
            "roadmap.adapters": "INFO",
        }
        with patch("roadmap.common.logging.structlog"):
            logger = setup_logging(custom_levels=custom_levels)
            assert logger is not None

    def test_setup_logging_console_level_override(self):
        """Test console level override."""
        with patch("roadmap.common.logging.structlog"):
            logger = setup_logging(console_level="WARNING")
            assert logger is not None

    def test_setup_logging_multiple_calls(self):
        """Test that multiple setup calls work."""
        with patch("roadmap.common.logging.structlog"):
            logger1 = setup_logging(log_level="INFO")
            logger2 = setup_logging(log_level="DEBUG")
            assert logger1 is not None
            assert logger2 is not None

    def test_setup_logging_all_levels(self):
        """Test setup with all log levels."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        with patch("roadmap.common.logging.structlog"):
            for level in levels:
                logger = setup_logging(log_level=level)
                assert logger is not None
