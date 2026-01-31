# Coverage Analysis & Prioritization Strategy

**Overall Package Coverage:** 77% (26673 stmts, 6057 missed)
**Target:** 85% overall coverage

---

## TIER 1: Critical Sync Components (<85% Coverage)

These are core to sync functionality and must reach 85%+

### 1. **SyncStateManager** (PRIORITY: HIGHEST)
- **File:** `roadmap/core/services/sync/sync_state_manager.py`
- **Current:** 46% (127 stmts, 68 missed)
- **Gap:** 39% to reach 85%
- **Impact:** CRITICAL - State persistence is fundamental to sync
- **Lines to Cover:** 213-222, 246-305, 321-363, 377-440
- **Rationale:** Phase 2 test suite exists but focuses only on load/save. Uncovered lines are in other utility methods.

### 2. **SyncChangeComputer** (PRIORITY: HIGH)
- **File:** `roadmap/core/services/sync/sync_change_computer.py`
- **Current:** 70% (77 stmts, 23 missed)
- **Gap:** 15% to reach 85%
- **Impact:** HIGH - Change computation is core to sync operations
- **Lines to Cover:** 54-65, 108-129, 187-207
- **Rationale:** Phase 2 tests cover main paths. Uncovered: enum conversion edge cases, alternative format handling.

### 3. **SyncConflictDetector** (PRIORITY: HIGH)
- **File:** `roadmap/core/services/sync/sync_conflict_detector.py`
- **Current:** 76% (62 stmts, 15 missed)
- **Gap:** 9% to reach 85%
- **Impact:** HIGH - Conflict detection is critical for data integrity
- **Lines to Cover:** 58-69, 78, 119-120, 131-145
- **Rationale:** Phase 3 target. Relatively small gap - quick win.

### 4. **SyncConflictResolver** (PRIORITY: HIGH)
- **File:** `roadmap/core/services/sync/sync_conflict_resolver.py`
- **Current:** 82% (146 stmts, 27 missed)
- **Gap:** 3% to reach 85%
- **Impact:** HIGH - Conflict resolution strategy critical
- **Lines to Cover:** 124-133, 165-168, 171-174, 297-298, 310-311, 317-325, 356-362, 439-446
- **Rationale:** Phase 1 tests exist. Small gap - error handling paths uncovered.

### 5. **SyncMetadataService** (PRIORITY: MEDIUM)
- **File:** `roadmap/core/services/sync/sync_metadata_service.py`
- **Current:** 60% (85 stmts, 34 missed)
- **Gap:** 25% to reach 85%
- **Impact:** MEDIUM - Metadata management (backend, timestamps)
- **Lines to Cover:** 127-152, 173-188, 200-201, 212-230
- **Rationale:** Not yet tested. Medium size, reasonable gap.

### 6. **SyncStateNormalizer** (PRIORITY: LOW - Quick Win!)
- **File:** `roadmap/core/services/sync/sync_state_normalizer.py`
- **Current:** 92% (24 stmts, 2 missed)
- **Gap:** Already 92%! Only 2 lines uncovered
- **Impact:** LOW - Already excellent coverage
- **Lines to Cover:** 42, 45
- **Rationale:** Tiny file, nearly complete. Easy to finish.

---

## TIER 2: Secondary Sync/Backend Components (Bang for Buck)

These provide good coverage improvement with reasonable effort. Focus on ROI.

### High ROI (Small gap, big impact):

1. **SyncPlanExecutor** - 66% (164 stmts, 56 missed)
   - Gap: 19% to reach 85%
   - **Impact:** HIGH - Executes sync operations
   - **Why:** Not tested; moderate size; execution logic critical

2. **SyncKeyNormalizer** - 74% (69 stmts, 18 missed)
   - Gap: 11% to reach 85%
   - **Impact:** MEDIUM - Key normalization
   - **Why:** Not tested; smaller file; normalization logic

3. **RemoteIssueCreationService** - 38% (29 stmts, 18 missed)
   - Gap: 47% to reach 85%
   - **Impact:** MEDIUM - Creates issues during sync
   - **Why:** Phase 3 target; small file; core functionality

### Medium ROI:

4. **SyncCacheOrchestrator** - 58% (146 stmts, 62 missed)
   - Gap: 27% to reach 85%
   - **Impact:** MEDIUM - Cache optimization
   - **Why:** Not tested; moderate size; optimization layer

5. **SyncRetrievalOrchestrator** - 59% (277 stmts, 114 missed)
   - Gap: 26% to reach 85%
   - **Impact:** MEDIUM - High-level sync coordination
   - **Why:** Partially tested; large file; orchestration

6. **SyncMergeEngine** - 40% (220 stmts, 131 missed)
   - Gap: 45% to reach 85%
   - **Impact:** MEDIUM - Merges data from multiple sources
   - **Why:** Not tested; large file; complex logic

### Lower ROI (but could help overall):

7. **SyncMergeOrchestrator** - 48% (210 stmts, 110 missed)
   - Gap: 37% to reach 85%
   - **Impact:** LOW-MEDIUM - Orchestrates merge
   - **Why:** Not tested; large file; complexity

8. **SyncDataFetchService** - 67% (79 stmts, 26 missed)
   - Gap: 18% to reach 85%
   - **Impact:** MEDIUM - Fetches sync data
   - **Why:** Not tested; smaller file

---

## TIER 3: Non-Sync/Lower Priority

These files are less critical to sync but could improve overall coverage.

### Configuration/Settings (RECOMMEND EXCLUSION):

❌ **roadmap/settings.py** - 38% (74 stmts, 46 missed)
   - Gap: 47% to reach 85%
   - **RECOMMENDATION:** EXCLUDE from coverage targets
   - **Reason:** Configuration files are typically excluded from coverage
   - **Use Case:** Settings are validated at runtime, not heavily logic-tested

❌ **roadmap/version.py** - 61% (184 stmts, 71 missed)
   - Gap: 24% to reach 85%
   - **RECOMMENDATION:** EXCLUDE or deprioritize
   - **Reason:** Version tracking/constants; low logic complexity
   - **Use Case:** Data structure, not critical logic

### Infrastructure/Adapters (Moderate Priority):

1. **Infrastructure Security/Credentials** - 64% (210 stmts, 75 missed)
   - Gap: 21% to reach 85%
   - **Impact:** MEDIUM - Security sensitive
   - **Why:** Not widely tested; security critical

2. **GitHub Backend Helpers** - 12% (120 stmts, 106 missed)
   - Gap: 73% to reach 85%
   - **Impact:** MEDIUM - GitHub integration
   - **Why:** Large file; complex API handling; mostly untested

3. **CLI Sync Module** - 34% (121 stmts, 80 missed)
   - Gap: 51% to reach 85%
   - **Impact:** LOW - User-facing CLI
   - **Why:** Integration layer; user-tested manually; e2e preferred

4. **Persistence/FileSync** - 89% (37 stmts, 4 missed)
   - Gap: Already 89%!
   - **Impact:** HIGH - File persistence
   - **Why:** Nearly complete; easy win (4 lines)

5. **Database Manager** - 92% (116 stmts, 9 missed)
   - Gap: Already 92%!
   - **Impact:** HIGH - Database operations
   - **Why:** Almost complete; easy win (9 lines)

---

## TIER 4: Configuration/Exclusion Candidates

### RECOMMEND EXCLUDING from coverage:

1. **Settings** - Configuration management, not logic
2. **Version** - Constants and metadata
3. **CLI Sync Context** - 0% (94 stmts) - Integration scaffolding
4. **CLI Init** - 0% (2 stmts) - Stub module
5. **CLI Sync Service** - 0% (16 stmts) - Thin wrapper

**Why Exclude These:**
- Configuration files don't contain testable logic
- Version/constant files are data, not algorithms
- Stub/thin wrapper modules test elsewhere (integration tests)
- Excluding these 5 files would remove ~126 uncovered statements
- **New package coverage: 77% → ~78%** with exclusions

### Configuration Files (Should Be Tested but Different Approach):

✅ **roadmap/common/configuration/config_manager.py** - 72% - *Test configuration loading/validation*
✅ **roadmap/common/configuration/config_schema.py** - 100% ✅

---

## SUMMARY: Prioritized Action Plan

### ✅ QUICK WINS (Easy coverage gains):
1. SyncStateNormalizer - 92% → 100% (2 lines)
2. FileSync - 89% → 100% (4 lines)
3. DatabaseManager - 92% → 100% (9 lines)
4. **ROI: 15 lines = ~0.06% overall improvement**

### 🎯 TIER 1 TARGETS (Must reach 85%):
1. **SyncConflictResolver** - 82% → 85% (3% gap) - Phase 1
2. **SyncConflictDetector** - 76% → 85% (9% gap) - Phase 3
3. **SyncChangeComputer** - 70% → 85% (15% gap) - Phase 2
4. **SyncStateManager** - 46% → 85% (39% gap) - Phase 2
5. **SyncMetadataService** - 60% → 85% (25% gap) - Phase 3

### 📊 TIER 2 TARGETS (Bang for Buck):
1. RemoteIssueCreationService - Phase 3
2. SyncKeyNormalizer - Phase 3
3. SyncPlanExecutor - Phase 4?
4. SyncDataFetchService - Phase 4?

### ❌ EXCLUDE (Not Core Logic):
- settings.py (configuration)
- version.py (constants)
- CLI sync stubs (integration scaffolding)

---

## Coverage Impact Analysis

### Current State:
- Total Stmts: 26673
- Missed: 6057 (77% coverage)
- Target: 85% = ~3900 missed stmts

### Gap to 85%:
- Need to cover: ~2157 additional statements (6057 - 3900)

### Tier 1 Priority Impact (if all reach 85%):
- **SyncStateManager:** 68 → ~19 = **49 statements**
- **SyncChangeComputer:** 23 → ~7 = **16 statements**
- **SyncConflictDetector:** 15 → ~4 = **11 statements**
- **SyncMetadataService:** 34 → ~8 = **26 statements**
- **SyncConflictResolver:** 27 → ~2 = **25 statements**
- **Total Tier 1:** ~127 statements covered

### Projected After Tier 1:
- Missed: 6057 - 127 = 5930
- **Coverage: 78%** (still 1227 stmts to 85%)

### Tier 2 Quick Impact (if all 5 reach 85%):
- RemoteIssueCreationService, KeyNormalizer, DataFetch, PlanExecutor, MetadataService
- **Estimated: ~200+ additional statements**
- **Projected Coverage: ~79-80%**

### Further Gains Needed:
- Backend infrastructure (GitHub helpers, etc.) - needed for final 5-6%

---

## Recommendations

### Phase 3 Work (Next):
1. ✅ SyncConflictDetector (9% gap) - Quick win
2. ✅ RemoteIssueCreationService (38% → 85%) - Phase 3 core
3. ✅ SyncMetadataService (60% → 85%) - Phase 3
4. ✅ SyncKeyNormalizer (74% → 85%) - Phase 3

### Phase 4 Work (After):
1. SyncPlanExecutor (66% → 85%)
2. SyncChangeComputer (70% → 85%) - Already 70%, easier than SyncStateManager
3. Further SyncStateManager work if needed

### What NOT to Test:
- `settings.py` (exclude from coverage)
- `version.py` (exclude from coverage)
- CLI stubs (already thin)
- Configuration constants

### Overall Strategy:
**Focus on Tier 1 + Quick Wins first = Realistic path to 85%**
- Tier 1 focused work = 78% coverage
- Tier 2 + infrastructure = 80-82%
- Final polish = 85%
- **Excludions can help with overall % if settings/version removed from calculations**
