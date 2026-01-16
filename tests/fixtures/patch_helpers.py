"""Common patch helpers and decorators for testing.

This module centralizes commonly-used patch patterns to reduce repetition
of @patch decorators across the test suite.

Usage:
    from tests.fixtures.patch_helpers import with_file_operations, with_health_validator

    @with_file_operations
    def test_something(mock_builtin_open, mock_git_repo):
        # test code
        pass

    @with_health_validator
    def test_health_check(mock_validator):
        # test code
        pass
"""

from collections.abc import Callable
from functools import wraps
from typing import Any
from unittest.mock import patch

# Common patch targets - centralized for easy maintenance
HEALTH_VALIDATOR_PATCH = "roadmap.core.services.health.infrastructure_validator"
BUILTIN_OPEN_PATCH = "builtins.open"
GIT_REPO_PATCH = "roadmap.adapters.git.repo"
GIT_SERVICE_PATCH = "roadmap.core.services.git.GitService"
GITHUB_CLIENT_PATCH = "roadmap.adapters.github.client.GitHubClient"
PERSISTENCE_PATCH = "roadmap.core.interfaces.persistence.PersistenceInterface"
PARSER_PATCH = "roadmap.adapters.persistence.parser.issue.IssueParser"


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
