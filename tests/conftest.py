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

from types import SimpleNamespace
from unittest.mock import patch

import pytest

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
    github_api_response,
    # GitHub fixtures
    github_webhook_payload,
    # Workspace fixtures
    isolate_roadmap_workspace,
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
    mock_console,
    # Mock fixtures
    mock_core,
    mock_core_initialized,
    mock_core_simple,
    mock_core_with_github,
    mock_core_with_projects,
    mock_core_with_repo_factory,
    mock_git_operations,
    mock_github_client,
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
    roadmap_workspace,
    selective_git_mock,
    session_mock_github_client,
    session_temp_workspace,
    shared_git_repo,
    # IO fixtures
    strip_ansi_fixture,
    temp_dir,
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
    "mock_console",
    "mock_core",
    "mock_core_initialized",
    "mock_core_simple",
    "mock_core_with_github",
    "mock_core_with_projects",
    "mock_core_with_repo_factory",
    "mock_git_operations",
    "mock_github_client",
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
    "roadmap_workspace",
    "selective_git_mock",
    "session_mock_github_client",
    "session_temp_workspace",
    "shared_git_repo",
    "strip_ansi_fixture",
    "temp_dir",
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
