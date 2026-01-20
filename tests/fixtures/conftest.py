"""Test fixtures - main entry point.

This module imports fixtures from specialized modules for better organization:
- io.py: Output and I/O utilities
- workspace.py: Workspace isolation and temporary directories
- mocks.py: Core object mocks
- performance.py: Performance-optimized fixtures
- github.py: GitHub integration fixtures
- assertions.py: Assertion helpers
- presenter_and_dto_fixtures.py: Presenter and DTO fixtures

All fixtures are automatically available to all tests through pytest's
fixture discovery mechanism.
"""

# Import all fixtures to make them available to pytest
import pytest

from .assertions import (
    assert_cli,
    assert_file,
)
from .github import (
    github_api_response,
    github_webhook_payload,
    mock_github_client,
    patch_github_integration,
    webhook_signature_creator,
)
from .io import (
    assert_output,
    clean_output,
    strip_ansi_fixture,
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
    mock_directory,
    mock_file_handle,
    mock_git_service,
    mock_issue,
    mock_issue_entity,
    mock_issue_factory,
    mock_issue_parser_interface,
    mock_milestone,
    mock_milestone_entity,
    mock_milestone_factory,
    mock_path,
    mock_persistence,
    mock_persistence_interface,
    mock_project_entity,
    mock_project_factory,
    mock_repo,
    mock_repo_factory,
    mock_roadmap_core_factory,
    mock_sync_service,
    mock_table_data,
    roadmap_core,
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


@pytest.fixture(autouse=True, scope="session")
def setup_test_logging():
    """Configure logging for all tests to prevent production logging from breaking tests."""
    from roadmap.common.logging import configure_for_testing

    configure_for_testing()


def pytest_collection_modifyitems(config, items):
    """Add performance optimizations based on test markers."""
    for item in items:
        # Mark slow tests automatically based on patterns
        if any(
            pattern in item.nodeid
            for pattern in [
                "git_hooks_integration",
                "test_multi_branch_workflow",
                "test_hook_performance",
                "repository_scanner_integration",
                "test_complete_roadmap_lifecycle",
            ]
        ):
            item.add_marker(pytest.mark.slow)

        # Add integration marker for heavy tests
        if "integration" in item.nodeid.lower() and not item.get_closest_marker("unit"):
            item.add_marker(pytest.mark.integration)

        # Add performance optimization markers
        if "git_hooks_integration" in item.nodeid:
            item.add_marker(pytest.mark.performance)

        # Auto-apply optimized fixtures for slow tests (but not integration tests)
        if item.get_closest_marker("slow") and "repository_scanner" in item.nodeid:
            # Skip mocking for integration tests that need real repository scanning
            if not item.get_closest_marker("integration"):
                # Add selective mocking marker for repository scanner tests
                item.add_marker(pytest.mark.mock_scanning)


__all__ = [
    # IO fixtures
    "strip_ansi_fixture",
    "clean_output",
    "assert_output",
    # Workspace fixtures
    "isolate_roadmap_workspace",
    "roadmap_workspace",
    "temp_dir",
    "temp_workspace",
    "session_temp_workspace",
    # Mock fixtures - Core
    "mock_core",
    "mock_core_initialized",
    "mock_core_simple",
    "mock_core_with_github",
    "mock_core_with_projects",
    "mock_config",
    "mock_console",
    "roadmap_core",
    "lightweight_mock_core",
    "fast_mock_core",
    "cli_test_data",
    # Mock fixtures - Services
    "mock_git_service",
    "mock_github_client",
    "mock_repo",
    "mock_sync_service",
    # Mock fixtures - Filesystem
    "mock_path",
    "mock_file_handle",
    "mock_directory",
    # Mock fixtures - Domain Entities
    "mock_issue",
    "mock_issue_entity",
    "mock_milestone",
    "mock_milestone_entity",
    "mock_comment_entity",
    "mock_project_entity",
    # Mock fixtures - Interfaces
    "mock_persistence",
    "mock_persistence_interface",
    "mock_issue_parser_interface",
    # Mock fixtures - UI/Presentation
    "mock_table_data",
    # Fixture Factories (replaces builder functions)
    "mock_roadmap_core_factory",
    "mock_core_with_projects",
    "mock_issue_factory",
    "mock_milestone_factory",
    "mock_comment_factory",
    "mock_project_factory",
    "mock_repo_factory",
    "mock_issue_entity",
    "mock_milestone",
    "mock_milestone_entity",
    "mock_comment_entity",
    "mock_project_entity",
    # Mock fixtures - Interfaces
    "mock_persistence",
    "mock_persistence_interface",
    "mock_issue_parser_interface",
    # Mock fixtures - UI/Presentation
    "mock_table_data",
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
]
