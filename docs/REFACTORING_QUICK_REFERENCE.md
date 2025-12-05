# Refactoring Quick Reference

## Priority 1: storage.py Extraction (HIGHEST PAYOFF)

### 📊 Current State
- **Size:** 1,510 LOC | **Coverage:** 16% | **MI:** 0.19 | **Issues:** D-complexity functions

### ✂️ What Gets Extracted

```
infrastructure/storage.py  (1,510 LOC → 300 LOC facade)
│
├─→ infrastructure/persistence/database_manager.py  (NEW, ~250 LOC)
│   ├── _init_database()
│   ├── _run_migrations()
│   ├── transaction()
│   ├── All CRUD methods (create_*, get_*, update_*, delete_*, archive_*)
│   └── vacuum(), is_initialized(), is_safe_for_writes()
│
├─→ infrastructure/persistence/file_synchronizer.py  (NEW, ~350 LOC) ⭐ MOST COMPLEX
│   ├── sync_issue_file()      ← C complexity, currently untested
│   ├── sync_milestone_file()  ← C complexity, currently untested
│   ├── sync_project_file()
│   ├── sync_directory_incremental()  ← C complexity
│   ├── full_rebuild_from_git()       ← C complexity, untested
│   ├── smart_sync()
│   ├── _calculate_file_hash()
│   ├── _parse_yaml_frontmatter()
│   └── _common_sync_entity()
│
├─→ infrastructure/persistence/sync_state_tracker.py  (NEW, ~100 LOC)
│   ├── get_sync_state()
│   ├── set_sync_state()
│   ├── get_file_sync_status()
│   ├── update_file_sync_status()
│   └── has_file_changed()
│
└─→ infrastructure/conflict_resolver.py  (NEW, ~80 LOC)
    ├── check_git_conflicts()
    ├── has_git_conflicts()
    └── get_conflict_files()

Refactored: infrastructure/persistence/state_manager.py  (100 LOC facade)
└── StateManager now delegates to all above
```

### 🎯 Why This Order

1. **DatabaseManager first** - Simplest, sets the pattern
2. **FileSynchronizer second** - Biggest payoff, most untested (~400 LOC at 0%)
3. **ConflictResolver third** - Smallest, quick win
4. **SyncStateTracker last** - Internal helper

### 📦 Dependencies (Only StateManager imports change internally)

**No breaking changes:**
- All 6 services still receive `StateManager`
- StateManager delegates to new classes
- External code doesn't see the split

```python
# BEFORE
state_mgr = StateManager()
state_mgr.sync_issue_file(path)

# AFTER - Same interface!
state_mgr = StateManager()
state_mgr.sync_issue_file(path)  # Now delegates to file_sync internally
```

### ✅ Phase Checklist

- [x] Phase 1: DatabaseManager (2-3h) ✅ COMPLETED
  - [x] Create `infrastructure/persistence/database_manager.py`
  - [x] Move DB methods + tests
  - [x] StateManager delegates
  - [x] All tests pass (1449 passed)

- [x] Phase 2: FileSynchronizer (4-5h) ✅ COMPLETED
  - [x] Create `infrastructure/persistence/file_synchronizer.py`
  - [x] Move sync methods (~11 methods)
  - [x] Create comprehensive tests
  - [x] StateManager delegates
  - [x] Coverage 16% → ready for component testing

- [x] Phase 3: SyncStateTracker & ConflictResolver (2-3h) ✅ COMPLETED
  - [x] Create both new classes
  - [x] Add tests
  - [x] StateManager delegates
  - [x] All tests passing (1449 passed)

- [ ] Phase 4: Write Comprehensive Tests (4-6h)
  - [ ] Write FileSynchronizer tests (~350 LOC untested)
  - [ ] Write DatabaseManager tests
  - [ ] Write SyncStateTracker tests
  - [ ] Write ConflictResolver tests
  - [ ] Coverage 55% → 75%+

- [ ] Phase 5: Optional Cleanup & Verification (1h)
  - [ ] StateManager review
  - [ ] Integration test pass
  - [ ] Coverage verification

---

## Priority 2: cli/core.py Extraction (HIGH)

### 📊 Current State
- **Size:** 1,134 LOC | **Coverage:** 54% | **MI:** 18.08 | **Issues:** 4 D/C-complexity functions

### ✂️ What Gets Extracted

```
cli/core.py  (1,134 LOC → 250 LOC commands only)
│
├─→ application/services/initialization_service.py  (NEW, ~200 LOC)
│   └── ProjectInitializationService
│       ├── run_interactive_setup()    ← from init()
│       ├── detect_existing_projects() ← D complexity
│       ├── detect_project_context()   ← D complexity
│       ├── create_main_project()      ← C complexity
│       └── setup_github_integration() ← C complexity
│
└─→ application/services/status_service.py  (NEW, ~150 LOC)
    └── ProjectStatusService
        ├── get_project_status()    ← from status()
        └── run_health_checks()     ← from health()

Refactored: cli/core.py  (250 LOC, click commands only)
├── @click.command init()    ← Click wrapper only
├── @click.command status()  ← Click wrapper only
└── @click.command health()  ← Click wrapper only
```

### 🎯 Why This Order

1. **Initialization service** - Largest, most complex (covers init D-rated function)
2. **Status service** - Status + health check coordination

### 📦 No Breaking Changes
- Click command signatures unchanged
- Parameters same
- Output format same

### ✅ Phase Checklist

- [ ] Phase 1: ProjectInitializationService (3-4h)
  - [ ] Create `application/services/initialization_service.py`
  - [ ] Move init() logic and helpers
  - [ ] Add tests for each detection path
  - [ ] Update cli/core.py to use service
  - [ ] Coverage 54% → 70%+

- [ ] Phase 2: ProjectStatusService (2-3h)
  - [ ] Create `application/services/status_service.py`
  - [ ] Move status() and health() logic
  - [ ] Add tests
  - [ ] Update cli/core.py
  - [ ] Coverage 70% → 80%+

- [ ] Phase 3: Cleanup cli/core.py (1h)
  - [ ] Keep only @click commands
  - [ ] Remove business logic
  - [ ] Verify all tests pass

---

## Priority 3: health.py Extraction (MEDIUM)

### 📊 Current State
- **Size:** 901 LOC | **Coverage:** 76% | **MI:** 16.82 | **Issues:** Multiple scan functions mixed

### ✂️ What Gets Extracted

```
application/health.py  (901 LOC → 200 LOC orchestrator)
│
└── application/validators/  (NEW DIRECTORY)
    ├── structure_validator.py      (NEW, ~150 LOC)
    │   └── StructureValidator
    │       ├── check_roadmap_directory()
    │       ├── check_issues_directory()
    │       ├── check_milestones_directory()
    │       ├── check_folder_structure()
    │       └── scan_for_folder_structure_issues()
    │
    ├── duplicate_detector.py       (NEW, ~120 LOC)
    │   └── DuplicateDetector
    │       ├── check_duplicate_issues()
    │       ├── scan_for_duplicate_issues()
    │       └── scan_for_malformed_files()
    │
    ├── archive_scanner.py          (NEW, ~130 LOC)
    │   └── ArchiveScanner
    │       ├── check_archivable_issues()
    │       ├── check_archivable_milestones()
    │       ├── scan_for_archivable_issues()
    │       └── scan_for_archivable_milestones()
    │
    ├── data_integrity_checker.py   (NEW, ~160 LOC)
    │   └── DataIntegrityChecker
    │       ├── check_state_file()
    │       ├── check_git_repository()
    │       ├── check_database_integrity()
    │       ├── check_data_integrity()
    │       ├── check_orphaned_issues()
    │       ├── check_old_backups()
    │       └── scan_for_data_integrity_issues()
    │
    └── __init__.py                 (Export public classes)

Refactored: application/health.py  (200 LOC orchestrator)
└── HealthCheck
    └── run_all_checks()  ← orchestrates 4 validators
```

### 🎯 Why This Order

**Validators are organized by concern:**
1. **StructureValidator** - File system structure
2. **DuplicateDetector** - Finding duplicates
3. **ArchiveScanner** - Archive readiness
4. **DataIntegrityChecker** - Data consistency

### 📦 Updates Needed

Only in `presentation/cli/cleanup.py`:
```python
# Before
from roadmap.application.health import scan_for_*, check_*

# After
from roadmap.application.validators import *
```

### ✅ Phase Checklist

- [ ] Create `application/validators/` directory
  - [ ] Create `__init__.py`
  - [ ] Create all 4 validator files

- [ ] Extract each validator (1.5h each)
  - [ ] StructureValidator
  - [ ] DuplicateDetector
  - [ ] ArchiveScanner
  - [ ] DataIntegrityChecker

- [ ] Add tests for each (2h)
  - [ ] Test coverage 76% → 90%+

- [ ] Refactor HealthCheck orchestrator (1h)
  - [ ] Update imports in cleanup.py
  - [ ] Verify all tests pass

---

## Timeline & Effort Summary

### Week 1: storage.py (CRITICAL)
- **Mon:** DatabaseManager (2-3h) ✓ Phase 1
- **Tue:** FileSynchronizer (4-5h) ✓ Phase 2
- **Wed:** SyncStateTracker + ConflictResolver (2-3h) ✓ Phase 3
- **Thu:** Cleanup & tests (1-2h) ✓ Phase 4
- **Fri:** Integration testing & coverage verification

**Result:** Coverage 16% → 80% on storage module

### Week 2: cli/core.py (HIGH PRIORITY)
- **Mon:** ProjectInitializationService (3-4h)
- **Tue:** ProjectStatusService (2-3h)
- **Wed:** Cleanup cli/core.py (1h)
- **Thu-Fri:** Tests & integration

**Result:** Coverage 54% → 80%+ on cli module

### Week 3-4: health.py (MEDIUM PRIORITY)
- **Mon-Tue:** Create validators structure & 4 classes
- **Wed:** Add comprehensive tests
- **Thu:** Refactor HealthCheck orchestrator
- **Fri:** Integration testing

**Result:** Coverage 76% → 90%+ (and better organized)

### Total Investment
- **Time:** 20-26 hours
- **Output:** 3 god objects split into 10+ focused classes
- **Payoff:**
  - Coverage: 55% → 80%+ overall
  - Maintainability: Average MI from ~17 to ~60+
  - Testability: Each class independently testable

---

## High-Level Pattern

All 3 refactorings follow the same pattern:

```python
# CURRENT: One monolithic class
class GodObject:
    def handle_a()
    def handle_b()
    def handle_c()
    def handle_d()

# REFACTORED: Orchestrator + focused handlers
class FocusedHandlerA:
    def handle()

class FocusedHandlerB:
    def handle()

class Orchestrator:
    def __init__(self):
        self.a = FocusedHandlerA()
        self.b = FocusedHandlerB()

    def do_something():
        self.a.handle()
        self.b.handle()
```

Benefits:
✅ Single Responsibility Principle
✅ Easy to test each handler independently
✅ Easy to mock dependencies
✅ Easy to add new handlers later
✅ Easier to understand code flow
