# Phase 6: Comprehensive Layer Violation Hunt

## Objective
Identify and fix all architectural layer violations to ensure proper separation of concerns and maintain clean dependency boundaries.

## Layer Dependency Rules (Allowed Imports)

### ✅ Allowed Import Directions

```
Adapters (CLI)
    ↓ can import from Core, Common, Shared

Core (Application/Services)
    ↓ can import from Common, Shared

Common (Shared Utilities)
    ↓ can import from Shared

Shared (Infrastructure)
    ↓ no dependencies (leaf layer)
```

### ❌ Forbidden Import Directions

- Core importing from Adapters ❌
- Core importing from Infrastructure directly (should go through interfaces) ❌
- Common importing from Adapters ❌
- Common importing from Core ❌
- Shared importing from anything ❌
- Adapters importing from Infrastructure directly (should use services) ❌

## Scanning Strategy

### Phase 6a: Identify Violations
1. Scan all imports in each layer
2. Build dependency graph
3. Identify backwards/lateral dependencies
4. Categorize by severity

### Phase 6b: Generate Report
1. List all violations with line numbers
2. Suggest fixes
3. Estimate refactoring effort

### Phase 6c: Fix Violations
1. High priority violations first
2. Use dependency injection and interfaces
3. Test after each fix

## Expected Issues

Based on architecture analysis, likely violations:
- Direct Core → Adapters imports (should use dependency injection)
- Direct Common → Core imports (circular dependencies)
- Infrastructure imports scattered across layers
- Shared imports in wrong places

## Success Criteria

✅ No imports from lower layers to upper layers
✅ Clean dependency graph (acyclic)
✅ All circular dependencies eliminated
✅ All imports validated by architecture checker
✅ All 6,558+ tests passing after fixes

## Phase 6b: Layer Consolidation Tasks

In addition to fixing boundary violations, we identified structural redundancies:

### 6b.1: Consolidate common/ and shared/ layers ✅ COMPLETE
- **Issue**: Both layers serve identical purpose ("stuff used everywhere")
- **Solution**: Consolidate into single `common/` layer, move `shared/*` contents there, delete `shared/`
- **Impact**: Reduces confusion for new developers, clearer mental model
- **Effort**: 2-3 hours (need to update ~150+ imports)

### 6b.2: Consolidate logging modules (NEW - Code Smell Fix)
- **Issue**: `common/logging/` and `infrastructure/logging/` have overlapping responsibilities
  - common/logging: core logging, formatting, correlation IDs (87 imports)
  - infrastructure/logging: decorators, error logging, performance tracking (52 imports)
- **Solution**: Consolidate `infrastructure/logging/` into `common/logging/`
  - Move decorators.py, error_logging.py, audit_logging.py, performance_tracking.py to common/logging
  - Delete infrastructure/logging, update 52 imports
- **Impact**: Single source of truth for logging, eliminates developer confusion
- **Effort**: 2-3 hours (straightforward consolidation + import updates)
- **Priority**: HIGH (common pattern across codebase)

### 6b.3: Reorganize GitHub modules (NEW - Code Smell Fix)
- **Issue**: GitHub functionality fragmented across 3 layers with unclear responsibility
  - adapters/github: API client (9 classes)
  - core/services/github: business logic (6 classes)
  - infrastructure/github: setup/config management (4 classes)
  - Problem: TokenResolver, ConfigManager logically belong in common/configuration, not infrastructure
- **Solution**: Clean layer separation
  - adapters/github: keep as thin API layer
  - core/services/github: keep business logic
  - Migrate infrastructure/github to:
    - common/configuration/github/ (TokenResolver, ConfigManager)
    - common/initialization/github/ (SetupValidator, InitializationService)
  - Delete infrastructure/github
- **Impact**: Proper layer separation, removes ~30 imports from wrong layer
- **Effort**: 4-5 hours (more complex refactoring, more testing)
- **Priority**: MEDIUM (architectural improvement)

### 6b.4: Simplify interface methods (duplicate operations)
- **Issue**: Redundant push_issue() and push_issues() methods (can always batch to push_issues)
- **Issue**: Similar redundancy with pull_issue/pull_issues
- **Solution**: Consolidate to single methods that accept list[Issue]
- **Impact**: Cleaner API, easier to maintain
- **Effort**: 1-2 hours (interface updates + test mocks)

### 6b.5: Split infrastructure/ layer by concern
- **Issue**: Infrastructure mixes persistence, GitHub adapters, observability, security, git coordination
- **Solution**: Consider separating into: persistence/, github/, observability/, security/
- **Impact**: Better separation of concerns, clearer what each submodule does
- **Effort**: 3-4 hours (structural reorganization + import updates)
- **Note**: Lower priority - first verify that 6b.1-6b.3 don't create better patterns

## Timeline

- **Phase 6a**: Scan & identify (20-30 min) ✅ COMPLETE
- **Phase 6b**: Report generation (10-15 min) ✅ COMPLETE
- **Phase 6b: Consolidation Tasks** ✅ ALL COMPLETE
  - 6b.1: Consolidate common/shared layers ✅ COMPLETE
  - 6b.2: Consolidate logging modules ✅ COMPLETE (verified consolidation, added enhanced logging)
  - 6b.3: Reorganize GitHub modules ✅ COMPLETE (TokenResolver/ConfigManager moved to common/configuration)
  - 6b.4: Simplify interface methods ✅ COMPLETE (consolidated push/pull methods)
  - 6b.5: Split infrastructure layer ✅ COMPLETE
    - Created: coordination/, git/, observability/, validation/ subdirectories
    - Organized: 25+ files into proper concern areas
    - Updated: 160+ imports across codebase
- **Phase 6c**: Fix boundary violations (IN PROGRESS)
  - Current status: **105 violations** (down from 685 baseline) - **85% reduction!** ✅
  - Goal: <50 violations by end of phase 6c
  - Progress: On track to exceed goal
- **Phase 6d**: Test refactoring (PLANNED)
  - Consolidate duplicate test directories (tests_core vs core, etc.)
  - Restructure tests to mirror infrastructure/ subdirectories
  - Scan test layer violations
  - Fix critical test isolation issues
- **Verification**: Full test suite validation (15-20 min)
