"""Shared test fixtures, factories, and mock data.

This package organizes test fixtures into logical modules:
  - io.py: Output and CLI utilities
  - workspace.py: Workspace isolation and temporary directories
  - mocks.py: Core object mocks
  - performance.py: Performance-optimized fixtures
  - github.py: GitHub integration fixtures
  - assertions.py: Assertion helpers
  - integration_helpers.py: Integration test utilities
  - data_factories.py: Data factories for test scenarios
  - test_logging.py: Logging helpers for tests
  - conftest.py: Main fixture entry point with setup functions

All fixtures are automatically available to tests via pytest's plugin system.
"""

# Re-export all fixtures for convenient importing
from .assertions import (
    CLIAssertion,
    FileAssertion,
    assert_cli,
    assert_file,
)
from .cli_test_fixtures import (
    cli_runner,
    cli_runner_with_init,
    temp_roadmap_dir,
    temp_roadmap_team_scenario,
    temp_roadmap_with_config,
    temp_roadmap_with_git_context,
    temp_roadmap_with_projects,
)
from .click_testing import (
    cli_runner as click_cli_runner,
)
from .click_testing import (
    isolated_cli_runner,
)
from .data_factories import (
    ComplexWorkflowFactory,
    IssueScenarioFactory,
    MilestoneScenarioFactory,
    TestDataBuilder,
)
from .github import (
    github_api_response,
    github_webhook_payload,
    mock_github_client,
    patch_github_integration,
    webhook_signature_creator,
)
from .integration_helpers import IntegrationTestBase
from .io import (
    assert_output,
    clean_output,
    strip_ansi_fixture,
)
from .issue_factory import IssueFactory
from .mock_builders import (
    CoreMockBuilder,
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
from .mocks import (
    cli_test_data,
    fast_mock_core,
    lightweight_mock_core,
    mock_comment_entity,
    mock_comment_factory,
    mock_config,
    mock_console,
    mock_core,
    mock_core_initialized,
    mock_core_simple,
    mock_core_with_github,
    mock_core_with_projects,
    mock_core_with_repo_factory,
    mock_git_service,
    mock_issue,
    mock_issue_entity,
    mock_issue_factory,
    mock_milestone,
    mock_milestone_entity,
    mock_milestone_factory,
    mock_path_factory,
    mock_persistence,
    mock_project_entity,
    mock_project_factory,
    mock_repo_factory,
    mock_roadmap_core_factory,
    roadmap_core,
)
from .patch_helpers import (
    with_file_and_git,
    with_file_operations,
    with_git_service,
    with_github_client,
    with_health_validator,
    with_parser,
    with_persistence,
)
from .performance import (
    mock_git_operations,
    optimized_git_repo,
    patch_filesystem_operations,
    performance_test_config,
    selective_git_mock,
    session_mock_github_client,
    shared_git_repo,
)
from .presenter_and_dto_fixtures import (
    effort_data,
    large_effort_data,
    milestone_description_content,
    milestone_dto,
    milestone_dto_minimal,
    milestone_dto_overdue,
    milestone_with_all_components,
    mock_closed_issue,
    mock_in_progress_issue,
    mock_issues,
    mock_issues_with_third,
    progress_data,
    project_description_content,
    project_dto,
    project_dto_minimal,
    project_dto_with_large_effort,
    project_with_all_components,
)
from .workspace import (
    isolate_roadmap_workspace,
    roadmap_workspace,
    session_temp_workspace,
    temp_dir,
    temp_workspace,
)

__all__ = [
    # Phase 1 Fixtures & Utilities
    "IssueFactory",
    "with_file_operations",
    "with_github_client",
    "with_git_service",
    "with_health_validator",
    "with_parser",
    "with_persistence",
    "with_file_and_git",
    # Mock builders (parametrizable functions only)
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
    "isolated_cli_runner",
    "click_cli_runner",
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
    "mock_core_with_projects",
    "mock_core_with_repo_factory",
    "mock_config",
    "mock_console",
    "mock_issue",
    "mock_issue_entity",
    "mock_milestone",
    "mock_milestone_entity",
    "mock_comment_entity",
    "mock_project_entity",
    "mock_persistence",
    "mock_persistence_interface",
    "mock_issue_parser_interface",
    "mock_git_service",
    "mock_github_client",
    "mock_repo",
    "mock_sync_service",
    "mock_path",
    "mock_path_factory",
    "mock_file_handle",
    "mock_directory",
    "mock_table_data",
    "roadmap_core",
    "lightweight_mock_core",
    "fast_mock_core",
    "cli_test_data",
    # Fixture factories (replace builder functions)
    "mock_roadmap_core_factory",
    "mock_core_with_repo_factory",
    "mock_issue_factory",
    "mock_milestone_factory",
    "mock_comment_factory",
    "mock_project_factory",
    "mock_repo_factory",
    "mock_path_factory",
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
    # Assertion fixtures and classes
    "assert_cli",
    "assert_file",
    "CLIAssertion",
    "FileAssertion",
    # Integration test helpers
    "IntegrationTestBase",
    # Data factories
    "MilestoneScenarioFactory",
    "IssueScenarioFactory",
    "ComplexWorkflowFactory",
    "TestDataBuilder",
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
]
