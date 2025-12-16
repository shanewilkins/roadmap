# Refactoring Roadmap - Quick Reference

**Generated**: December 16, 2025
**Test Status**: ✅ 2506 passing
**Codebase Ready**: Yes (baseline established)

---

## 🎯 Top 5 Most Impactful Refactorings

### 1. StateManager God Object (42 methods)
**Priority**: 🔴 CRITICAL
**Effort**: 4-6 hours
**Impact**: Improves testability, reduces coupling, clarifies responsibility

**Location**: `adapters/persistence/storage/state_manager.py` (376 lines)

**Quick Action**:
```python
# Current - 42 methods managing 5+ different concerns
class StateManager:
    def get_issue_state(self, issue_id): ...
    def get_project_state(self, project_id): ...
    def get_sync_state(self): ...
    # ... 39 more methods

# Target - Split into specialized managers
StateManager (facade)
  ├── IssueStateManager (10 methods)
  ├── ProjectStateManager (8 methods)
  ├── SyncStateManager (6 methods)
  ├── UserStateManager (5 methods)
  └── ValidationStateManager (9 methods)
```

**Benefits**:
- Each manager has single responsibility
- Easier to test in isolation
- Reduced cognitive load
- Clearer dependencies

---

### 2. Core Services - Dependency Inversion (27 violations)
**Priority**: 🔴 CRITICAL
**Effort**: 2-3 hours (quick) / 8-12 hours (full)
**Impact**: Fixes architectural bleeding, enables proper testing, improves testability

**Problem**:
```python
# core/services/issue_service.py (BAD)
from infrastructure.issue_operations import IssueOperations  # ❌ Wrong direction

# Should be:
from domain.repositories import IssueRepository  # ✅ Correct direction
```

**Quick Fix** (2-3 hours):
1. Create abstract interfaces in `domain/repositories/`
2. Have infrastructure implement them
3. Inject dependencies into services
4. Fix direct imports in 5-7 service files

**Full Fix** (8-12 hours):
1. Complete dependency injection setup
2. Create repository interfaces for all entities
3. Extract all infrastructure calls to repositories
4. Add integration tests

---

### 3. Cleanup.py - Mixed Concerns (485 lines)
**Priority**: 🟡 HIGH
**Effort**: 6-8 hours
**Impact**: Reduces file size by 70%, improves maintainability

**Current Mixture**:
```
cleanup.py (485 lines)
  ├── Backup operations (100 lines)
  ├── Folder cleanup (80 lines)
  ├── Duplicate detection (120 lines)
  ├── Malformed detection (100 lines)
  └── Orchestration (85 lines)
```

**Target Structure**:
```
infrastructure/maintenance/
  ├── backup_manager.py (100 lines)
  ├── folder_cleaner.py (80 lines)
  ├── duplicate_detector.py (120 lines)
  ├── malformed_detector.py (100 lines)
  └── cleanup.py (orchestrator, 85 lines)
```

---

### 4. Service Layer Parameter Refactoring (9-param functions)
**Priority**: 🟡 HIGH
**Effort**: 3-4 hours
**Impact**: Consistency with CLI layer, cleaner interfaces

**Candidates**:
1. `IssueService.create_issue()` - 9 params
2. `IssueBuilder.build_create_dict()` - 9 params
3. `IssueOperations.create_issue()` - 9 params
4. `IssueCoordinator.create()` - 9 params

**Pattern** (already used in CLI):
```python
# Before
def create_issue(self, title, priority, status, assignee,
                 milestone, description, estimate, depends_on, blocks):
    pass

# After - reuse existing IssueCreateParams or create service-specific version
def create_issue(self, params: IssueCreateServiceParams):
    pass

@dataclass
class IssueCreateServiceParams:
    title: str
    priority: str
    status: str
    assignee: str
    milestone: str
    description: str
    estimate: str
    depends_on: List[str]
    blocks: List[str]
```

---

### 5. CoreInitializationPresenter - Multiple Presenters (31 methods)
**Priority**: 🟡 HIGH
**Effort**: 3-5 hours
**Impact**: Follows separation of concerns, easier to add new entity types

**Current**:
```python
class CoreInitializationPresenter:  # 31 methods
    # Issue presentation (6 methods)
    # Milestone presentation (5 methods)
    # Project presentation (4 methods)
    # Status display (8 methods)
    # Utilities (8 methods)
```

**Target**:
```python
# Abstract interface
class Presenter(ABC):
    def format(self, entity) -> str: ...

# Specific presenters
class IssuePresenter(Presenter): ...
class MilestonePresenter(Presenter): ...
class ProjectPresenter(Presenter): ...
class StatusPresenter(Presenter): ...

# Utility module
presentation_utils.py  # Shared formatting logic
```

---

## 📋 Implementation Checklist

### Phase 1: Quick Wins (2-3 hours)
- [ ] Document architecture layers (README.md)
- [ ] Create abstract interfaces in `domain/repositories/`
  - [ ] `IssueRepository`
  - [ ] `ProjectRepository`
  - [ ] `MilestoneRepository`
- [ ] Add type hints documentation to architecture
- [ ] Update test baseline after Phase 1

**Commit**: "refactor: add abstract repository interfaces for dependency inversion"

---

### Phase 2: Service Layer Refactoring (3-4 hours)
- [ ] Create service-layer parameter dataclasses
  - [ ] `IssueCreateServiceParams`
  - [ ] `IssueUpdateServiceParams`
  - [ ] Coordinator parameter model
- [ ] Refactor 4 service functions
  - [ ] `IssueService.create_issue()`
  - [ ] `IssueBuilder.build_create_dict()`
  - [ ] `IssueOperations.create_issue()`
  - [ ] `IssueCoordinator.create()`
- [ ] Run test suite
- [ ] Update all callers

**Commit**: "refactor: consolidate service layer parameters using dataclasses"

---

### Phase 3: State Manager Split (4-6 hours)
- [ ] Create `IssueStateManager` class
- [ ] Create `ProjectStateManager` class
- [ ] Create `SyncStateManager` class
- [ ] Create `UserStateManager` class
- [ ] Create `ValidationStateManager` class
- [ ] Create `StateManager` facade maintaining compatibility
- [ ] Update all references (gradual migration)
- [ ] Add tests for each manager
- [ ] Run full test suite

**Commit**: "refactor: split StateManager into focused managers"

---

### Phase 4: Large File Refactoring (6-8 hours)
- [ ] **cleanup.py** - Split into 5 modules
  - [ ] Move backup logic to `backup_manager.py`
  - [ ] Move folder cleanup to `folder_cleaner.py`
  - [ ] Move duplicate detection to `duplicate_detector.py`
  - [ ] Move malformed detection to `malformed_detector.py`
  - [ ] Create orchestrator in `cleanup.py`
- [ ] **init/commands.py** - Internal reorganization
  - [ ] Extract initialization logic to separate module
  - [ ] Extract GitHub setup logic
  - [ ] Extract template handling
  - [ ] Keep Click commands in `commands.py`
- [ ] **CoreInitializationPresenter** - Split into presenters
  - [ ] Extract `IssuePresenter`
  - [ ] Extract `MilestonePresenter`
  - [ ] Extract `ProjectPresenter`
  - [ ] Extract `StatusPresenter`
  - [ ] Create `presentation_utils.py`
- [ ] Run full test suite for each split

**Commits** (one per split):
- "refactor: split cleanup.py into focused managers"
- "refactor: reorganize init command module"
- "refactor: split presenter into entity-specific classes"

---

### Phase 5: Code Quality Polish (2-3 hours)
- [ ] Extract common `Validator` interface
  - [ ] Update all validators to inherit from interface
  - [ ] Consolidate `get_check_name()` and `perform_check()`
- [ ] Review and consolidate builder patterns
  - [ ] Create `Builder` interface if applicable
  - [ ] Consolidate `build_*_dict()` methods
- [ ] Run full quality audit again

**Commit**: "refactor: extract common patterns (validators, builders)"

---

## 🧪 Testing Strategy

After each phase:
```bash
# Run full test suite
poetry run pytest

# Check type hints
poetry run pyright

# Lint and format
poetry run ruff format roadmap/
poetry run ruff check --fix roadmap/

# Measure coverage
poetry run pytest --cov=roadmap
```

**Expected Result**: 2506+ tests passing, 0 regressions

---

## 📊 Metrics to Track

### Before Refactoring
- God objects: 2 (42 & 31 methods)
- Functions with >7 params: 15
- Layer violations: 27
- Largest file: 551 lines
- Average file size: ~120 lines

### After Complete Refactoring (Target)
- God objects: 0
- Functions with >7 params: 0
- Layer violations: 0
- Largest file: <300 lines
- Average file size: <100 lines

---

## 💡 Architecture Pattern: Dependency Injection

**Before** (current, tight coupling):
```python
# core/services/issue_service.py
from infrastructure.issue_operations import IssueOperations

class IssueService:
    def __init__(self):
        self.operations = IssueOperations()  # Direct dependency
```

**After** (proper layering):
```python
# domain/repositories/issue_repository.py
from abc import ABC, abstractmethod

class IssueRepository(ABC):
    @abstractmethod
    def create(self, issue: Issue) -> Issue: ...

# infrastructure/repositories/issue_repository.py
from domain.repositories import IssueRepository

class IssueRepositoryImpl(IssueRepository):
    def create(self, issue: Issue) -> Issue:
        # Infrastructure implementation

# core/services/issue_service.py
class IssueService:
    def __init__(self, repository: IssueRepository):
        self.repository = repository  # Injected, loosely coupled
```

---

## 🎓 Key Principles Applied

1. **Single Responsibility**: Each class has one reason to change
2. **Dependency Inversion**: Depend on abstractions, not implementations
3. **Don't Repeat Yourself (DRY)**: Extract common patterns
4. **Separation of Concerns**: Mixed responsibilities split into focused modules
5. **Interface Segregation**: Create small, focused interfaces

---

## 📚 Related Documentation

- `CODE_QUALITY_AUDIT.md` - Detailed findings and analysis
- `REFACTORING_SUMMARY.md` - Previous refactoring work (CLI parameters)
- `README.md` - Architecture documentation (to be updated)

---

## ⏱️ Timeline Estimate

| Phase | Effort | Complexity | Impact |
|-------|--------|-----------|--------|
| 1 | 2-3 hrs | Low | 🟢 Enable future refactoring |
| 2 | 3-4 hrs | Low | 🟡 Consistency with CLI |
| 3 | 4-6 hrs | Medium | 🔴 Improves testability |
| 4 | 6-8 hrs | Medium | 🔴 Reduces file complexity |
| 5 | 2-3 hrs | Low | 🟡 Code quality polish |
| **Total** | **20-28 hrs** | **Medium** | **Major improvement** |

---

## ✅ Success Criteria

- [x] Baseline audit completed
- [x] All findings documented
- [x] Refactoring roadmap created
- [x] 2506 tests remain passing
- [ ] Phase 1 complete (2-3 hrs)
- [ ] Phase 2 complete (3-4 hrs)
- [ ] Phase 3 complete (4-6 hrs)
- [ ] Phase 4 complete (6-8 hrs)
- [ ] Phase 5 complete (2-3 hrs)
- [ ] Final audit showing 0 critical issues
- [ ] API freeze documentation updated

---

## 🚀 Next Action

**Option A: Start Phase 1 Immediately**
```bash
# Create abstract interfaces foundation
poetry run roadmap init --template=architecture
```

**Option B: Plan & Review First**
Review `CODE_QUALITY_AUDIT.md` and discuss priorities with team

**Recommendation**: Start with Option B (review), then proceed with Phase 1 quick wins to establish foundation for later phases.
