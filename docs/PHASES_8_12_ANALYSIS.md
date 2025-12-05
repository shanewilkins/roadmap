## Phases 8-12: CLI/Core and Health Refactoring Analysis

**Date:** December 5, 2025
**Status:** PENDING (Ready for Implementation)
**Priority:** HIGH (Phases 8-10), MEDIUM (Phases 11-12)

---

## Overview

This document analyzes the remaining god objects in the codebase for service extraction:
- **Phases 8-10:** `cli/core.py` (1,133 LOC) → ProjectInitializationService + ProjectStatusService
- **Phases 11-12:** `health.py` (900 LOC) → 4 Health Validators

Both are HIGH/MEDIUM priority and critical for reducing architectural complexity.

---

## Phase 8-10: CLI Core Refactoring

### Current State: `roadmap/cli/core.py` (1,133 LOC)

**Problem:**
Large monolithic file containing mixed responsibilities:
- Project initialization workflow (~300 LOC)
- Status command execution (~100 LOC)
- Health command execution (~70 LOC)
- GitHub setup workflow (~150 LOC)
- Project template generation (~180 LOC)
- Post-init validation (~60 LOC)
- Multiple helper functions scattered throughout

**Responsibility Matrix:**

```
Initialization Logic (Phase 8):
├── Project detection and context setup
├── GitHub configuration
├── Project template generation
├── Validation and success summary
└── ~500+ LOC total

Status Logic (Phase 9):
├── Project context detection
├── Status aggregation
├── Status output formatting
└── ~150 LOC total

Setup/Helpers (Phase 10):
├── Main project setup
├── GitHub integration setup
├── Post-init validation
└── ~80 LOC total
```

### Proposed Extraction Strategy

**Phase 8: ProjectInitializationService** (7-8 hours)
- Extract from `init` command and related helpers
- Extract from: `_detect_existing_projects`, `_create_main_project`, `_setup_main_project`, `_setup_github_integration`, `_post_init_validate`
- New File: `roadmap/cli/services/project_initialization_service.py`
- Key Methods:
  - `detect_existing_projects(projects_dir) → list[dict]`
  - `validate_initialization_context(config, interactive) → bool`
  - `create_main_project(name, description, template) → None`
  - `setup_github_integration(token, repo) → bool`
  - `generate_project_template(template_name, custom_path) → str`
  - `run_initialization_workflow(options) → bool`
  - `validate_post_init() → dict[str, bool]`

**Phase 9: ProjectStatusService** (4-5 hours)
- Extract from `status` command implementation
- Extract from: `_detect_project_context`, status display logic
- New File: `roadmap/cli/services/project_status_service.py`
- Key Methods:
  - `detect_project_context() → dict[str, Any]`
  - `gather_status_data() → dict[str, Any]`
  - `get_project_health_summary(health_checks) → dict`
  - `format_status_report() → str`

**Phase 10: CLI Helpers** (1-2 hours)
- Thin wrapper for `init` and `status` commands
- Refactor: Call new services instead of nested functions
- Remove: 500+ LOC of business logic
- Keep: Click decorators, CLI options, orchestration

### Expected Results
- **cli/core.py:** 1,133 LOC → ~150 LOC (87% reduction)
- **New Services:** ~400 LOC total (reusable, testable)
- **Coverage:** Add ~50-60 new unit tests
- **Time Estimate:** 12-15 hours total

---

## Phase 11-12: Health Check Refactoring

### Current State: `roadmap/application/health.py` (900 LOC)

**Problem:**
Single HealthCheck class contains 13 methods, each doing distinct validation:

```python
class HealthCheck:
    # File System Validators (100 LOC)
    ├── check_roadmap_directory()
    ├── check_state_file()
    ├── check_issues_directory()
    └── check_milestones_directory()

    # Repository Validators (50 LOC)
    ├── check_git_repository()
    └── check_database_integrity()

    # Data Integrity Validators (100 LOC)
    ├── check_duplicate_issues()
    ├── check_folder_structure()
    ├── check_data_integrity()
    └── check_orphaned_issues()

    # Informational Validators (80 LOC)
    ├── check_old_backups()
    ├── check_archivable_issues()
    └── check_archivable_milestones()

    # Orchestration (50 LOC)
    ├── run_all_checks()
    └── get_overall_status()
```

**Issue:** Each validator is independent but lumped together. They should be testable separately.

### Proposed Extraction Strategy

**Phase 11: Critical Validators Service** (3-4 hours)
- Extract file system and repository checks
- New File: `roadmap/application/health/validators/infrastructure_validator.py`
- Validators:
  - `RoadmapDirectoryValidator` - check_roadmap_directory
  - `StateFileValidator` - check_state_file
  - `IssuesDirectoryValidator` - check_issues_directory
  - `MilestonesDirectoryValidator` - check_milestones_directory
  - `GitRepositoryValidator` - check_git_repository
  - `DatabaseIntegrityValidator` - check_database_integrity

**Phase 12: Data Integrity Validators** (2-3 hours)
- Extract data quality and informational checks
- New File: `roadmap/application/health/validators/data_integrity_validator.py`
- Validators:
  - `DataIntegrityValidator` - check_data_integrity
  - `DuplicateIssuesValidator` - check_duplicate_issues
  - `FolderStructureValidator` - check_folder_structure
  - `OrphanedIssuesValidator` - check_orphaned_issues
  - `ArchivedIssuesValidator` - check_archivable_issues
  - `ArchivedMilestonesValidator` - check_archivable_milestones
  - `BackupValidator` - check_old_backups

**HealthCheck Refactoring (Thin Orchestrator)**
- Keep: `run_all_checks()` and `get_overall_status()`
- Remove: All 13 individual check methods
- New: Instantiate validators and call them
- Result: ~50 LOC (from 900)

### Expected Results
- **health.py:** 900 LOC → ~100 LOC (89% reduction)
- **New Validators:** ~600 LOC total (each testable independently)
- **Coverage:** Add ~40-50 unit tests
- **Time Estimate:** 6-7 hours total

---

## Implementation Order & Dependencies

```
Phase 8: ProjectInitializationService
  ├─ Extract initialization logic
  ├─ Create service with 7 public methods
  └─ Estimated: 7-8 hours

Phase 9: ProjectStatusService
  ├─ Depends on: Phase 8 (shares same file structure)
  ├─ Extract status logic
  ├─ Create service with 4 public methods
  └─ Estimated: 4-5 hours

Phase 10: CLI Refactoring
  ├─ Depends on: Phases 8-9 (must have services ready)
  ├─ Refactor init/status commands
  ├─ Call new services
  └─ Estimated: 1-2 hours

Phase 11: Infrastructure Validators
  ├─ No dependencies (can start anytime)
  ├─ Extract 6 validators
  ├─ Create validator service
  └─ Estimated: 3-4 hours

Phase 12: Data Integrity Validators
  ├─ Depends on: Phase 11 (validator pattern established)
  ├─ Extract 7 validators
  ├─ Refactor HealthCheck
  └─ Estimated: 2-3 hours
```

---

## Code Examples

### Phase 8: ProjectInitializationService Structure

```python
class ProjectInitializationService:
    """Service for project initialization workflow.

    Handles:
    - Project context detection
    - GitHub integration setup
    - Template generation
    - Post-init validation
    """

    def __init__(self, config_manager, github_manager):
        self.config = config_manager
        self.github = github_manager

    def detect_existing_projects(self, projects_dir: Path) -> list[dict]:
        """Scan for existing project structures."""
        # Logic from _detect_existing_projects (30 LOC)
        pass

    def create_main_project(
        self,
        name: str,
        description: str,
        template: str
    ) -> bool:
        """Create main project structure."""
        # Logic from _create_main_project (35 LOC)
        pass

    def setup_github_integration(
        self,
        token: str,
        repo: str
    ) -> bool:
        """Configure GitHub integration."""
        # Logic from _setup_github_integration (80 LOC)
        pass

    def generate_project_template(
        self,
        template_name: str,
        custom_path: Path = None
    ) -> str:
        """Generate project template content."""
        # Logic from _generate_project_template (150 LOC)
        pass

    def run_initialization_workflow(
        self,
        options: dict
    ) -> bool:
        """Execute complete initialization."""
        # Orchestrate all steps
        pass
```

### Phase 11: Infrastructure Validator Pattern

```python
from abc import ABC, abstractmethod
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthValidator(ABC):
    """Base class for all health validators."""

    @abstractmethod
    def validate(self) -> tuple[HealthStatus, str]:
        """Run validation and return (status, message)."""
        pass

class RoadmapDirectoryValidator(HealthValidator):
    """Validate .roadmap directory."""

    def validate(self) -> tuple[HealthStatus, str]:
        # Logic from check_roadmap_directory (25 LOC)
        pass

class StateFileValidator(HealthValidator):
    """Validate state database file."""

    def validate(self) -> tuple[HealthStatus, str]:
        # Logic from check_state_file (30 LOC)
        pass

# ... 4 more validators ...

class InfrastructureValidator:
    """Orchestrator for all infrastructure validators."""

    def __init__(self):
        self.validators = {
            'roadmap_directory': RoadmapDirectoryValidator(),
            'state_file': StateFileValidator(),
            # ... etc
        }

    def validate_all(self) -> dict[str, tuple[HealthStatus, str]]:
        """Run all validators and return results."""
        return {
            name: validator.validate()
            for name, validator in self.validators.items()
        }
```

---

## Testing Strategy

### Unit Tests (Phases 8-10)
```
tests/unit/cli/services/test_project_initialization_service.py
├── TestProjectDetection (5 tests)
├── TestProjectCreation (4 tests)
├── TestGitHubSetup (3 tests)
├── TestTemplateGeneration (4 tests)
└── TestWorkflowOrchestration (3 tests)
└── Total: ~20 tests

tests/unit/cli/services/test_project_status_service.py
├── TestContextDetection (3 tests)
├── TestStatusGathering (3 tests)
├── TestHealthSummary (2 tests)
└── Total: ~8 tests
```

### Unit Tests (Phases 11-12)
```
tests/unit/application/health/validators/test_infrastructure_validators.py
├── TestRoadmapDirectoryValidator (4 tests)
├── TestStateFileValidator (4 tests)
├── TestRepositoryValidator (3 tests)
├── TestDatabaseValidator (4 tests)
└── Total: ~15 tests

tests/unit/application/health/validators/test_data_integrity_validators.py
├── TestDataIntegrityValidator (4 tests)
├── TestDuplicateIssuesValidator (3 tests)
├── TestFolderStructureValidator (4 tests)
├── TestOrphanedIssuesValidator (3 tests)
├── TestArchiveValidators (4 tests)
└── Total: ~18 tests
```

---

## Risk Assessment

### Phase 8-10 Risks
- **HIGH:** init command is complex with many edge cases
- **MEDIUM:** GitHub integration has external dependencies
- **MITIGATION:** Keep existing integration tests, add mocks for GitHub API

### Phase 11-12 Risks
- **LOW:** Validators are relatively independent
- **MEDIUM:** Health checks depend on file system state
- **MITIGATION:** Use temporary directories in tests

---

## Success Criteria

### Phases 8-10
- ✅ `cli/core.py` reduced from 1,133 → ~150 LOC (87%)
- ✅ All existing tests pass (1,642+)
- ✅ New services have 85%+ coverage
- ✅ Init and status commands work identically to before

### Phases 11-12
- ✅ `health.py` reduced from 900 → ~100 LOC (89%)
- ✅ All validators independently testable
- ✅ Health checks work identically to before
- ✅ New validators have 80%+ coverage

---

## Timeline

| Phase | Work | Est. Time | Cumulative |
|-------|------|-----------|-----------|
| 8 | ProjectInitializationService | 7-8h | 7-8h |
| 9 | ProjectStatusService | 4-5h | 11-13h |
| 10 | CLI Refactoring | 1-2h | 12-15h |
| 11 | Infrastructure Validators | 3-4h | 15-19h |
| 12 | Data Integrity Validators | 2-3h | 17-22h |

**Total Estimated Time:** 17-22 hours
**Recommended Sprint:** 2-3 work days

---

## Next Steps

1. **Review this analysis** - Validate extraction strategy
2. **Approve scope** - Confirm Phase 8 dependencies and structure
3. **Begin Phase 8** - ProjectInitializationService extraction
4. **Parallel Phase 11** - Infrastructure validators (no dependencies)
5. **Complete 8-10, then 11-12** - Follow dependency chain

---

## Key Metrics

### Pre-Refactoring
- cli/core.py: 1,133 LOC (god object)
- health.py: 900 LOC (god object)
- Total: 2,033 LOC in god objects
- Tests: 1,642 passing

### Post-Refactoring (Target)
- cli/core.py: ~150 LOC (thin wrapper)
- health.py: ~100 LOC (thin orchestrator)
- Extracted services: ~1,000 LOC (reusable)
- Total: ~1,250 LOC (38% overall reduction)
- Tests: 1,742+ passing (+100 new tests)
- Coverage: Maintain 85%+

---

**Document Generated:** December 5, 2025
**Status:** Ready for Implementation
**Next Phase:** Phase 8 - ProjectInitializationService Extraction
