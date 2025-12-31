"""Shared test fixtures, factories, and mock data.

This package organizes test fixtures into logical modules:
  - io.py: Output and CLI utilities
  - workspace.py: Workspace isolation and temporary directories
  - mocks.py: Core object mocks
  - performance.py: Performance-optimized fixtures
  - github.py: GitHub integration fixtures
  - assertions.py: Assertion helpers
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
from .click_testing import (
    cli_runner,
    isolated_cli_runner,
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
from .mocks import (
    cli_test_data,
    fast_mock_core,
    lightweight_mock_core,
    mock_config,
    mock_console,
    mock_core,
    mock_core_initialized,
    mock_core_simple,
    mock_core_with_github,
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

__all__ = [
    # IO fixtures
    "strip_ansi_fixture",
    "clean_output",
    "assert_output",
    # Click testing fixtures
    "cli_runner",
    "isolated_cli_runner",
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
    "mock_config",
    "mock_console",
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
    # Assertion fixtures and classes
    "assert_cli",
    "assert_file",
    "CLIAssertion",
    "FileAssertion",
    # Integration test helpers
    "IntegrationTestBase",
]
