# God Object Refactoring Plan

**Priority Sequence:** Start with #1, then #2, then #3

---

## Priority 1: `infrastructure/storage.py` Refactor 🔴 HIGHEST

### Current Problem
- **File Size:** 1,510 LOC (god object)
- **Maintainability Index:** 0.19 (lowest in codebase)
- **Coverage:** 16% (437 LOC untested)
- **Responsibilities:** 48 public methods doing 5+ different things

### Current Responsibilities

The `StateManager` class has become a dumping ground for:

1. **Database Management** (lines ~84-265)
   - `_init_database()` - Schema initialization
   - `_run_migrations()` - Version management
   - `_get_connection()` - Connection pooling
   - `transaction()` - Transaction management
   - `vacuum()` - Database maintenance

2. **CRUD Operations** (lines ~278-538)
   - Project: `create_project()`, `get_project()`, `list_projects()`, `update_project()`, `delete_project()`
   - Milestone: `create_milestone()`, `get_milestone()`, `update_milestone()`
   - Issue: `create_issue()`, `get_issue()`, `update_issue()`, `delete_issue()`
   - Archival: `mark_project_archived()`, `mark_milestone_archived()`, `mark_issue_archived()`

3. **File Synchronization** (lines ~584-1000, **MOST COMPLEX**)
   - `sync_issue_file()` - C complexity, parses YAML, detects changes
   - `sync_milestone_file()` - C complexity, handles dependencies
   - `sync_project_file()` - Complex project sync logic
   - `sync_directory_incremental()` - C complexity, incremental updates
   - `full_rebuild_from_git()` - C complexity, full reconstruction
   - `smart_sync()` - Orchestrates sync strategy
   - Helper methods: `_calculate_file_hash()`, `_parse_yaml_frontmatter()`, `_common_sync_entity()`

4. **Sync State Tracking** (lines ~552-643)
   - `get_sync_state()`, `set_sync_state()` - Persistence of sync metadata
   - `get_file_sync_status()` - Track which files are synced
   - `update_file_sync_status()` - Update sync records
   - `has_file_changed()` - Detect file changes
   - `_calculate_file_hash()` - File hashing

5. **Conflict Resolution** (lines ~1196-1282)
   - `check_git_conflicts()` - Detect git conflicts
   - `has_git_conflicts()` - Check if conflicts exist
   - `get_conflict_files()` - List conflicting files

6. **Query Operations** (lines ~1324-1451)
   - `get_all_issues()`, `get_all_milestones()` - Bulk queries
   - `get_milestone_progress()` - Aggregation
   - `get_issues_by_status()` - Aggregation
   - `is_safe_for_writes()` - State checking

### Proposed Refactoring: Split into 3 Classes

#### New File 1: `infrastructure/persistence/database_manager.py`
**Responsibility:** Database infrastructure and transactions

```
DatabaseManager (new class)
├── __init__(db_path)
├── _get_connection()           [moved from StateManager]
├── transaction()               [moved from StateManager]
├── _init_database()            [moved from StateManager]
├── _run_migrations()           [moved from StateManager]
├── vacuum()                    [moved from StateManager]
├── close()                     [moved from StateManager]
├── is_initialized()            [moved from StateManager]
└── is_safe_for_writes()        [moved from StateManager]
```

**Usage Pattern:**
```python
# Before
state_mgr = StateManager()
state_mgr.create_issue(...)
state_mgr.transaction()

# After
db_mgr = DatabaseManager()
with db_mgr.transaction() as conn:
    # ... operations
```

---

#### New File 2: `infrastructure/persistence/file_synchronizer.py`
**Responsibility:** File-to-database synchronization logic (MOST CRITICAL)

```
FileSynchronizer (new class)
├── __init__(db_manager, parser)
├── sync_issue_file(file_path)           [moved from StateManager]
├── sync_milestone_file(file_path)       [moved from StateManager]
├── sync_project_file(file_path)         [moved from StateManager]
├── sync_directory_incremental(roadmap_dir)  [moved from StateManager]
├── full_rebuild_from_git(roadmap_dir)   [moved from StateManager]
├── smart_sync(roadmap_dir)              [moved from StateManager]
├── _calculate_file_hash(file_path)      [moved from StateManager]
├── _parse_yaml_frontmatter(file_path)   [moved from StateManager]
├── _common_sync_entity(...)             [moved from StateManager]
├── _get_default_project_id()            [moved from StateManager]
└── _get_milestone_id_by_name(name)      [moved from StateManager]

SyncStateTracker (new class)
├── __init__(db_manager)
├── get_sync_state(key)                  [moved from StateManager]
├── set_sync_state(key, value)           [moved from StateManager]
├── get_file_sync_status(file_path)      [moved from StateManager]
├── update_file_sync_status(...)         [moved from StateManager]
└── has_file_changed(file_path)          [moved from StateManager]
```

**Why separate:** Sync logic has 5 different concerns:
1. File change detection (hashing)
2. YAML parsing
3. Database updates
4. Sync state persistence
5. Rebuild orchestration

This makes it hard to test and debug. FileSynchronizer focuses on the orchestration, SyncStateTracker on metadata.

---

#### New File 3: `infrastructure/conflict_resolver.py`
**Responsibility:** Git conflict detection and resolution

```
ConflictResolver (new class)
├── __init__(db_manager, git_integration)
├── check_git_conflicts(roadmap_dir)     [moved from StateManager]
├── has_git_conflicts()                  [moved from StateManager]
└── get_conflict_files()                 [moved from StateManager]
```

---

#### Refactored `StateManager` (MUCH SMALLER)

**New file: `infrastructure/persistence/state_manager.py`**

```python
class StateManager:
    """Orchestrator for persistence operations.

    Now delegates to specialized managers instead of doing everything itself.
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_manager = DatabaseManager(db_path)
        self.file_sync = FileSynchronizer(self.db_manager, parser)
        self.sync_state = SyncStateTracker(self.db_manager)
        self.conflict_resolver = ConflictResolver(self.db_manager, git_integration)

    # CRUD Operations - delegates to db_manager
    def create_project(self, project_data):
        return self._execute_with_db(lambda: self.db_manager.create_project(project_data))

    def get_issue(self, issue_id):
        return self.db_manager.get_issue(issue_id)

    # File Sync - delegates to file_sync
    def sync_issue_file(self, file_path):
        return self.file_sync.sync_issue_file(file_path)

    def smart_sync(self, roadmap_dir):
        return self.file_sync.smart_sync(roadmap_dir)

    # Query operations - delegates to db_manager
    def get_all_issues(self):
        return self.db_manager.get_all_issues()

    @contextmanager
    def transaction(self):
        with self.db_manager.transaction() as conn:
            yield conn

    def close(self):
        self.db_manager.close()
```

**Benefits:**
- StateManager becomes a thin facade
- Easy to test each component independently
- Clear separation of concerns
- Can mock each synchronizer independently

---

### Refactoring Dependencies

**What needs updating:**

1. Import statements in:
   - `roadmap/application/core.py` - Still imports StateManager (no change needed)
   - `roadmap/application/services/*.py` - Still use StateManager interface (no change needed)
   - `roadmap/cli/core.py` - No direct storage imports (no change)

2. New imports to add (internal only):
   - `FileSynchronizer` from `infrastructure.persistence.file_synchronizer`
   - `DatabaseManager` from `infrastructure.persistence.database_manager`
   - `ConflictResolver` from `infrastructure.conflict_resolver`

**Breaking Changes:** NONE - StateManager interface stays the same!

---

### Implementation Order (storage.py)

**Phase 1: Extract DatabaseManager** (2-3 hours)
1. Create `infrastructure/persistence/database_manager.py`
2. Move DB-related methods from StateManager
3. Create tests for DatabaseManager
4. Update StateManager to delegate to DatabaseManager

**Phase 2: Extract FileSynchronizer** (4-5 hours, MOST COMPLEX)
1. Create `infrastructure/persistence/file_synchronizer.py`
2. Move all sync methods (11 methods, ~400 LOC)
3. Create SyncStateTracker class
4. Add comprehensive tests (currently 0% coverage)
5. Update StateManager to delegate

**Phase 3: Extract ConflictResolver** (1-2 hours)
1. Create `infrastructure/conflict_resolver.py`
2. Move conflict methods (3 methods, ~80 LOC)
3. Add tests
4. Update StateManager to delegate

**Phase 4: Refactor StateManager** (1 hour)
- Clean up to become orchestrator facade
- Verify all tests pass
- Run coverage analysis (target 50% → 80%)

**Total Effort:** 8-11 hours

---

## Priority 2: `cli/core.py` Refactor 🟠 HIGH

### Current Problem
- **File Size:** 1,134 LOC
- **Maintainability Index:** 18.08 (very low)
- **Coverage:** 54% (189 LOC untested)
- **Functions:** 4 D/C-rated functions doing initialization

### Current Responsibilities

```
init()                          # D complexity - Main initialization command (109-271 LOC)
├── _detect_existing_projects()    # D complexity - Find projects
├── _detect_project_context()      # D complexity - Multiple detection paths
├── _show_detected_context()       # Display results
├── _create_main_project()         # C complexity - Create project
├── _configure_github()            # Setup GitHub
└── _setup_github_integration()    # C complexity - Full GitHub setup

status()                        # C complexity - Show project status
├── Check project existence
├── Load configuration
├── Display various status items

health()                        # B complexity - Run health checks
└── Calls HealthCheck.run_all_checks()
```

### Proposed Refactoring: Split into 2 Service Classes

#### New File 1: `roadmap/application/services/initialization_service.py`
**Responsibility:** Project initialization workflow

```python
class ProjectInitializationService:
    """Handles the complete project initialization workflow."""

    def __init__(self, core: RoadmapCore):
        self.core = core

    def run_interactive_setup(self,
        name: str = ".roadmap",
        project_name: str | None = None,
        skip_github: bool = False,
        skip_project: bool = False
    ) -> InitializationResult:
        """Main entry point for init command."""

    def detect_existing_projects(self, projects_dir: Path) -> list[dict]:
        """Find existing projects."""

    def detect_project_context(self) -> dict:
        """Auto-detect project information from git/package files."""

    def create_main_project(self, project_data: dict) -> str:
        """Create the main project."""

    def setup_github_integration(self, config: dict) -> bool:
        """Configure GitHub integration."""
```

**Usage:**
```python
# In cli/core.py init command
service = ProjectInitializationService(core)
result = service.run_interactive_setup(
    name=name,
    project_name=project_name,
    skip_github=skip_github
)
if result.success:
    display_success(result)
```

#### New File 2: `roadmap/application/services/status_service.py`
**Responsibility:** Project status reporting

```python
class ProjectStatusService:
    """Handles status reporting and health checks."""

    def __init__(self, core: RoadmapCore):
        self.core = core

    def get_project_status(self, verbose: bool = False) -> ProjectStatus:
        """Get comprehensive project status."""

    def run_health_checks(self, verbose: bool = False) -> HealthCheckResults:
        """Run all health checks and return results."""

    def format_status_report(self, status: ProjectStatus) -> str:
        """Format status for display."""
```

**Usage:**
```python
# In cli/core.py status command
service = ProjectStatusService(core)
status = service.get_project_status(verbose=verbose)
console.print(service.format_status_report(status))

# In cli/core.py health command
results = service.run_health_checks(verbose=verbose)
display_health_results(results)
```

### What Stays in `cli/core.py`

Only the Click command definitions and display logic:

```python
@click.command()
@click.option(...)
def init(...):
    """Click command wrapper."""
    service = ProjectInitializationService(core)
    result = service.run_interactive_setup(...)
    display_initialization_result(result)

@click.command()
def status(ctx, verbose):
    """Click command wrapper."""
    service = ProjectStatusService(core)
    status = service.get_project_status(verbose=verbose)
    display_status(status)

@click.command()
def health(ctx, verbose):
    """Click command wrapper."""
    service = ProjectStatusService(core)
    results = service.run_health_checks(verbose=verbose)
    display_health_results(results)
```

---

### Implementation Order (cli/core.py)

**Phase 1: Extract ProjectInitializationService** (3-4 hours)
1. Move `init()` logic to `initialization_service.py`
2. Move helper functions: `_detect_existing_projects()`, `_detect_project_context()`, etc.
3. Create tests
4. Update `cli/core.py` to use service

**Phase 2: Extract ProjectStatusService** (2-3 hours)
1. Move `status()` and `health()` logic
2. Create tests
3. Update `cli/core.py` to use service

**Phase 3: Simplify cli/core.py** (1 hour)
- Keep only Click commands and basic display logic
- Verify coverage improves (54% → 80%+)

**Total Effort:** 6-8 hours

---

## Priority 3: `application/health.py` Refactor 🟡 MEDIUM

### Current Problem
- **File Size:** 901 LOC
- **Maintainability Index:** 16.82
- **Coverage:** 76% (27 LOC untested)
- **Functions:** 8 scan functions + HealthCheck class with 13 check methods

### Current Structure

```
Standalone functions (16 functions):
├── extract_issue_id()
├── scan_for_duplicate_issues()
├── scan_for_folder_structure_issues()         # D complexity
├── scan_for_old_backups()                     # B complexity
├── scan_for_archivable_issues()               # C complexity
├── scan_for_archivable_milestones()           # B complexity
├── scan_for_data_integrity_issues()           # A complexity
├── scan_for_orphaned_issues()                 # A complexity
├── scan_for_malformed_files()                 # A complexity
└── [various helpers]

HealthCheck class (13 methods):
├── check_roadmap_directory()
├── check_state_file()
├── check_issues_directory()
├── check_milestones_directory()
├── check_git_repository()
├── check_duplicate_issues()
├── check_folder_structure()
├── check_old_backups()
├── check_archivable_issues()
├── check_archivable_milestones()
├── check_database_integrity()
├── check_data_integrity()
├── check_orphaned_issues()
└── run_all_checks()
```

### Proposed Refactoring: Split into 4 Validator Classes

Instead of one monolithic HealthCheck class, create focused validators:

#### New File 1: `roadmap/application/validators/structure_validator.py`
```python
class StructureValidator:
    """Validates directory and file structure integrity."""

    def __init__(self, core: RoadmapCore):
        self.core = core

    def check_roadmap_directory(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def check_issues_directory(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def check_milestones_directory(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def check_folder_structure(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def scan_for_folder_structure_issues(self) -> dict[str, list[dict]]:
        # Moved from health.py
```

#### New File 2: `roadmap/application/validators/duplicate_detector.py`
```python
class DuplicateDetector:
    """Detects duplicate issues and files."""

    def __init__(self, core: RoadmapCore):
        self.core = core

    def check_duplicate_issues(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def scan_for_duplicate_issues(self) -> dict[str, list[Path]]:
        # Moved from health.py

    def scan_for_malformed_files(self) -> dict[str, list[str]]:
        # Moved from health.py
```

#### New File 3: `roadmap/application/validators/archive_scanner.py`
```python
class ArchiveScanner:
    """Identifies issues and milestones ready for archival."""

    def __init__(self, core: RoadmapCore):
        self.core = core

    def check_archivable_issues(self, threshold_days: int = 30) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def check_archivable_milestones(self, threshold_days: int = 14) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def scan_for_archivable_issues(self) -> list[dict]:
        # Moved from health.py

    def scan_for_archivable_milestones(self) -> list[dict]:
        # Moved from health.py
```

#### New File 4: `roadmap/application/validators/data_integrity_checker.py`
```python
class DataIntegrityChecker:
    """Checks data consistency and integrity."""

    def __init__(self, core: RoadmapCore):
        self.core = core

    def check_state_file(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def check_git_repository(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def check_database_integrity(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def check_data_integrity(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def check_orphaned_issues(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def check_old_backups(self) -> tuple[HealthStatus, str]:
        # Moved from HealthCheck

    def scan_for_data_integrity_issues(self) -> list[dict]:
        # Moved from health.py

    def scan_for_orphaned_issues(self) -> list[dict]:
        # Moved from health.py
```

#### Refactored `HealthCheck` class
```python
class HealthCheck:
    """Orchestrator that delegates to specialized validators."""

    def __init__(self, core: RoadmapCore):
        self.core = core
        self.structure_validator = StructureValidator(core)
        self.duplicate_detector = DuplicateDetector(core)
        self.archive_scanner = ArchiveScanner(core)
        self.data_integrity = DataIntegrityChecker(core)

    def run_all_checks(self, verbose: bool = False) -> HealthCheckResults:
        """Run all checks using validators."""
        results = HealthCheckResults()
        results.structure = self.structure_validator.run_all()
        results.duplicates = self.duplicate_detector.run_all()
        results.archives = self.archive_scanner.run_all()
        results.integrity = self.data_integrity.run_all()
        return results
```

---

### Implementation Order (health.py)

**Phase 1: Create validator directory structure** (30 min)
```
roadmap/application/validators/
├── __init__.py
├── structure_validator.py
├── duplicate_detector.py
├── archive_scanner.py
└── data_integrity_checker.py
```

**Phase 2: Extract each validator** (5-6 hours total)
- 1.5 hours per validator
- Move methods and their dependencies
- Add tests for each

**Phase 3: Refactor HealthCheck** (1-2 hours)
- Update to delegate to validators
- Update imports in `presentation/cli/cleanup.py`
- Verify coverage improves (76% → 90%+)

**Total Effort:** 7-9 hours

---

## Implementation Roadmap Summary

| Priority | Module | New Architecture | Est. Time | Coverage Gain |
|----------|--------|------------------|-----------|---------------|
| **1** | `storage.py` | DatabaseManager + FileSynchronizer + ConflictResolver | 8-11h | 16% → 80% |
| **2** | `cli/core.py` | ProjectInitializationService + ProjectStatusService | 6-8h | 54% → 85% |
| **3** | `health.py` | 4 focused validators + orchestrator | 7-9h | 76% → 90%+ |

---

## Expected Benefits

### After All Refactorings

| Metric | Before | After | Gain |
|--------|--------|-------|------|
| Average Module LOC | 700+ | 200-400 | 🎯 3-4x smaller |
| Avg Maintainability (MI) | 17.7 | 60+ | 🎯 3.5x better |
| Test Coverage | 55% | 80%+ | 🎯 +25% |
| Functions with C+ CC | 22 | 8 | 🎯 -64% |
| Module Dependencies | High | Low | 🎯 Better isolation |

### Testability Improvements

**Before refactoring:**
- Hard to test storage.py sync logic (300+ LOC, many paths)
- Hard to test init.py (1,100+ LOC, many branches)
- Hard to test health.py (multiple concerns mixed)

**After refactoring:**
- Each module <300 LOC with single responsibility
- Can test FileSynchronizer independently of DatabaseManager
- Can mock validators independently
- Each class has clear, testable interface

---

## Risk Assessment

### Breaking Changes
✅ **NONE** - All changes are internal refactoring
- Public APIs stay the same
- StateManager interface unchanged
- HealthCheck interface unchanged
- CLI commands unchanged

### Testing Strategy
1. Run full test suite before each phase
2. Add tests incrementally for new classes
3. Verify coverage doesn't drop
4. Keep old code until new code proven

---

## Next Steps

1. **Start with Phase 1 of storage.py** (DatabaseManager extraction)
   - Lowest risk
   - Establishes pattern
   - Can be done incrementally

2. **Then tackle storage.py Phase 2** (FileSynchronizer)
   - Most complex but highest payoff
   - Where the real testing gap is

3. **Then cli/core.py** (services extraction)
   - High payoff for init/status command coverage

4. **Finally health.py** (validator split)
   - Lowest urgency, mostly complete anyway
