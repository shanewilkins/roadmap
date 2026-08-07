"""Tests for git operation and configuration error classes."""

from pathlib import Path

import pytest

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity
from roadmap.common.errors.error_git import ConfigurationError, GitOperationError


class TestGitOperationError:
    """Tests for GitOperationError class."""

    def test_git_operation_error_basic(self):
        """Test basic GitOperationError."""
        error = GitOperationError("Git command failed")

        assert error.message == "Git command failed"
        assert error.category == ErrorCategory.GIT_OPERATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.command is None
        assert error.exit_code is None

    def test_git_operation_error_with_command(self):
        """Test GitOperationError with command info."""
        error = GitOperationError("Command failed", command="git pull origin main")

        assert error.message == "Command failed"
        assert error.command == "git pull origin main"
        assert "command" in error.context
        assert error.context["command"] == "git pull origin main"

    def test_git_operation_error_with_exit_code(self):
        """Test GitOperationError with exit code."""
        error = GitOperationError("Git failed", exit_code=128)

        assert error.exit_code == 128
        assert error.context["exit_code"] == 128

    def test_git_operation_error_with_all_fields(self):
        """Test GitOperationError with all fields."""
        error = GitOperationError(
            "Merge conflict", command="git merge feature-branch", exit_code=1
        )

        assert error.message == "Merge conflict"
        assert error.command == "git merge feature-branch"
        assert error.exit_code == 1
        assert error.context["command"] == "git merge feature-branch"
        assert error.context["exit_code"] == 1

    def test_git_operation_error_custom_severity(self):
        """Test GitOperationError with custom severity."""
        error = GitOperationError("Critical git issue", severity=ErrorSeverity.CRITICAL)

        assert error.severity == ErrorSeverity.CRITICAL

    def test_git_operation_error_with_cause(self):
        """Test GitOperationError with cause."""
        cause = OSError("File system error")
        error = GitOperationError("Git operation failed", cause=cause)

        assert error.cause is cause

    @pytest.mark.parametrize(
        "command,exit_code",
        [
            ("git status", 0),
            ("git commit -m 'test'", 1),
            ("git push", 128),
            ("git fetch", 255),
        ],
    )
    def test_git_operation_error_parametrized(self, command, exit_code):
        """Test GitOperationError with various command and exit codes."""
        error = GitOperationError(
            f"Command '{command}' returned {exit_code}",
            command=command,
            exit_code=exit_code,
        )

        assert error.command == command
        assert error.exit_code == exit_code


class TestConfigurationError:
    """Tests for ConfigurationError class."""

    def test_configuration_error_basic(self):
        """Test basic ConfigurationError."""
        error = ConfigurationError("Invalid config")

        assert error.message == "Invalid config"
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.config_file is None

    def test_configuration_error_with_string_path(self):
        """Test ConfigurationError with string file path."""
        error = ConfigurationError("Config file not found", config_file=".roadmaprc")

        assert error.message == "Config file not found"
        assert error.config_file == ".roadmaprc"
        assert "config_file" in error.context
        assert error.context["config_file"] == ".roadmaprc"

    def test_configuration_error_with_path_object(self):
        """Test ConfigurationError with Path object."""
        config_path = Path(".roadmaprc")
        error = ConfigurationError("Cannot parse config", config_file=config_path)

        assert error.config_file == config_path
        assert error.context["config_file"] == str(config_path)

    def test_configuration_error_absolute_path(self):
        """Test ConfigurationError with absolute path."""
        config_path = Path("/home/user/.roadmaprc")
        error = ConfigurationError("Config parse error", config_file=config_path)

        assert error.config_file == config_path
        assert error.context["config_file"] == str(config_path)

    def test_configuration_error_custom_severity(self):
        """Test ConfigurationError with custom severity."""
        error = ConfigurationError(
            "Critical config issue", severity=ErrorSeverity.CRITICAL
        )

        assert error.severity == ErrorSeverity.CRITICAL

    def test_configuration_error_with_cause(self):
        """Test ConfigurationError with cause."""
        cause = ValueError("Invalid YAML")
        error = ConfigurationError("Failed to parse config", cause=cause)

        assert error.cause is cause

    @pytest.mark.parametrize(
        "filename",
        [
            ".roadmaprc",
            ".roadmap/config.yaml",
            "~/.roadmaprc",
            "/etc/roadmap/config.yaml",
        ],
    )
    def test_configuration_error_various_paths(self, filename):
        """Test ConfigurationError with various file paths."""
        error = ConfigurationError("Config error", config_file=filename)

        assert error.config_file == filename
        assert error.context["config_file"] == filename

    def test_configuration_error_with_context_dict(self):
        """Test ConfigurationError with additional context."""
        error = ConfigurationError(
            "Config validation failed",
            config_file=".roadmaprc",
            context={"line_number": 42, "field": "status_colors"},
        )

        assert "config_file" in error.context
        assert "line_number" in error.context
        assert "field" in error.context
        assert error.context["line_number"] == 42
        assert error.context["field"] == "status_colors"
