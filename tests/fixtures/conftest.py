"""Test fixtures - main entry point.

This module imports fixtures from specialized modules for better organization:
- io.py: Output and I/O utilities
- workspace.py: Workspace isolation and temporary directories
- mocks.py: Core object mocks
- performance.py: Performance-optimized fixtures
- github.py: GitHub integration fixtures
- assertions.py: Assertion helpers

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
    mock_config,
    mock_core,
    mock_issue,
    mock_milestone,
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
    # Mock fixtures
    "mock_core",
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
]
