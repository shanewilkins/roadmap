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
    mock_config,
    mock_console,
    # Mock fixtures
    mock_core,
    mock_core_initialized,
    mock_core_simple,
    mock_core_with_github,
    mock_git_operations,
    mock_github_client,
    mock_in_progress_issue,
    mock_issue,
    mock_issues,
    mock_issues_with_third,
    mock_milestone,
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
from tests.fixtures.issue_factory import IssueFactory
from tests.fixtures.mock_builders import (
    CoreMockBuilder,
    build_mock_core,
    build_mock_core_with_repo,
    build_mock_directory,
    build_mock_file_handle,
    build_mock_git_service,
    build_mock_github_service,
    build_mock_repo,
    build_mock_sync_service,
)
from tests.fixtures.patch_helpers import (
    with_file_operations,
    with_git_service,
    with_github_client,
    with_health_validator,
    with_parser,
    with_persistence,
)

__all__ = [
    # Setup
    "setup_test_logging",
    "pytest_collection_modifyitems",
    # Phase 1 Fixtures & Utilities
    "IssueFactory",
    "with_file_operations",
    "with_github_client",
    "with_git_service",
    "with_health_validator",
    "with_parser",
    "with_persistence",
    # Phase 2 Mock Builders
    "build_mock_repo",
    "build_mock_core",
    "build_mock_core_with_repo",
    "build_mock_git_service",
    "build_mock_github_service",
    "build_mock_sync_service",
    "build_mock_file_handle",
    "build_mock_directory",
    "CoreMockBuilder",
    # IO fixtures
    "strip_ansi_fixture",
    "clean_output",
    "assert_output",
    # Click testing fixtures
    "cli_runner",
    "cli_runner_with_init",
    "temp_roadmap_dir",
    "temp_roadmap_with_projects",
    "temp_roadmap_with_config",
    "temp_roadmap_with_git_context",
    "temp_roadmap_team_scenario",
    # Workspace fixtures
    "isolate_roadmap_workspace",
    "roadmap_workspace",
    "temp_dir",
    "temp_workspace",
    "session_temp_workspace",
    # Mock fixtures
    "mock_core",
    "mock_core_initialized",
    "mock_core_simple",
    "mock_core_with_github",
    "mock_console",
    "mock_config",
    "mock_issue",
    "mock_milestone",
    "lightweight_mock_core",
    "fast_mock_core",
    "cli_test_data",
    # Performance fixtures
    "performance_test_config",
    "shared_git_repo",
    "optimized_git_repo",
    "patch_filesystem_operations",
    "mock_git_operations",
    "selective_git_mock",
    "session_mock_github_client",
    # GitHub fixtures
    "github_webhook_payload",
    "webhook_signature_creator",
    "github_api_response",
    "mock_github_client",
    "patch_github_integration",
    # Assertion fixtures
    "assert_cli",
    "assert_file",
    # Presenter and DTO fixtures
    "milestone_dto",
    "milestone_dto_minimal",
    "milestone_dto_overdue",
    "project_dto",
    "project_dto_minimal",
    "project_dto_with_large_effort",
    "mock_closed_issue",
    "mock_in_progress_issue",
    "mock_issues",
    "mock_issues_with_third",
    "progress_data",
    "effort_data",
    "large_effort_data",
    "milestone_description_content",
    "project_description_content",
    "milestone_with_all_components",
    "project_with_all_components",
    # Validator fixtures
    "all_validators_mocked",
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
