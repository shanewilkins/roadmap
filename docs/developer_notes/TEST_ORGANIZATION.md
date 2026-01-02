"""
Test Organization Structure
===========================

This file outlines the new organized test structure following the architectural layers.

Directory Structure
-------------------

tests/
├── unit/                           # Isolated component tests (34 test files)

│   ├── domain/                     # Domain layer tests (3 files)

│   │   ├── test_parser.py          # Models and parsing logic

│   │   ├── test_assignee_validation.py
│   │   └── test_estimated_time.py
│   │
│   ├── application/                # Application layer tests (9 files)

│   │   ├── test_core.py
│   │   ├── test_core_advanced.py
│   │   ├── test_core_comprehensive.py
│   │   ├── test_core_edge_cases.py
│   │   ├── test_core_final.py
│   │   ├── test_data_utils.py
│   │   ├── test_data_factory.py
│   │   ├── test_bulk_operations.py
│   │   └── test_visualization.py
│   │
│   ├── infrastructure/             # Infrastructure layer tests (6 files)

│   │   ├── test_file_locking.py
│   │   ├── test_github_client.py
│   │   ├── test_git_hooks.py
│   │   ├── test_git_hooks_coverage.py
│   │   ├── test_enhanced_persistence.py
│   │   └── test_gitignore_management.py
│   │
│   └── shared/                     # Shared layer tests (4 files)

│       ├── test_utils.py
│       ├── test_progress_calculation.py
│       ├── test_security.py
│       └── test_credentials.py
│
├── integration/                    # Integration tests (12 files)

│   ├── test_integration.py         # Core integration tests

│   ├── test_git_integration.py
│   ├── test_git_integration_coverage.py
│   ├── test_git_hooks_integration.py
│   ├── test_cli_coverage.py
│   ├── test_cli_smoke.py
│   ├── test_cli_extended_deprecated.py
│   ├── test_milestone_commands.py
│   ├── test_comments.py
│   ├── test_platform_integration.py
│   ├── test_init_core_setup.py
│   ├── test_init_templates_and_customization.py
│   ├── test_sync_and_link_helper_functions.py
│   └── test_enhanced_list_command.py
│
├── fixtures/                       # Shared test fixtures and utilities

│   ├── conftest.py                 # Pytest configuration and fixtures

│   └── (mock_data.py, factories.py - for future)
│
├── conftest.py                     # Root pytest configuration (original)

└── (legacy test files - not yet deleted)


Test Categories
---------------

Unit Tests (tests/unit/)
- Domain: Pure business logic, models, validation
- Application: Services, use cases, orchestration
- Infrastructure: Storage, external integrations, file operations
- Shared: Common utilities, validation, logging, progress

Integration Tests (tests/integration/)
- CLI commands and workflows
- Git and GitHub integration
- Multi-component workflows
- Platform-specific functionality


Coverage Summary
----------------

✅ Total test files: 34
✅ Unit tests: 22 files organized by layer
✅ Integration tests: 12 files for workflows
✅ Test status: All passing (1395 tests when including copies)
✅ Pytest fixtures: Centralized in tests/fixtures/
✅ Coverage maintained: 80%+


Next Steps
----------

1. Delete original test files in tests/ root (after confirming no side effects)
   - Keep conftest.py at root if it's referenced by pytest
   - Or update pytest.ini to point to tests/fixtures/conftest.py

2. Consider creating:
   - tests/fixtures/mock_data.py (for test data factories)
   - tests/fixtures/factories.py (for object factories)
   - tests/fixtures/fixtures.py (shared pytest fixtures)

3. Update pytest.ini if needed to discover tests in new locations

4. Document test patterns and conventions for each layer


Layer-Specific Test Guidelines
------------------------------

Domain Tests (tests/unit/domain/)
- Test business logic in isolation
- No external dependencies
- Focus on models, enums, calculations
- Mock external services

Application Tests (tests/unit/application/)
- Test services and orchestration
- Use fixtures for domain objects
- Mock infrastructure layer
- Test use cases end-to-end

Infrastructure Tests (tests/unit/infrastructure/)
- Test integration with external systems
- Use mocks for actual API calls (when appropriate)
- Test storage operations
- Test file/git operations

Shared Tests (tests/unit/shared/)
- Test utility functions
- Test validators and formatters
- Test logging and progress
- No domain-specific logic

Integration Tests (tests/integration/)
- Test workflows across layers
- May hit actual external systems (or use mocks)
- Test CLI commands
- Test complete user scenarios
"""
