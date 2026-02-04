"""Global test configuration and fixtures.

This file serves as the main entry point for pytest configuration.
All fixtures are organized in the fixtures/ directory and imported here.

Fixture organization:
  tests/fixtures/io.py          - Output and CLI utilities
  tests/fixtures/workspace.py   - Workspace isolation and temp directories
  tests/fixtures/mocks.py       - Core object mocks
  tests/fixtures/performance.py - Performance-optimized fixtures
  tests/fixtures/github.py      - GitHub integration fixtures
  tests/fixtures/assertions.py  - Assertion helpers
  tests/fixtures/validators.py  - Infrastructure validator fixtures
"""

import gc
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.persistence.storage import StateManager
from roadmap.adapters.persistence.yaml_repositories import YAMLIssueRepository
from roadmap.common.constants import IssueType, MilestoneStatus, Priority, Status
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone

# Import setup function from fixtures
# Import all fixtures from fixtures module - they're automatically available to tests
from tests.fixtures import (
    # Assertion fixtures
    assert_cli,
    assert_file,
    assert_output,
    clean_output,
    # CLI test fixtures
    cli_runner,
    cli_runner_with_init,
    # Click testing fixtures
    cli_test_data,
    effort_data,
    fast_mock_core,
    # Phase 9: Temporary directory factories
    git_repo_factory,
    github_api_response,
    # GitHub fixtures
    github_webhook_payload,
    # Workspace fixtures
    isolate_roadmap_workspace,
    isolated_workspace,
    large_effort_data,
    lightweight_mock_core,
    milestone_description_content,
    milestone_dto,
    milestone_dto_minimal,
    milestone_dto_overdue,
    milestone_with_all_components,
    mock_closed_issue,
    mock_comment_entity,
    mock_comment_factory,
    mock_config,
    mock_config_factory,
    mock_console,
    mock_console_factory,
    # Mock fixtures
    mock_core,
    mock_core_initialized,
    mock_core_simple,
    mock_core_with_github,
    mock_core_with_projects,
    mock_core_with_repo_factory,
    mock_database_connection_factory,
    mock_git_executor_factory,
    mock_git_factory,
    mock_git_operations,
    mock_github_client,
    mock_github_integration_factory,
    mock_github_manager_factory,
    mock_in_progress_issue,
    mock_issue,
    mock_issue_entity,
    mock_issue_factory,
    mock_issues,
    mock_issues_with_third,
    mock_milestone,
    mock_milestone_entity,
    mock_milestone_factory,
    mock_path_factory,
    mock_project_entity,
    mock_project_factory,
    mock_repo_factory,
    mock_response_factory,
    mock_roadmap_core_factory,
    optimized_git_repo,
    patch_filesystem_operations,
    patch_github_integration,
    # Performance fixtures
    performance_test_config,
    progress_data,
    project_description_content,
    project_dto,
    project_dto_minimal,
    project_dto_with_large_effort,
    project_with_all_components,
    roadmap_structure_factory,
    roadmap_workspace,
    selective_git_mock,
    session_mock_github_client,
    session_temp_workspace,
    shared_git_repo,
    # IO fixtures
    strip_ansi_fixture,
    temp_dir,
    temp_file_factory,
    temp_roadmap_dir,
    temp_roadmap_team_scenario,
    temp_roadmap_with_config,
    temp_roadmap_with_git_context,
    temp_roadmap_with_projects,
    temp_workspace,
    webhook_signature_creator,
)
from tests.fixtures.conftest import pytest_collection_modifyitems, setup_test_logging

# Import new Phase 1 fixtures
from tests.fixtures.mock_builders import (
    build_mock_comment,
    build_mock_core,
    build_mock_core_with_repo,
    build_mock_database_connection,
    build_mock_directory,
    build_mock_file_handle,
    build_mock_issue,
    build_mock_milestone,
    build_mock_path,
    build_mock_project,
    build_mock_repo,
    build_mock_roadmap_core,
)

__all__ = [
    # Setup
    "setup_test_logging",
    "pytest_collection_modifyitems",
    # Phase 1 Fixtures & Utilities
    "assert_cli",
    "assert_file",
    "assert_output",
    "clean_output",
    "cli_runner",
    "cli_runner_with_init",
    "cli_test_data",
    "effort_data",
    "fast_mock_core",
    "github_api_response",
    "github_webhook_payload",
    "isolate_roadmap_workspace",
    "large_effort_data",
    "lightweight_mock_core",
    "milestone_description_content",
    "milestone_dto",
    "milestone_dto_minimal",
    "milestone_dto_overdue",
    "milestone_with_all_components",
    "mock_closed_issue",
    "mock_comment_entity",
    "mock_comment_factory",
    "mock_config",
    "mock_config_factory",
    "mock_console",
    "mock_console_factory",
    "mock_core",
    "mock_core_initialized",
    "mock_core_simple",
    "mock_core_with_github",
    "mock_core_with_projects",
    "mock_core_with_repo_factory",
    "mock_database_connection_factory",
    "mock_git_factory",
    "mock_git_executor_factory",
    "mock_git_operations",
    "mock_github_client",
    "mock_github_integration_factory",
    "mock_github_manager_factory",
    "mock_in_progress_issue",
    "mock_issue",
    "mock_issue_entity",
    "mock_issue_factory",
    "mock_issues",
    "mock_issues_with_third",
    "mock_milestone",
    "mock_milestone_entity",
    "mock_milestone_factory",
    "mock_path_factory",
    "mock_project_entity",
    "mock_project_factory",
    "mock_repo_factory",
    "mock_response_factory",
    "mock_roadmap_core_factory",
    "optimized_git_repo",
    "patch_filesystem_operations",
    "patch_github_integration",
    "performance_test_config",
    "progress_data",
    "project_description_content",
    "project_dto",
    "project_dto_minimal",
    "project_dto_with_large_effort",
    "project_with_all_components",
    # Phase 9: Temporary directory factories
    "git_repo_factory",
    "isolated_workspace",
    "roadmap_structure_factory",
    "roadmap_workspace",
    "selective_git_mock",
    "session_mock_github_client",
    "session_temp_workspace",
    "shared_git_repo",
    "strip_ansi_fixture",
    "temp_dir",
    "temp_file_factory",
    "temp_roadmap_dir",
    "temp_roadmap_team_scenario",
    "temp_roadmap_with_config",
    "temp_roadmap_with_git_context",
    "temp_roadmap_with_projects",
    "temp_workspace",
    "webhook_signature_creator",
    # Builder functions (deprecated - use fixture factories instead)
    "build_mock_repo",
    "build_mock_core",
    "build_mock_core_with_repo",
    "build_mock_roadmap_core",
    "build_mock_issue",
    "build_mock_milestone",
    "build_mock_comment",
    "build_mock_project",
    "build_mock_path",
    "build_mock_file_handle",
    "build_mock_directory",
    "build_mock_database_connection",
]


# ============================================================================
# Infrastructure Validator Fixtures (Phase 2.2)
# ============================================================================
# These fixtures consolidate multi-decorator patterns used for mocking
# validators across test files (40+ @patch.object decorators reduced)


@pytest.fixture
def all_validators_mocked():
    """Fixture that mocks all 6 infrastructure validators.

    Returns a SimpleNamespace with attributes for each mocked validator:
    - roadmap_validator
    - state_validator
    - issues_validator
    - milestones_validator
    - git_validator
    - db_validator

    Usage:
        def test_something(all_validators_mocked):
            all_validators_mocked.roadmap_validator.return_value = (HealthStatus.HEALTHY, "OK")
            ...
    """
    from roadmap.core.services.health.infrastructure_validator_service import (
        DatabaseIntegrityValidator,
        GitRepositoryValidator,
        IssuesDirectoryValidator,
        MilestonesDirectoryValidator,
        RoadmapDirectoryValidator,
        StateFileValidator,
    )

    with (
        patch.object(RoadmapDirectoryValidator, "check") as mock_roadmap,
        patch.object(StateFileValidator, "check") as mock_state,
        patch.object(IssuesDirectoryValidator, "check") as mock_issues,
        patch.object(MilestonesDirectoryValidator, "check") as mock_milestones,
        patch.object(GitRepositoryValidator, "check") as mock_git,
        patch.object(DatabaseIntegrityValidator, "check") as mock_db,
    ):
        # Return as SimpleNamespace for clean attribute access
        yield SimpleNamespace(
            roadmap_validator=mock_roadmap,
            state_validator=mock_state,
            issues_validator=mock_issues,
            milestones_validator=mock_milestones,
            git_validator=mock_git,
            db_validator=mock_db,
        )


@pytest.fixture
def path_operations_mocked():
    """Fixture that mocks common pathlib.Path operations.

    Returns a SimpleNamespace with mocked Path methods:
    - exists
    - stat
    - unlink
    - glob

    Usage:
        def test_something(path_operations_mocked):
            path_operations_mocked.exists.return_value = True
            ...
    """
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.stat") as mock_stat,
        patch("pathlib.Path.unlink") as mock_unlink,
        patch("pathlib.Path.glob") as mock_glob,
    ):
        yield SimpleNamespace(
            exists=mock_exists,
            stat=mock_stat,
            unlink=mock_unlink,
            glob=mock_glob,
        )


@pytest.fixture
def backup_cleanup_mocked(path_operations_mocked):
    """Fixture for backup cleanup service tests.

    Mocks: logger, Path operations, and backup selection method.

    Returns a SimpleNamespace with:
    - logger
    - path_ops (pathlib.Path operations)
    - select_backups (BackupCleanupService._select_backups_for_deletion)

    Usage:
        def test_cleanup(backup_cleanup_mocked):
            backup_cleanup_mocked.logger.info.assert_called()
            ...
    """
    from roadmap.core.services.health.backup_cleanup_service import BackupCleanupService

    with (
        patch(
            "roadmap.core.services.health.backup_cleanup_service.logger"
        ) as mock_logger,
        patch.object(
            BackupCleanupService, "_select_backups_for_deletion"
        ) as mock_select,
    ):
        yield SimpleNamespace(
            logger=mock_logger,
            path_ops=path_operations_mocked,
            select_backups=mock_select,
        )


@pytest.fixture
def error_logging_logger_mocked():
    """Fixture for error logging tests.

    Mocks the logger in roadmap.common.logging.error_logging module.

    Returns a mock logger object for assertions.

    Usage:
        def test_error_logging(error_logging_logger_mocked):
            error_logging_logger_mocked.error.assert_called()
            ...
    """
    from unittest.mock import MagicMock

    mock_logger = MagicMock()
    with patch("roadmap.common.logging.error_logging.logger", mock_logger):
        yield mock_logger


@pytest.fixture
def performance_tracking_logger_mocked():
    """Fixture for performance tracking tests.

    Mocks the logger in roadmap.common.logging.performance_tracking module.

    Returns a mock logger object for assertions.

    Usage:
        def test_performance(performance_tracking_logger_mocked):
            performance_tracking_logger_mocked.debug.assert_called()
            ...
    """
    from unittest.mock import MagicMock

    mock_logger = MagicMock()
    with patch("roadmap.common.logging.performance_tracking.logger", mock_logger):
        yield mock_logger


@pytest.fixture
def git_run_command_mocked():
    """Fixture for git history tests.

    Mocks the _run_git_command function in roadmap.adapters.persistence.git_history module.

    Returns a mock function for setting return values and making assertions.

    Usage:
        def test_git_history(git_run_command_mocked):
            git_run_command_mocked.return_value = "abc123"
            ...
    """
    with patch("roadmap.adapters.persistence.git_history._run_git_command") as mock_cmd:
        yield mock_cmd


@pytest.fixture
def temp_dir_context():
    """Fixture for tests using TemporaryDirectory context manager pattern.

    Provides a context manager-based temporary directory that's auto-cleaned.
    Replaces: with tempfile.TemporaryDirectory() as tmpdir:

    Usage:
        def test_something(temp_dir_context):
            with temp_dir_context() as tmpdir:
                path = Path(tmpdir)
                # test code
    """
    from tempfile import TemporaryDirectory

    def _context_manager():
        return TemporaryDirectory()

    return _context_manager


# ============================================================================
# Test Independence Fixtures (Autouse)
# ============================================================================


@pytest.fixture(autouse=True)
def clear_session_cache_between_tests():
    """Clear the session cache before and after each test.

    This ensures tests don't share cached state, which is critical for
    CLI tests that invoke commands sequentially. Each test should start
    with a clean cache state.

    This fixture uses autouse=True to run automatically for all tests.

    Pattern: Cache Cleanup Between Tests
    - Prevents state leakage between tests
    - Ensures each test has a clean environment
    - Critical for CLI/command testing where cache persists
    """
    from roadmap.common.cache import clear_session_cache

    # Clear before test
    clear_session_cache()

    # Test runs here
    yield

    # Clear after test
    clear_session_cache()


# ============================================================================
# PHASE 8: NEW FIXTURES FOR FUNCTIONAL TESTING
# ============================================================================
# These fixtures support high-quality functional tests with real code paths,
# minimal mocking, and parameterization for comprehensive coverage.

# ============================================================================
# DATA FIXTURES: Raw dictionaries for test parameterization
# ============================================================================


@pytest.fixture
def p8_valid_issue_data() -> dict[str, Any]:
    """Minimal valid issue dictionary for Phase 8 tests."""
    return {
        "id": "issue-1",
        "title": "Test Issue",
        "status": Status.TODO,
        "priority": Priority.MEDIUM,
    }


@pytest.fixture
def p8_complete_issue_data(p8_valid_issue_data) -> dict[str, Any]:
    """Complete issue with all optional fields."""
    return {
        **p8_valid_issue_data,
        "headline": "Brief summary",
        "content": "Detailed description",
        "assignee": "user@example.com",
        "labels": ["bug", "urgent"],
        "milestone": "v1.0",
        "issue_type": IssueType.BUG,
        "estimated_hours": 8.0,
        "due_date": datetime(2024, 12, 31, tzinfo=UTC),
        "depends_on": ["issue-2"],
        "blocks": ["issue-3"],
        "progress_percentage": 50.0,
    }


@pytest.fixture
def p8_minimal_issue_data() -> dict[str, Any]:
    """Truly minimal valid issue (only required fields)."""
    return {
        "title": "Minimal Issue",
    }


@pytest.fixture
def p8_valid_milestone_data() -> dict[str, Any]:
    """Minimal valid milestone dictionary."""
    return {
        "name": "v1.0",
        "status": MilestoneStatus.OPEN,
    }


@pytest.fixture
def p8_complete_milestone_data(p8_valid_milestone_data) -> dict[str, Any]:
    """Complete milestone with all optional fields."""
    return {
        **p8_valid_milestone_data,
        "headline": "First release",
        "content": "Release notes",
        "due_date": datetime(2024, 12, 31, tzinfo=UTC),
    }


@pytest.fixture
def p8_valid_comment_data() -> dict[str, Any]:
    """Valid comment dictionary."""
    return {
        "id": 1,
        "issue_id": "issue-1",
        "author": "alice",
        "body": "This is a comment",
        "created_at": datetime(2024, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2024, 1, 1, tzinfo=UTC),
    }


# ============================================================================
# DOMAIN MODEL FIXTURES: Real Pydantic objects
# ============================================================================


@pytest.fixture
def p8_issue(p8_valid_issue_data) -> Issue:
    """Create a valid Issue object."""
    return Issue(**p8_valid_issue_data)


@pytest.fixture
def p8_complete_issue(p8_complete_issue_data) -> Issue:
    """Create a complete Issue with all fields."""
    return Issue(**p8_complete_issue_data)


@pytest.fixture
def p8_minimal_issue(p8_minimal_issue_data) -> Issue:
    """Create a minimal Issue."""
    return Issue(**p8_minimal_issue_data)


@pytest.fixture
def p8_milestone(p8_valid_milestone_data) -> Milestone:
    """Create a valid Milestone object."""
    return Milestone(**p8_valid_milestone_data)


@pytest.fixture
def p8_complete_milestone(p8_complete_milestone_data) -> Milestone:
    """Create a complete Milestone with all fields."""
    return Milestone(**p8_complete_milestone_data)


@pytest.fixture
def p8_comment(p8_valid_comment_data) -> Comment:
    """Create a valid Comment object."""
    return Comment(**p8_valid_comment_data)


# ============================================================================
# FILE SYSTEM FIXTURES
# ============================================================================


@pytest.fixture
def p8_issues_dir(tmp_path) -> Path:
    """Create an empty issues directory."""
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    return issues_dir


@pytest.fixture
def p8_milestones_dir(tmp_path) -> Path:
    """Create an empty milestones directory."""
    milestones_dir = tmp_path / "milestones"
    milestones_dir.mkdir(parents=True, exist_ok=True)
    return milestones_dir


@pytest.fixture
def p8_populated_issues_dir(p8_issues_dir) -> Path:
    """Create directory with sample issues as YAML files."""
    issues_data = [
        {
            "id": "issue-1",
            "title": "Build feature A",
            "status": Status.TODO,
            "milestone": "v1.0",
        },
        {
            "id": "issue-2",
            "title": "Fix bug B",
            "status": Status.IN_PROGRESS,
            "milestone": "v1.0",
        },
        {
            "id": "issue-3",
            "title": "Documentation",
            "status": Status.TODO,
            "milestone": "v2.0",
        },
        {
            "id": "issue-4",
            "title": "Unassigned task",
            "status": Status.TODO,
            "milestone": None,
        },
    ]

    # Import here to avoid circular imports
    from roadmap.adapters.persistence.parser import IssueParser

    for data in issues_data:
        issue = Issue(**data)
        issue_file = p8_issues_dir / f"{issue.id}.md"
        IssueParser.save_issue_file(issue, issue_file)

    return p8_issues_dir


@pytest.fixture
def p8_corrupted_yaml_file(tmp_path) -> Path:
    """Create a corrupted YAML file."""
    bad_file = tmp_path / "corrupted.md"
    bad_file.write_text("{ invalid: yaml: structure: [")
    return bad_file


@pytest.fixture
def p8_populated_milestones_dir(p8_milestones_dir) -> Path:
    """Create directory with sample milestones as YAML files."""
    milestones_data = [
        {"name": "v1.0", "status": MilestoneStatus.OPEN},
        {"name": "v2.0", "status": MilestoneStatus.OPEN},
        {"name": "v0.5", "status": MilestoneStatus.CLOSED},
    ]

    # Import here to avoid circular imports
    from roadmap.adapters.persistence.parser import MilestoneParser

    for data in milestones_data:
        milestone = Milestone(**data)
        milestone_file = p8_milestones_dir / f"{milestone.name}.md"
        MilestoneParser.save_milestone_file(milestone, milestone_file)

    return p8_milestones_dir


# ============================================================================
# SERVICE FIXTURES: Repositories with real storage
# ============================================================================


@pytest.fixture
def p8_mock_state_manager() -> MagicMock:
    """Create a mock StateManager for Phase 8 tests."""
    return MagicMock(spec=StateManager)


@pytest.fixture
def p8_yaml_issue_repository(
    p8_mock_state_manager, p8_issues_dir
) -> YAMLIssueRepository:
    """Create YAMLIssueRepository with temporary directory."""
    return YAMLIssueRepository(p8_mock_state_manager, p8_issues_dir)


@pytest.fixture
def p8_populated_issue_repository(
    p8_mock_state_manager, p8_populated_issues_dir
) -> YAMLIssueRepository:
    """Create YAMLIssueRepository with pre-populated data."""
    return YAMLIssueRepository(p8_mock_state_manager, p8_populated_issues_dir)


# ============================================================================
# Database Connection Cleanup
# ============================================================================


def pytest_sessionfinish(session, exitstatus):
    """Clean up database connections after all tests complete."""
    # Close any unclosed sqlite3 connections
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            try:
                obj.close()
            except (sqlite3.ProgrammingError, Exception):
                pass

    # Force garbage collection to free resources
    gc.collect()
