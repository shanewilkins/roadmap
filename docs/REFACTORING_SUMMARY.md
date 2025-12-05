# Refactoring Plan Summary

## Three God Objects to Refactor

### Priority 1: `infrastructure/storage.py` ⭐ HIGHEST
**File:** 1,510 LOC | **Coverage:** 16% | **MI:** 0.19

**Why Critical:** Lowest maintainability index in entire codebase, mission-critical but untested sync logic

**Solution:** Split into 4 focused classes
- `DatabaseManager` - DB infrastructure (250 LOC, 95%+ coverage)
- `FileSynchronizer` - File syncing logic (350 LOC, 0% → 80% coverage) ← BIGGEST WIN
- `SyncStateTracker` - Sync metadata tracking (100 LOC, 100% coverage)
- `ConflictResolver` - Git conflict handling (80 LOC, 100% coverage)
- `StateManager` becomes thin facade (100 LOC, delegates to above)

**Effort:** 8-11 hours over 4-5 phases
**Result:** Module coverage 16% → 80%, MI 0.19 → 45.0

---

### Priority 2: `cli/core.py` 🟠 HIGH
**File:** 1,134 LOC | **Coverage:** 54% | **MI:** 18.08

**Why Important:** Core initialization commands have 4 D/C-complexity functions, mostly untested

**Solution:** Extract business logic to service classes
- `ProjectInitializationService` - Init workflow (200 LOC, handles all D/C functions)
- `ProjectStatusService` - Status & health checks (150 LOC)
- `cli/core.py` becomes thin Click command wrapper (250 LOC, only @click decorators)

**Effort:** 6-8 hours
**Result:** Module coverage 54% → 85%, MI 18.08 → 65.0

---

### Priority 3: `application/health.py` 🟡 MEDIUM
**File:** 901 LOC | **Coverage:** 76% | **MI:** 16.82

**Why Useful:** Multiple scan functions mixed together, low MI, could be cleaner

**Solution:** Split into 4 focused validators
- `StructureValidator` - Directory structure checks (150 LOC)
- `DuplicateDetector` - Find duplicates & malformed files (120 LOC)
- `ArchiveScanner` - Archival readiness (130 LOC)
- `DataIntegrityChecker` - Data consistency checks (160 LOC)
- `HealthCheck` becomes thin orchestrator (200 LOC)

**Effort:** 7-9 hours
**Result:** Module coverage 76% → 90%, MI 16.82 → 58.0

---

## What Gets Moved Where

### storage.py Breakdown

| Current Location | New Location | Lines | Reason |
|-----------------|---|-------|--------|
| StateManager._init_database() | DatabaseManager | 100 | DB infrastructure |
| StateManager._run_migrations() | DatabaseManager | 30 | DB infrastructure |
| StateManager.transaction() | DatabaseManager | 15 | DB infrastructure |
| StateManager.create_* / get_* / update_* / delete_* | DatabaseManager | 200 | CRUD operations |
| StateManager.sync_issue_file() | FileSynchronizer | 80 | File sync (C complexity) |
| StateManager.sync_milestone_file() | FileSynchronizer | 90 | File sync (C complexity) |
| StateManager.sync_project_file() | FileSynchronizer | 50 | File sync |
| StateManager.sync_directory_incremental() | FileSynchronizer | 40 | Directory sync (C complexity) |
| StateManager.full_rebuild_from_git() | FileSynchronizer | 50 | Git rebuild (C complexity) |
| StateManager.smart_sync() | FileSynchronizer | 30 | Sync orchestration |
| StateManager._calculate_file_hash() | SyncStateTracker | 10 | Change detection |
| StateManager._parse_yaml_frontmatter() | FileSynchronizer | 20 | YAML parsing |
| StateManager.get_sync_state() / set_sync_state() | SyncStateTracker | 20 | State tracking |
| StateManager.get_file_sync_status() | SyncStateTracker | 15 | Status tracking |
| StateManager.check_git_conflicts() | ConflictResolver | 40 | Conflict detection |

### cli/core.py Breakdown

| Current Location | New Location | Reason |
|-----------------|---|--------|
| init() function body (160 LOC) | ProjectInitializationService.run_interactive_setup() | Init orchestration |
| _detect_project_context() | ProjectInitializationService.detect_project_context() | Project detection |
| _setup_github_integration() | ProjectInitializationService.setup_github_integration() | GitHub setup |
| _setup_main_project() | ProjectInitializationService.create_main_project() | Project creation |
| _detect_existing_projects() | ProjectInitializationService.detect_existing_projects() | Project discovery |
| status() function body | ProjectStatusService.get_project_status() | Status reporting |
| health() function body | ProjectStatusService.run_health_checks() | Health check orchestration |
| All display logic | Remains in cli/core.py | Click decorators, console output |

### health.py Breakdown

| Current Location | New Location | Reason |
|-----------------|---|--------|
| check_roadmap_directory() | StructureValidator | Structure validation |
| scan_for_folder_structure_issues() | StructureValidator | Structure scanning |
| check_duplicate_issues() | DuplicateDetector | Duplicate detection |
| scan_for_duplicate_issues() | DuplicateDetector | Duplicate scanning |
| scan_for_malformed_files() | DuplicateDetector | Malformed file detection |
| check_archivable_issues() | ArchiveScanner | Archive readiness |
| scan_for_archivable_issues() | ArchiveScanner | Archive scanning |
| check_data_integrity() | DataIntegrityChecker | Data consistency |
| scan_for_data_integrity_issues() | DataIntegrityChecker | Data scanning |
| check_orphaned_issues() | DataIntegrityChecker | Orphan detection |
| All remaining checks | Distributed to appropriate validator | Logical grouping |

---

## No Breaking Changes

All refactorings maintain 100% backward compatibility:

```python
# External code NEVER changes
from roadmap.infrastructure.storage import StateManager

state = StateManager()
state.sync_issue_file(path)  # Works exactly the same
state.create_issue(data)     # Still works
state.get_project(id)        # Unchanged API
```

**Why:**
- StateManager delegates internally to new classes
- Public method signatures never change
- Import statements never change
- All existing tests pass without modification

---

## Implementation Timeline

### Week 1: storage.py (CRITICAL)
**Mon-Tue:** DatabaseManager (2-3h)
- Extract DB methods from StateManager
- Create DatabaseManager class
- Add tests
- StateManager delegates

**Wed-Thu:** FileSynchronizer (4-5h)
- Extract all sync methods (~11 methods, 400 LOC)
- Move YAML parsing helpers
- Add comprehensive tests (0% → 80% coverage)
- StateManager delegates

**Fri:** Wrap-up (1-2h)
- Extract SyncStateTracker & ConflictResolver
- Run full test suite
- Verify coverage 16% → 80%

### Week 2: cli/core.py (HIGH)
**Mon-Tue:** ProjectInitializationService (3-4h)
- Extract init() logic
- Move all detection/setup helpers
- Add tests for each path

**Wed:** ProjectStatusService (2-3h)
- Extract status() & health() logic
- Add tests

**Thu-Fri:** Integration & verification
- Update cli/core.py to use services
- Run tests
- Verify coverage 54% → 85%

### Week 3-4: health.py (MEDIUM)
**Create validators structure + tests**

---

## Coverage Impact

```
BEFORE          AFTER (Target)
─────────────────────────────

storage.py      16%   →   85%   (+69%)
cli/core.py     54%   →   85%   (+31%)
health.py       76%   →   90%   (+14%)
────────────────────────────────
OVERALL         55%   →   80%   (+25%)
```

### Where the Wins Come From

**storage.py (69% gain):**
- FileSynchronizer: 0% → 80% (350 LOC of untested code)
- DatabaseManager: 95%+ (mostly already covered)
- Smaller classes easier to test completely

**cli/core.py (31% gain):**
- ProjectInitializationService covers init D-function
- ProjectStatusService covers status/health logic
- Cleaner code = easier to test paths

**health.py (14% gain):**
- Better organization, already 76%
- Each validator easier to test independently
- Cleaner inheritance patterns

---

## Key Benefits

✅ **Maintainability**
- 3x lower MI (0.19 → 45), (18 → 65), (16.8 → 58)
- Single responsibility principle applied
- Easier to understand code flow

✅ **Testability**
- Each class independently testable
- Can mock dependencies
- Clear test boundaries
- 25% coverage improvement

✅ **Architecture**
- Better separation of concerns
- No circular dependencies
- Cleaner dependency flow
- Extensible (easy to add features)

✅ **Developer Experience**
- Smaller files = easier to navigate
- Clear class responsibilities
- Easier to find code
- Easier to add tests

---

## Risk Assessment

### Risks: VERY LOW
- ✅ No breaking changes (backward compatible)
- ✅ Can implement phase by phase
- ✅ Tests verify everything works
- ✅ Old code stays until replacement proven

### Mitigation
- Run full test suite before each phase
- Keep old code until new code tested
- Feature flags if needed (but not needed here)
- Git history preserved (can revert)

---

## Success Metrics

| Metric | Before | Target | Status |
|--------|--------|--------|--------|
| Avg Module LOC | 1,182 | 250 | 🎯 5x smaller |
| Avg MI | 17.7 | 60 | 🎯 3.5x better |
| Test Coverage | 55% | 80% | 🎯 +25% |
| D-functions | 8 | 0 | 🎯 Eliminated |
| C-functions | 22 | 5 | 🎯 77% fewer |
| Module Dependencies | High | Low | 🎯 Isolated |

---

## Next Step

**→ Proceed with Phase 1 of storage.py refactoring (DatabaseManager extraction)**

This is:
- ✅ Lowest risk (simplest methods)
- ✅ Establishes the pattern
- ✅ Unblocks Phase 2 (biggest payoff)
- ✅ Can be completed in 2-3 hours
