"""Common patch helpers and decorators for testing.

This module centralizes commonly-used patch patterns to reduce repetition
of @patch decorators across the test suite.

Usage:
    from tests.fixtures.patch_helpers import with_file_operations, with_health_validator

    @with_file_operations
    def test_something(mock_builtin_open, mock_git_repo):
        # test code
        pass

    @with_all_validators
    def test_health_check(mock_roadmap_check, mock_state_check, ...):
        # test code
        pass
"""

from collections.abc import Callable
from functools import wraps
from typing import Any
from unittest.mock import patch

# Common patch targets - centralized for easy maintenance

# === Health & Backup Services ===
HEALTH_VALIDATOR_PATCH = "roadmap.core.services.health.infrastructure_validator"
BACKUP_CLEANUP_LOGGER_PATCH = (
    "roadmap.core.services.health.backup_cleanup_service.logger"
)

# === File Operations ===
BUILTIN_OPEN_PATCH = "builtins.open"
GIT_REPO_PATCH = "roadmap.adapters.git.repo"

# === Git & Version Control ===
GIT_SERVICE_PATCH = "roadmap.core.services.git.GitService"
GIT_RUN_COMMAND_PATCH = "roadmap.adapters.persistence.git_history._run_git_command"
GIT_HOOK_AUTO_SYNC_PATCH = (
    "roadmap.core.services.git.git_hook_auto_sync_service.SyncMetadataService"
)
SUBPROCESS_RUN_PATCH = "subprocess.run"

# === GitHub Integration ===
GITHUB_CLIENT_PATCH = "roadmap.adapters.github.client.GitHubClient"
GITHUB_CONFIG_VALIDATOR_REQUESTS_PATCH = (
    "roadmap.core.services.github.github_config_validator.requests.get"
)

# === Persistence & Interfaces ===
PERSISTENCE_PATCH = "roadmap.core.interfaces.persistence.PersistenceInterface"
PARSER_PATCH = "roadmap.adapters.persistence.parser.issue.IssueParser"

# === Logging ===
PERFORMANCE_TRACKING_LOGGER_PATCH = "roadmap.common.logging.performance_tracking.logger"
ERROR_LOGGING_LOGGER_PATCH = "roadmap.common.logging.error_logging.logger"

# === UI & Presentation ===
DAILY_SUMMARY_CONSOLE_PATCH = (
    "roadmap.adapters.cli.presentation.daily_summary_presenter.console"
)
PROJECT_STATUS_CONSOLE_PATCH = (
    "roadmap.adapters.cli.presentation.project_status_presenter.get_console"
)
MILESTONE_LIST_CONSOLE_PATCH = (
    "roadmap.adapters.cli.presentation.milestone_list_presenter.console"
)

# === Path Operations ===
PATH_EXISTS_PATCH = "pathlib.Path.exists"
PATH_STAT_PATCH = "pathlib.Path.stat"
INFRASTRUCTURE_VALIDATOR_PATH_PATCH = (
    "roadmap.core.services.health.infrastructure_validator_service.Path"
)


def with_health_validator(test_func: Callable) -> Callable:
    """Decorator that patches the infrastructure health validator.

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with health validator mocked
    """

    @patch(HEALTH_VALIDATOR_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_file_operations(test_func: Callable) -> Callable:
    """Decorator that patches file operations (open and git repo).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with file operations mocked
    """

    @patch(BUILTIN_OPEN_PATCH, create=True)
    @patch(GIT_REPO_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_git_service(test_func: Callable) -> Callable:
    """Decorator that patches the Git service.

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with Git service mocked
    """

    @patch(GIT_SERVICE_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_github_client(test_func: Callable) -> Callable:
    """Decorator that patches the GitHub client.

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with GitHub client mocked
    """

    @patch(GITHUB_CLIENT_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_persistence(test_func: Callable) -> Callable:
    """Decorator that patches the persistence interface.

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with persistence interface mocked
    """

    @patch(PERSISTENCE_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_parser(test_func: Callable) -> Callable:
    """Decorator that patches the issue parser.

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with parser mocked
    """

    @patch(PARSER_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_file_and_git(test_func: Callable) -> Callable:
    """Decorator that patches both file and git operations.

    Combines with_file_operations and with_git_service for convenience.

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with file and git operations mocked
    """

    @patch(GIT_SERVICE_PATCH)
    @patch(BUILTIN_OPEN_PATCH, create=True)
    @patch(GIT_REPO_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


# ============================================================================
# High-Frequency Logger Patches (65+ occurrences)
# ============================================================================


def with_performance_tracking_logger(test_func: Callable) -> Callable:
    """Decorator that patches performance tracking logger (36 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with performance logger mocked
    """

    @patch(PERFORMANCE_TRACKING_LOGGER_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_error_logging_logger(test_func: Callable) -> Callable:
    """Decorator that patches error logging logger (29 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with error logger mocked
    """

    @patch(ERROR_LOGGING_LOGGER_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_backup_cleanup_logger(test_func: Callable) -> Callable:
    """Decorator that patches backup cleanup logger (9 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with backup logger mocked
    """

    @patch(BACKUP_CLEANUP_LOGGER_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


# ============================================================================
# Subprocess and Command Execution Patches (46+ occurrences)
# ============================================================================


def with_subprocess_run(test_func: Callable) -> Callable:
    """Decorator that patches subprocess.run (26 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with subprocess.run mocked
    """

    @patch(SUBPROCESS_RUN_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_git_run_command(test_func: Callable) -> Callable:
    """Decorator that patches _run_git_command (20 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with git command execution mocked
    """

    @patch(GIT_RUN_COMMAND_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_sync_metadata_service(test_func: Callable) -> Callable:
    """Decorator that patches SyncMetadataService (21 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with SyncMetadataService mocked
    """

    @patch(GIT_HOOK_AUTO_SYNC_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


# ============================================================================
# Console/UI Presentation Patches (30+ occurrences)
# ============================================================================


def with_daily_summary_console(test_func: Callable) -> Callable:
    """Decorator that patches console in daily_summary_presenter (18 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with daily summary console mocked
    """

    @patch(DAILY_SUMMARY_CONSOLE_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_project_status_console(test_func: Callable) -> Callable:
    """Decorator that patches get_console in project_status_presenter (12 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with project status console mocked
    """

    @patch(PROJECT_STATUS_CONSOLE_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_milestone_list_console(test_func: Callable) -> Callable:
    """Decorator that patches console in milestone_list_presenter (12 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with milestone list console mocked
    """

    @patch(MILESTONE_LIST_CONSOLE_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


# ============================================================================
# Path and File System Patches (18+ occurrences)
# ============================================================================


def with_path_exists(test_func: Callable) -> Callable:
    """Decorator that patches pathlib.Path.exists (9 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with Path.exists mocked
    """

    @patch(PATH_EXISTS_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_path_stat(test_func: Callable) -> Callable:
    """Decorator that patches pathlib.Path.stat (7 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with Path.stat mocked
    """

    @patch(PATH_STAT_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_file_system_operations(test_func: Callable) -> Callable:
    """Decorator that patches common file system operations.

    Patches: pathlib.Path.exists, pathlib.Path.stat, builtins.open

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with file system operations mocked
    """

    @patch(PATH_STAT_PATCH)
    @patch(PATH_EXISTS_PATCH)
    @patch(BUILTIN_OPEN_PATCH, create=True)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_infrastructure_validator_path(test_func: Callable) -> Callable:
    """Decorator that patches Path in infrastructure_validator_service (9 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with infrastructure validator Path mocked
    """

    @patch(INFRASTRUCTURE_VALIDATOR_PATH_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


# ============================================================================
# GitHub and HTTP Request Patches (13+ occurrences)
# ============================================================================


def with_github_requests_get(test_func: Callable) -> Callable:
    """Decorator that patches requests.get in github_config_validator (13 occurrences).

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with requests.get mocked
    """

    @patch(GITHUB_CONFIG_VALIDATOR_REQUESTS_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


# ============================================================================
# Combined Multi-Patch Decorators
# ============================================================================


def with_all_loggers(test_func: Callable) -> Callable:
    """Decorator that patches all common loggers.

    Patches: performance tracking logger, error logging logger, backup cleanup logger

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with all loggers mocked
    """

    @patch(BACKUP_CLEANUP_LOGGER_PATCH)
    @patch(ERROR_LOGGING_LOGGER_PATCH)
    @patch(PERFORMANCE_TRACKING_LOGGER_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_all_consoles(test_func: Callable) -> Callable:
    """Decorator that patches all common console objects.

    Patches: daily_summary, project_status, milestone_list consoles

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with all console objects mocked
    """

    @patch(MILESTONE_LIST_CONSOLE_PATCH)
    @patch(PROJECT_STATUS_CONSOLE_PATCH)
    @patch(DAILY_SUMMARY_CONSOLE_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper


def with_git_integration(test_func: Callable) -> Callable:
    """Decorator that patches all git-related operations.

    Patches: subprocess.run, _run_git_command, SyncMetadataService

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function with git operations mocked
    """

    @patch(GIT_HOOK_AUTO_SYNC_PATCH)
    @patch(GIT_RUN_COMMAND_PATCH)
    @patch(SUBPROCESS_RUN_PATCH)
    @wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return test_func(*args, **kwargs)

    return wrapper
