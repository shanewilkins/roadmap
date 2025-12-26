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
"""

# Import setup function from fixtures
# Import all fixtures from fixtures module - they're automatically available to tests
from tests.fixtures import (
    # Assertion fixtures
    assert_cli,
    assert_file,
    assert_output,
    clean_output,
    # Click testing fixtures
    cli_runner,
    cli_test_data,
    fast_mock_core,
    github_api_response,
    # GitHub fixtures
    github_webhook_payload,
    # Workspace fixtures
    isolate_roadmap_workspace,
    lightweight_mock_core,
    mock_config,
    mock_console,
    # Mock fixtures
    mock_core,
    mock_core_initialized,
    mock_core_simple,
    mock_core_with_github,
    mock_git_operations,
    mock_github_client,
    mock_issue,
    mock_milestone,
    optimized_git_repo,
    patch_filesystem_operations,
    patch_github_integration,
    # Performance fixtures
    performance_test_config,
    roadmap_workspace,
    selective_git_mock,
    session_mock_github_client,
    session_temp_workspace,
    shared_git_repo,
    # IO fixtures
    strip_ansi_fixture,
    temp_dir,
    temp_workspace,
    webhook_signature_creator,
)
from tests.fixtures.conftest import pytest_collection_modifyitems, setup_test_logging

__all__ = [
    # Setup
    "setup_test_logging",
    "pytest_collection_modifyitems",
    # IO fixtures
    "strip_ansi_fixture",
    "clean_output",
    "assert_output",
    # Click testing fixtures
    "cli_runner",
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
]
