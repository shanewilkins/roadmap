# Roadmap Application Architecture & Layering Guide

## Overview

The Roadmap application uses a **layered architecture** that separates concerns and enforces clean dependency rules. This document describes the layers, their responsibilities, allowed dependencies, and testing patterns.

## Architecture Layers

### Layer 1: Domain (Innermost)
**Location**: `roadmap/core/domain/`

**Responsibility**: Define core business entities and value objects with zero external dependencies.

**Exports**:
- Issue, Milestone, Project domain models
- Status, Priority, IssueType enums
- Exceptions: DomainError, ValidationError

**Allowed Dependencies**:
- None (except Python stdlib)
- Must NOT import from any other roadmap layer

**Testing**:
- Location: `tests/unit/domain/`
- Tests can use adapters/infrastructure to set up data
- Focus on business logic and domain rules

---

### Layer 2: Core (Business Logic)
**Location**: `roadmap/core/`

**Responsibility**: Implement application business logic using domain models.

**Components**:
- `core/domain/` - Domain models (see Layer 1)
- `core/interfaces/` - Interfaces/contracts for adapters
- `core/models/` - Application models (SyncState, etc)
- `core/services/` - Business logic services

**Allowed Dependencies**:
- ✅ Domain (core/domain)
- ✅ Interfaces (core/interfaces)
- ✅ Common (shared utilities)
- ✅ Infrastructure (coordination, observability, validation)
- ❌ NOT Adapters (except through interfaces)

**Testing**:
- Location: `tests/unit/core/`
- Organized by service type (baseline, sync, github, etc)
- Use mocking for adapter dependencies

---

### Layer 3: Common (Shared Utilities)
**Location**: `roadmap/common/`

**Responsibility**: Provide shared utilities, logging, error handling, configuration.

**Components**:
- `common/errors/` - Exception hierarchy
- `common/logging/` - Logging and performance tracking
- `common/console/` - Rich output formatting
- `common/configuration/` - Config management
- `common/datetime_parser/` - Date/time utilities
- `common/initialization/` - Setup workflows

**Allowed Dependencies**:
- ✅ Infrastructure
- ❌ NOT Core, Domain, or Adapters

**Testing**:
- Location: `tests/unit/common/`
- Tests may import from adapters/infrastructure for fixture setup
- Fixtures and assertion helpers live here

---

### Layer 4: Infrastructure (Coordination & Support)
**Location**: `roadmap/infrastructure/`

**Responsibility**: Cross-cutting concerns, coordination between layers, system integration.

**Subdirectories** (organized by concern):
- `infrastructure/coordination/` - Orchestration layer (RoadmapCore, etc)
- `infrastructure/git/` - Git integration operations
- `infrastructure/observability/` - Health checks, metrics, traces
- `infrastructure/validation/` - Data validation, consistency checks
- `infrastructure/security/` - Credentials, secrets management
- `infrastructure/maintenance/` - Cleanup, repairs, backups

**Allowed Dependencies**:
- ✅ Core (coordinates application logic)
- ✅ Common
- ✅ Adapters (coordinates between adapters and core)

**Testing**:
- Location: `tests/unit/infrastructure/{subdirectory}/`
- Can import from adapters (testing infrastructure/adapter coordination)
- Use mocking to avoid tight coupling

---

### Layer 5: Adapters (External Integration)
**Location**: `roadmap/adapters/`

**Responsibility**: Implement interfaces for external systems and user interaction.

**Subdirectories**:
- `adapters/cli/` - Command-line interface
- `adapters/github/` - GitHub API integration
- `adapters/git/` - Git operations (via GitPython)
- `adapters/persistence/` - File storage, database
- `adapters/sync/` - Sync backend selection/execution
- `adapters/vcs/` - Version control integration
- `adapters/presentation/` - Output formatting

**Allowed Dependencies**:
- ✅ Core (implements core interfaces)
- ✅ Common
- ✅ Infrastructure
- ✅ Other Adapters (carefully)

**Testing**:
- Location: `tests/unit/adapters/{subdirectory}/`
- Isolate from other adapters where possible
- Use mocking for external APIs

---

### Layer 6: Presentation (Output)
**Location**: `roadmap/adapters/presentation/` (conceptually, though in adapters directory)

**Responsibility**: Format and display data to users.

**Components**:
- Output formatters (table, kanban, etc)
- Display helpers and utilities

**Allowed Dependencies**:
- ✅ Core (domain models)
- ✅ Common
- ✅ Infrastructure
- ✅ Adapters (for display formats)

**Testing**:
- Location: `tests/unit/presentation/`
- May import from infrastructure/adapters for testing display logic
- Test output formatting and data presentation

---

## Dependency Rules Summary

```
Domain (layer 1)
  ↑ Only imports stdlib

Core (layer 2)
  ↑ Imports Domain, Common, Infrastructure, (Adapters via interfaces)

Common (layer 3)
  ↑ Imports Infrastructure

Infrastructure (layer 4)
  ↑ Imports Core, Common, Adapters

Adapters (layer 5)
  ↑ Imports Core, Common, Infrastructure, (other Adapters)

Presentation (layer 6)
  ↑ Imports Core, Common, Infrastructure, Adapters
```

## Test Layer Organization

Tests mirror the application layer structure:

```
tests/unit/
├── domain/              # Domain model tests (can use full stack for setup)
├── core/                # Core service tests
│   ├── services/        # Service layer tests
│   ├── models/          # Model tests
│   └── interfaces/      # Interface contract tests
├── common/              # Common utilities tests
│   ├── errors/
│   ├── logging/
│   └── formatters/
├── infrastructure/      # Infrastructure tests by concern
│   ├── coordination/
│   ├── git/
│   ├── observability/
│   ├── validation/
│   ├── security/
│   └── maintenance/
├── adapters/            # Adapter tests by type
│   ├── cli/
│   ├── github/
│   ├── git/
│   ├── persistence/
│   └── sync/
└── presentation/        # Presentation/display tests
```

## Test Layer Violation Rules

### Acceptable Violations
- ✅ **Domain tests** using full stack for setup (integration-style)
- ✅ **Common tests** importing adapters for fixture creation
- ✅ **Core tests** importing adapter error types (when core service uses them)
- ✅ **Infrastructure tests** importing adapters (testing coordination)
- ✅ **Test fixtures** importing from any layer (setup-only)

### Unacceptable Violations
- ❌ **Unit tests** importing implementation details unnecessarily
- ❌ **Tests** breaking isolation with direct adapter imports
- ❌ **Circular imports** between test modules
- ❌ **Domain/Core** tests importing CLI or presentation logic

## Architecture Principles

### 1. Dependency Inversion
- Core defines interfaces
- Adapters implement interfaces
- Never inject concrete adapters into core

### 2. Single Responsibility
- Each layer has one reason to change
- Domain: Business rules change
- Core: Application logic changes
- Adapters: External system integration changes

### 3. Isolation
- Each layer can be tested independently
- Mock dependencies across layer boundaries
- Use interfaces for contracts

### 4. Gradual Integration
- Unit tests: Single layer + mocked dependencies
- Integration tests: Multiple layers working together

## Migration Path

If you need to add a new feature:

1. **Define domain models** (Layer 1: Domain)
2. **Implement business logic** (Layer 2: Core/Services)
3. **Integrate with infrastructure** (Layer 4: Infrastructure)
4. **Build adapters** (Layer 5: Adapters)
5. **Add presentation** (Layer 6: Presentation)
6. **Write tests** at each layer

## Common Mistakes to Avoid

### ❌ Don't: Import adapters into core
```python
# BAD - Core importing adapter implementation
from roadmap.adapters.github.github import GitHubClient
```

### ✅ Do: Use interfaces
```python
# GOOD - Core depending on interface
from roadmap.core.interfaces.github import GitHubBackendInterface
```

### ❌ Don't: Put business logic in adapters
```python
# BAD - Business logic in CLI adapter
def sync_command(self):
    issues = self.core.get_issues()
    # <business logic here>
```

### ✅ Do: Keep business logic in core
```python
# GOOD - Business logic in core, adapters just call it
def sync_command(self):
    result = self.core.sync_with_github()
    return self.format_result(result)
```

### ❌ Don't: Skip testing layer boundaries
```python
# BAD - Test importing everything it needs
from roadmap.adapters.cli import main
from roadmap.adapters.github import GitHubClient
from roadmap.adapters.persistence import FileStorage
```

### ✅ Do: Mock across boundaries
```python
# GOOD - Test mocks adapter dependencies
from unittest.mock import MagicMock
from roadmap.core.services.sync import SyncService

def test_sync():
    mock_github = MagicMock(spec=GitHubBackendInterface)
    service = SyncService(mock_github)
    # test with mock
```

## Layer Violation Statistics

**Current State** (January 2026):
- Production Code Layer Violations: **97** (down from 685 baseline)
- Test Layer Violations: **51** (from 52 after Phase 6d.4)
- No Circular Imports: ✅ Clean
- No Core→Adapters Direct Imports: ✅ Clean

**Improvement Goal**: <50 total violations through ongoing refactoring

---

**Last Updated**: January 15, 2026  
**Phase**: 6 - Architecture & Code Quality  
**Maintainer**: GitHub Copilot
