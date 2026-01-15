# Codebase Structure (Phase 5 - Post-Refactoring)

This document describes the Python codebase organization following Phase 5 refactoring (Code Readability & Organization).

## Overview

The Roadmap CLI tool follows a **layered architecture** with clear separation of concerns:

```
Adapters Layer (CLI)
        ↓
Application Layer (Core)
        ↓
Domain Layer (Models, Interfaces)
        ↓
Infrastructure Layer (Persistence, GitHub)
        ↓
Shared Layer (Common utilities, formatting)
```

## Directory Structure

### Root Level: `/roadmap/`

```
roadmap/
├── __init__.py                    # Package initialization, exports
├── adapters/                      # ⭐ Presentation Layer - CLI interface
├── core/                          # ⭐ Application/Business Logic Layer
├── common/                        # ⭐ Cross-cutting utilities
└── shared/                        # ⭐ Shared infrastructure & formatting
```

---

## Layer 1: Adapters (`/roadmap/adapters/`)

**Purpose**: Translates CLI user input to domain operations.

```
adapters/
├── cli/                           # Click CLI command structure
│   ├── __init__.py               # Exports main CLI groups
│   ├── cli_command_helpers.py    # CLI helper utilities (renamed from helpers.py)
│   ├── console_exports.py        # Console-related re-exports (renamed from utils.py)
│   ├── root.py                   # Root command (@roadmap)
│   │
│   ├── analysis/                 # Analysis commands
│   │   ├── __init__.py
│   │   ├── list.py
│   │   ├── kanban.py
│   │   ├── view.py
│   │   └── analyze.py
│   │
│   ├── comment/                  # Comment commands
│   │   ├── __init__.py
│   │   └── comment.py
│   │
│   ├── config/                   # Configuration commands
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── validate.py
│   │
│   ├── crud/                     # CRUD operations (create, read, update, delete)
│   │   ├── __init__.py
│   │   ├── create.py
│   │   ├── delete.py
│   │   ├── close.py
│   │   ├── archive.py
│   │   ├── restore.py
│   │   ├── assign.py
│   │   ├── update.py
│   │   └── recalculate.py
│   │
│   ├── dtos/                     # Data Transfer Objects for CLI
│   │   ├── __init__.py
│   │   ├── issue_dto.py
│   │   ├── milestone_dto.py
│   │   └── view_dto.py
│   │
│   ├── health/                   # Health check commands
│   │   ├── __init__.py
│   │   └── health.py
│   │
│   ├── init/                     # Initialization commands
│   │   ├── __init__.py
│   │   ├── init.py
│   │   └── onboarding.py
│   │
│   ├── issues/                   # Issue-specific commands
│   │   ├── __init__.py
│   │   ├── issue.py
│   │   ├── start.py
│   │   └── deps.py              # Dependency management
│   │
│   ├── milestones/              # Milestone commands
│   │   ├── __init__.py
│   │   ├── milestone.py
│   │   ├── create.py
│   │   └── close.py
│   │
│   └── projects/                # Project commands
│       ├── __init__.py
│       └── project.py
```

**Key Changes in Phase 5**:
- Renamed `helpers.py` → `cli_command_helpers.py` (more descriptive)
- Renamed `utils.py` → `console_exports.py` (clarifies purpose)
- Renamed `archive_utils.py` → `archive_operations.py` (follows verb-noun pattern)

---

## Layer 2: Core (`/roadmap/core/`)

**Purpose**: Business logic, domain services, and application state management.

```
core/
├── __init__.py
│
├── domain/                       # Domain layer (pure data models)
│   ├── __init__.py
│   ├── entities.py              # Core issue/milestone entities
│   ├── value_objects.py         # Value objects (ID, Status, Priority)
│   └── interfaces.py            # Domain interfaces/contracts
│
├── models/                      # Data models for serialization
│   ├── __init__.py
│   ├── issue.py                # Issue model
│   ├── milestone.py            # Milestone model
│   └── baseline.py             # Baseline model
│
├── interfaces/                  # Plugin/extension interfaces
│   ├── __init__.py
│   ├── sync_interface.py
│   ├── persistence_interface.py
│   └── github_interface.py
│
├── services/                    # ⭐ Core services layer (52 → organized)
│   ├── __init__.py
│   │
│   ├── baseline/               # Baseline retrieval & building
│   │   ├── __init__.py
│   │   ├── baseline_builder.py
│   │   ├── baseline_builder_progress.py
│   │   ├── baseline_retriever.py
│   │   ├── baseline_selector.py
│   │   └── optimized_baseline_builder.py
│   │
│   ├── comment/                # Comment operations
│   │   ├── __init__.py
│   │   └── comment_service.py
│   │
│   ├── git/                    # Git operations
│   │   ├── __init__.py
│   │   ├── git_service.py
│   │   └── branch_service.py
│   │
│   ├── github/                 # GitHub-specific integration
│   │   ├── __init__.py
│   │   ├── github_integration_service.py
│   │   ├── github_issue_client.py
│   │   ├── github_change_detector.py
│   │   ├── github_config_validator.py
│   │   ├── github_conflict_detector.py
│   │   └── github_entity_classifier.py
│   │
│   ├── health/                 # Health checking services
│   │   ├── __init__.py
│   │   ├── health_check_service.py
│   │   ├── entity_health_scanner.py
│   │   ├── issue_health_scanner.py
│   │   ├── data_integrity_validator_service.py
│   │   └── infrastructure_validator_service.py
│   │
│   ├── helpers/                # (being flattened in Stage 1)
│   │   └── [FILES MOVED - see status_change_service.py]
│   │
│   ├── initialization/         # Initialization services
│   │   ├── __init__.py
│   │   ├── roadmap_initializer.py
│   │   ├── config_generator.py
│   │   └── template_generator.py
│   │
│   ├── issue/                  # Issue management services
│   │   ├── __init__.py
│   │   ├── issue_service.py
│   │   ├── issue_creation_service.py
│   │   ├── issue_update_service.py
│   │   ├── issue_matching_service.py
│   │   ├── start_issue_service.py
│   │   └── assignee_validation_service.py
│   │
│   ├── issue_helpers/          # (being flattened in Stage 1)
│   │   └── [FILES MOVED - see issue_filter_service.py]
│   │
│   ├── project/                # Project management
│   │   ├── __init__.py
│   │   ├── project_service.py
│   │   ├── project_status_service.py
│   │   └── project_init/       # Project initialization subsection
│   │       ├── __init__.py
│   │       └── project_initializer.py
│   │
│   ├── status_change_service.py  # Issue status transitions (moved from helpers/)
│   ├── issue_filter_service.py   # Issue filtering logic (moved from issue_helpers/)
│   │
│   ├── sync/                   # Sync-related services
│   │   ├── __init__.py
│   │   ├── sync_plan.py
│   │   ├── sync_plan_executor.py
│   │   ├── sync_report.py
│   │   ├── sync_state_manager.py
│   │   ├── sync_state_normalizer.py
│   │   ├── sync_state_comparator.py
│   │   ├── sync_change_computer.py
│   │   ├── sync_conflict_detector.py
│   │   ├── sync_conflict_resolver.py
│   │   ├── sync_metadata_service.py
│   │   └── sync_key_normalizer.py
│   │
│   ├── utils/                  # Utility functions (being reorganized)
│   │   ├── __init__.py
│   │   └── [BEING DISTRIBUTED]
│   │
│   └── validators/             # Validation services
│       ├── __init__.py
│       ├── validator_base.py   # Base validator class (renamed from base_validator.py)
│       ├── issue_validator.py
│       ├── milestone_validator.py
│       ├── dependency_validator.py
│       └── circular_dependency_validator.py
│
└── utils/                      # Core utility functions
    ├── __init__.py
    ├── date_utils.py
    ├── path_utils.py
    └── collection_utils.py
```

**Key Changes in Phase 5**:
- **Stage 1**: Moved `status_change_helpers.py` → `status_change_service.py`
- **Stage 1**: Moved `issue_filters.py` → `issue_filter_service.py`
- **Stage 2**: Reorganized `services/` from 52 flat files → 10+ subdirectories
- **Stage 4**: Renamed `base_validator.py` → `validator_base.py` (prefix pattern)

---

## Layer 3: Common (`/roadmap/common/`)

**Purpose**: Cross-cutting utilities and shared infrastructure.

```
common/
├── __init__.py                 # Main exports for backward compatibility
│
├── cache.py                    # Caching utilities
├── cli_errors.py              # CLI error definitions
├── console.py                 # Console output utilities
├── constants.py               # Global constants
├── datetime_parser.py         # Date/time parsing
├── error_formatter.py         # Error formatting
├── output_formatter.py        # Output formatting
├── progress.py                # Progress calculation
│
├── configuration/             # ⭐ Configuration layer (files: ~6)
│   ├── __init__.py
│   ├── config.py             # Configuration loading
│   ├── config_validator.py   # Config validation
│   └── config_models.py      # Config data models
│
├── errors/                   # ⭐ Error definitions (files: ~12)
│   ├── __init__.py
│   ├── base_exceptions.py
│   ├── validation_errors.py
│   ├── sync_errors.py
│   ├── github_errors.py
│   ├── persistence_errors.py
│   ├── initialization_errors.py
│   └── [etc]
│
├── formatting/               # ⭐ Formatting utilities (files: ~5)
│   ├── __init__.py
│   ├── ansi_utilities.py    # ANSI color/formatting (renamed from test_utils.py)
│   ├── assertion_helpers.py # Test assertions (renamed from test_helpers.py)
│   └── formatters.py        # General formatting
│
├── logging/                  # ⭐ Logging configuration (files: ~8)
│   ├── __init__.py
│   ├── logger.py
│   ├── log_config.py
│   └── [etc]
│
├── models/                   # ⭐ Shared data models (files: ~7)
│   ├── __init__.py
│   ├── sync_state.py
│   ├── health_report.py
│   └── [etc]
│
├── security/                 # ⭐ Security utilities (files: ~10)
│   ├── __init__.py
│   ├── encryption.py
│   ├── credentials.py
│   ├── token_manager.py
│   └── [etc]
│
└── services/                 # ⭐ Shared services (files: ~7)
    ├── __init__.py
    ├── file_service.py       # File operations (renamed from file_utils.py)
    ├── path_service.py       # Path operations (renamed from path_utils.py)
    ├── timezone_service.py   # Timezone handling (renamed from timezone_utils.py)
    └── [etc]
```

**Key Changes in Phase 5**:
- **Stage 3**: Reorganized `common/` from 28 flat files → 5 subdirectories
- **Stage 3**: Moved files to: `configuration/`, `errors/`, `formatting/`, `logging/`, `models/`, `security/`, `services/`
- **Stage 4**: Renamed utility files:
  - `file_utils.py` → `file_service.py`
  - `path_utils.py` → `path_service.py`
  - `timezone_utils.py` → `timezone_service.py`
- Created proper `__init__.py` with exports for backward compatibility

---

## Layer 4: Shared (`/roadmap/shared/`)

**Purpose**: Infrastructure layer for persistence, formatting, and external integrations.

```
shared/
├── __init__.py
│
├── persistence.py            # File persistence implementation
├── file_locking.py          # File locking mechanism
├── github_client.py         # GitHub API client
├── credentials.py           # Credential management
│
├── formatters/              # Output formatting layer (~30 formatters)
│   ├── __init__.py
│   │
│   ├── export/             # Export formatters
│   │   ├── __init__.py
│   │   ├── json_formatter.py
│   │   ├── csv_formatter.py
│   │   └── yaml_formatter.py
│   │
│   ├── kanban/             # Kanban board formatters
│   │   ├── __init__.py
│   │   └── kanban_formatter.py
│   │
│   ├── output/             # Output formatters
│   │   ├── __init__.py
│   │   ├── ansi_formatter.py
│   │   ├── markdown_formatter.py
│   │   └── text_formatter.py
│   │
│   ├── tables/             # Table formatters
│   │   ├── __init__.py
│   │   ├── table_formatter_base.py (was base_table_formatter.py)
│   │   ├── issue_table_formatter.py
│   │   ├── milestone_table_formatter.py
│   │   └── kanban_table_formatter.py
│   │
│   └── text/               # Text processing
│       ├── __init__.py
│       ├── text_wrapper.py
│       └── syntax_highlighter.py
│
├── git_hooks/              # Git hooks integration
│   ├── __init__.py
│   └── hook_manager.py
│
├── otel_init.py           # OpenTelemetry initialization
└── observability/         # Observability utilities
    ├── __init__.py
    ├── metrics.py
    └── tracing.py
```

---

## Import Patterns

### Public API Exports

Each layer has an `__init__.py` that exports its public API:

```python
# roadmap/core/services/__init__.py
from .issue import issue_service
from .sync import sync_plan
from .health import health_check_service

__all__ = ['issue_service', 'sync_plan', 'health_check_service']
```

### Backward Compatibility

Common reorganizations maintain compatibility:

```python
# roadmap/common/__init__.py
# Old imports still work
from .services.file_service import FileService  # not from file_utils
from .configuration.config import Config

__all__ = ['FileService', 'Config']
```

### Internal Imports

Within layers, use relative imports:

```python
# roadmap/core/services/issue/issue_service.py
from ..validators import validator_base
from ...common.models import IssueModel
from ...shared.persistence import save_to_disk
```

---

## Naming Conventions (Phase 5)

### Files & Directories

| Pattern | Use Case | Example |
|---------|----------|---------|
| `service_name.py` | Business logic services | `issue_service.py` |
| `name_validator.py` | Validators | `issue_validator.py` |
| `formatter.py` | Formatters | `json_formatter.py` |
| `name_service.py` | Utility services | `file_service.py` |
| `name_client.py` | External clients | `github_client.py` |
| `name_manager.py` | Complex coordination | `sync_state_manager.py` |
| `subdir/` | Feature/concern grouping | `issue/`, `sync/`, `github/` |

### Eliminated Patterns

❌ `*_utils.py` (now `*_service.py` or moved to subdir)
❌ `*_helpers.py` (now `*_service.py`)
❌ `base_*.py` (now `*_base.py` when needed)

---

## File Counts by Directory

| Directory | Files | Status |
|-----------|-------|--------|
| `adapters/cli` | 21 | ✅ Organized |
| `core/services` | 52+ | ✅ Reorganized into 10 subdirs |
| `common` | 28+ | ✅ Reorganized into 5 subdirs |
| `shared` | 30+ | ✅ Well organized |
| **Total** | **150+** | ✅ Phase 5 Complete |

---

## Architecture Principles

### 1. Layering

```
Adapters (CLI)
    ↓
Core (Business Logic)
    ↓
Common (Shared Utilities)
    ↓
Shared (Infrastructure)
```

No layer should depend on layers above it.

### 2. Dependency Injection

Services receive dependencies via constructor:

```python
class IssueService:
    def __init__(self, persistence, github_client):
        self.persistence = persistence
        self.github_client = github_client
```

### 3. Interface Segregation

Use abstract interfaces for contracts:

```python
class PersistenceInterface(ABC):
    @abstractmethod
    def save(self, data: Dict) -> None:
        pass
```

### 4. Single Responsibility

Each service handles one concern:
- `IssueService` → Issue CRUD operations
- `SyncPlanExecutor` → Executing sync plans
- `HealthCheckService` → System health checks

---

## Testing Organization

Tests mirror the source code structure in a layered approach:

```
tests/
├── unit/                           # Isolated component tests
│   ├── domain/                     # Domain layer tests (3 files)
│   │   ├── test_parser.py
│   │   ├── test_assignee_validation.py
│   │   └── test_estimated_time.py
│   │
│   ├── application/                # Application/Core service tests (9 files)
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
│   ├── infrastructure/             # Infrastructure/Shared layer tests (6 files)
│   │   ├── test_file_locking.py
│   │   ├── test_github_client.py
│   │   ├── test_git_hooks.py
│   │   ├── test_git_hooks_coverage.py
│   │   ├── test_enhanced_persistence.py
│   │   └── test_gitignore_management.py
│   │
│   ├── presentation/               # CLI adapter tests (10+ files)
│   │   ├── test_cli_smoke.py
│   │   ├── test_issue.py
│   │   ├── test_project.py
│   │   ├── test_deps_add_validation_handling.py
│   │   └── [other CLI command tests]
│   │
│   └── shared/                     # Shared utility tests (4 files)
│       ├── test_utils.py
│       ├── test_progress_calculation.py
│       ├── test_security.py
│       └── test_credentials.py
│
├── integration/                    # Integration tests (50+ files)
│   ├── test_integration.py
│   ├── test_git_integration.py
│   ├── test_cli_issue_commands.py
│   ├── test_cli_milestone_commands.py
│   ├── test_sync_backend_selection.py
│   ├── test_issue_lifecycle.py
│   ├── test_milestone_lifecycle.py
│   └── [other workflow tests]
│
├── security/                       # Security-specific tests
│   └── test_input_validation.py
│
├── fixtures/                       # Shared test fixtures
│   ├── conftest.py                # Pytest configuration & fixtures
│   └── [additional fixtures]
│
└── conftest.py                    # Root pytest configuration
```

### Test Layer Guidelines

**Domain Tests** (`tests/unit/domain/`)
- Pure business logic in isolation
- No external dependencies
- Focus on models, enums, calculations
- Mock external services

**Application Tests** (`tests/unit/application/`)
- Service and orchestration logic
- Use fixtures for domain objects
- Mock infrastructure layer
- Test use cases end-to-end

**Infrastructure Tests** (`tests/unit/infrastructure/`)
- Integration with external systems
- Storage and persistence operations
- File and git operations
- Mock actual API calls when appropriate

**Presentation Tests** (`tests/unit/presentation/`)
- CLI command tests
- Input validation
- Output formatting
- Click command runner tests

**Shared Tests** (`tests/unit/shared/`)
- Utility function tests
- Validators and formatters
- Logging and progress helpers
- No domain-specific logic

**Integration Tests** (`tests/integration/`)
- Workflows across layers
- CLI end-to-end scenarios
- Complete user workflows
- May hit actual external systems or mocks

### Test Statistics

- **Total Tests**: 6,558 (all passing with xdist parallelization)
- **Unit Tests**: 80+ test files
- **Integration Tests**: 50+ test files
- **Coverage**: 80%+ of codebase
- **Parallel Execution**: 8 workers with xdist
- **Recent Fix**: Fixed 3 flaky tests in test_deps_add_validation_handling.py for xdist compatibility

---

## Phase 5 Impact Summary

### Files Changed: 60+
- 8 files renamed (generic names → descriptive)
- 50+ files moved/reorganized
- 125+ imports updated
- 0 circular dependencies introduced

### Code Quality
- ✅ All pre-commit hooks passing
- ✅ 6,558 tests passing (xdist compatible)
- ✅ Type hints validated (Pyright)
- ✅ Code style enforced (ruff)
- ✅ Security checks (bandit)

### Developer Experience
- ✅ Clear file organization by concern
- ✅ Descriptive file/directory names
- ✅ Easy navigation (subdirs by feature)
- ✅ Backward compatible imports
- ✅ Maintainable dependency graph

---

## Sync Architecture

### Overview

The Roadmap sync system uses a **file-as-source-of-truth** approach leveraging git history and frontmatter metadata. This enables backend-agnostic sync while maintaining atomic, versioned state and three-way merge conflict detection.

```
┌─────────────────────────────────────────────────────────────┐
│                   User Workflow (CLI)                       │
│  roadmap sync → Fetch remote → Three-way merge → Commit     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            Generic Sync Orchestrator                        │
│  • Detects changes (git diff + git history)                │
│  • Performs three-way merge                                │
│  • Handles conflict resolution                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         Backend-Agnostic Sync Interface                     │
│  • GitHub API Backend                                       │
│  • Vanilla Git Backend                                      │
│  • Future: Jira, Linear, GitLab adapters                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          Local File-Based Storage                           │
│  • Issues: .roadmap/projects/{project}/issues/             │
│  • YAML Frontmatter: sync_metadata embedded                │
│  • Git History: Baseline reconstruction via git log        │
│  • Database: Cache layer only (rebuilt on startup)         │
└─────────────────────────────────────────────────────────────┘
```

### Core Principle

**Files are the source of truth.** Everything else (database, git history, sync metadata) is derived from or supporting.

### Sync Metadata Structure

Sync metadata is embedded in issue YAML frontmatter for:
- **Atomic storage** with issue data
- **Git history integration** (part of committed file)
- **Backend agnostic** (applies to any syncing system)
- **User transparency** (they see all state in git)

```yaml
---
id: "gh-123"
title: "Implement feature X"
status: "in-progress"
assignee: "jane"
priority: "high"
labels:
  - "feature"
  - "backend"

# Sync metadata - stored in YAML header for git tracking
sync_metadata:
  last_synced: "2026-01-03T10:30:45Z"
  last_updated: "2026-01-03T10:25:00Z"
  remote_state:
    status: "open"
    assignee: "bob"
    priority: "medium"
    labels: ["feature"]
---

Full markdown content here...
```

### Sync Data Flow

#### Normal Operation

```
User: roadmap list
    ↓
IssueService.list_issues()
    ↓
Check if DB is in sync with git
    ├─ git diff --name-only (cheap, milliseconds)
    ├─ If no changes: return cached from DB (fast)
    └─ If changes detected:
        ├─ For each changed file: load from disk
        ├─ Update database
        └─ Return from database
```

#### On Sync Operation

```
User: roadmap sync
    ↓
SyncOrchestrator starts
    ├─ Get baseline: from database sync_base_state (fast)
    ├─ Get local issues: from database (cached, fast)
    ├─ Get remote issues: from API (expected cost)
    ├─ Three-way merge
    └─ Apply changes:
        ├─ Write to files: .roadmap/issues/{id}.md
        └─ Update database (in transaction)
```

### Git Sync Monitor

The Git Sync Monitor (`roadmap/core/services/sync/`) detects changes between git and database:

```python
class GitSyncMonitor:
    """Detects changes between git and database."""

    def detect_changes(self) -> dict[str, str]:
        """Detect which .roadmap/issues files changed since last sync.

        Returns:
            {
                'modified': ['issue1.md', 'issue2.md'],
                'added': ['issue3.md'],
                'deleted': ['issue4.md']
            }
        """
        # Fast: just get list of changed files via git diff
        # Don't scan filesystem
```

### Baseline State Management

Baseline state is reconstructed from git history via:

1. **Git log queries** to find relevant commit history
2. **Frontmatter parsing** from historical versions
3. **Reconstruction** of state at specific points in time
4. **Three-way merge** using: local version, remote version, baseline

This approach enables:
- ✅ Complete reproducibility (anyone can clone and reconstruct)
- ✅ No external database dependencies for baseline
- ✅ Atomic sync operations (git commits as transactions)
- ✅ Backend agnostic (works with any issue tracking system)

### Sync Services

| Service | Location | Purpose |
|---------|----------|---------|
| `SyncOrchestrator` | `core/services/sync/` | Coordinates sync workflow |
| `SyncStatePlan` | `core/services/sync/` | Plans sync operations |
| `SyncStateManager` | `core/services/sync/` | Manages local sync state |
| `SyncChangeComputer` | `core/services/sync/` | Computes changes needed |
| `SyncConflictDetector` | `core/services/sync/` | Detects merge conflicts |
| `SyncConflictResolver` | `core/services/sync/` | Resolves conflicts |
| `GitSyncMonitor` | `core/services/sync/` | Monitors git changes |
| `GitKeyNormalizer` | `core/services/sync/` | Normalizes git keys |

---

## Related Documents

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Data models & file formats (Roadmap data structure)
- [SYNC_ARCHITECTURE.md](./SYNC_ARCHITECTURE.md) - Detailed sync implementation guide (reference)
- [GIT_SYNC_ARCHITECTURE.md](./GIT_SYNC_ARCHITECTURE.md) - Git diff-based optimization details (reference)
- [NAMING_CONVENTIONS.md](../NAMING_CONVENTIONS.md) - Code style guide
- [SECURITY.md](./SECURITY.md) - Security architecture and best practices
