"""Tests for error classes."""

from pathlib import Path

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity, RoadmapError
from roadmap.common.errors.error_file import (
    FileOperationError,
    FileReadError,
    FileWriteError,
)
from roadmap.common.errors.error_git import ConfigurationError, GitOperationError
from roadmap.common.errors.error_network import NetworkError
from roadmap.common.errors.error_security import SecurityError


class TestGitOperationError:
    """Tests for GitOperationError."""

    def test_git_error_with_command(self):
        """Test GitOperationError with command info."""
        error = GitOperationError(
            "Failed to pull", command="git pull origin main", exit_code=1
        )

        assert error.message == "Failed to pull"
        assert error.command == "git pull origin main"
        assert error.exit_code == 1
        assert error.category == ErrorCategory.GIT_OPERATION
        assert error.severity == ErrorSeverity.HIGH

    def test_git_error_without_command(self):
        """Test GitOperationError without command info."""
        error = GitOperationError("Git operation failed")

        assert error.message == "Git operation failed"
        assert error.command is None
        assert error.exit_code is None

    def test_git_error_context(self):
        """Test that git info is in context."""
        error = GitOperationError("Failed to pull", command="git pull", exit_code=128)

        assert "command" in error.context
        assert error.context["command"] == "git pull"
        assert error.context["exit_code"] == 128

    def test_git_error_custom_severity(self):
        """Test GitOperationError with custom severity."""
        error = GitOperationError("Git issue", severity=ErrorSeverity.CRITICAL)

        assert error.severity == ErrorSeverity.CRITICAL

    def test_git_error_with_cause(self):
        """Test GitOperationError with cause."""
        cause = RuntimeError("Permission denied")
        error = GitOperationError("Git operation failed", cause=cause)

        assert error.cause == cause


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_config_error_with_file_path(self):
        """Test ConfigurationError with file path."""
        config_path = Path(".roadmap/settings.toml")
        error = ConfigurationError("Invalid config", config_file=config_path)

        assert error.message == "Invalid config"
        assert error.config_file == config_path
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH

    def test_config_error_with_string_path(self):
        """Test ConfigurationError with string path."""
        config_file = "/home/user/.roadmap/settings.toml"
        error = ConfigurationError("Config parse error", config_file=config_file)

        assert error.config_file == config_file
        assert config_file in error.context["config_file"]

    def test_config_error_without_file(self):
        """Test ConfigurationError without file info."""
        error = ConfigurationError("Configuration error")

        assert error.config_file is None

    def test_config_error_context(self):
        """Test config file info is in context."""
        config_file = "settings.toml"
        error = ConfigurationError("Error", config_file=config_file)

        assert "config_file" in error.context

    def test_config_error_custom_severity(self):
        """Test ConfigurationError with custom severity."""
        error = ConfigurationError("Config issue", severity=ErrorSeverity.CRITICAL)

        assert error.severity == ErrorSeverity.CRITICAL


class TestFileOperationError:
    """Tests for FileOperationError."""

    def test_file_operation_error_basic(self):
        """Test basic FileOperationError."""
        error = FileOperationError("File operation failed")

        assert error.message == "File operation failed"
        assert error.category == ErrorCategory.FILE_OPERATION

    def test_file_operation_error_with_path(self):
        """Test FileOperationError with file path."""
        file_path = Path(".roadmap/issues/test.md")
        error = FileOperationError("Cannot read file", file_path=file_path)

        assert error.message == "Cannot read file"
        assert error.file_path == file_path

    def test_file_read_error(self):
        """Test FileReadError."""
        file_path = Path("test.md")
        error = FileReadError("Permission denied", file_path=file_path)

        assert error.message == "Permission denied"
        assert error.file_path == file_path

    def test_file_write_error(self):
        """Test FileWriteError."""
        file_path = Path("test.md")
        error = FileWriteError("Disk full", file_path=file_path)

        assert error.message == "Disk full"
        assert error.file_path == file_path


class TestSecurityError:
    """Tests for SecurityError."""

    def test_security_error_basic(self):
        """Test basic SecurityError."""
        error = SecurityError("Permission denied")

        assert error.message == "Permission denied"
        assert error.category == ErrorCategory.PERMISSION
        assert error.severity == ErrorSeverity.CRITICAL

    def test_security_error_with_resource(self):
        """Test SecurityError with resource info."""
        error = SecurityError("Access denied", resource="/sensitive/file")

        assert error.message == "Access denied"


class TestNetworkError:
    """Tests for NetworkError."""

    def test_network_error_basic(self):
        """Test basic NetworkError."""
        error = NetworkError("Connection failed")

        assert error.message == "Connection failed"
        assert error.category == ErrorCategory.NETWORK

    def test_network_error_with_details(self):
        """Test NetworkError with endpoint/status."""
        error = NetworkError(
            "API error", url="https://api.github.com/repos", status_code=403
        )

        assert error.message == "API error"
        assert error.url == "https://api.github.com/repos"
        assert error.status_code == 403


class TestErrorInheritance:
    """Tests for error class hierarchy."""

    def test_git_error_is_roadmap_error(self):
        """Test that GitOperationError is a RoadmapError."""
        error = GitOperationError("Test")
        assert isinstance(error, RoadmapError)

    def test_config_error_is_roadmap_error(self):
        """Test that ConfigurationError is a RoadmapError."""
        error = ConfigurationError("Test")
        assert isinstance(error, RoadmapError)

    def test_file_operation_error_is_roadmap_error(self):
        """Test that FileOperationError is a RoadmapError."""
        error = FileOperationError("Test")
        assert isinstance(error, RoadmapError)

    def test_file_read_error_is_file_operation_error(self):
        """Test that FileReadError is a FileOperationError."""
        error = FileReadError("Test")
        assert isinstance(error, FileOperationError)

    def test_security_error_is_roadmap_error(self):
        """Test that SecurityError is a RoadmapError."""
        error = SecurityError("Test")
        assert isinstance(error, RoadmapError)

    def test_network_error_is_roadmap_error(self):
        """Test that NetworkError is a RoadmapError."""
        error = NetworkError("Test")
        assert isinstance(error, RoadmapError)
