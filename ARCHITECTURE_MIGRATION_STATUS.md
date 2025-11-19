# Architecture Migration Status Report

**Generated:** 2025-11-19

## Executive Summary

During the transition to the layered architecture, several modules remain in the root `roadmap/` directory that should be migrated or consolidated. This report analyzes each module and provides migration recommendations.

---

## Modules in Root Directory

### 🔴 Priority: HIGH - Active Usage, Should Be Migrated

#### 1. **timezone_utils.py** (388 lines)
- **Current Usage:** Imported by 3 service modules
  - `roadmap/application/services/issue_service.py`
  - `roadmap/application/services/project_service.py`
  - `roadmap/application/services/milestone_service.py`
- **Purpose:** Timezone handling utilities
- **Recommendation:** Move to `roadmap/shared/timezone_utils.py`
- **Rationale:** Cross-cutting concern used across application layer
- **Migration Impact:** LOW - Only 3 import statements to update

#### 2. **data_utils.py** (568 lines)
- **Current Usage:** Imported by visualization layer
  - `roadmap/application/visualization/charts.py`
- **Purpose:** Data analysis and DataFrame operations
- **Recommendation:** Move to `roadmap/application/data/`
- **Rationale:** Application-layer service for data transformation
- **Migration Impact:** LOW - Single import point

#### 3. **progress.py** (441 lines)
- **Current Usage:** Imported by CLI
  - `roadmap/presentation/cli/progress/recalculate.py`
- **Purpose:** Progress calculation engine
- **Recommendation:** Move to `roadmap/application/services/progress_service.py`
- **Rationale:** Core business logic for progress tracking
- **Migration Impact:** LOW - Single import point

#### 4. **parser.py** (638 lines)
- **Current Usage:** Used throughout codebase
- **Purpose:** Issue/Milestone YAML frontmatter parsing
- **Recommendation:** Move to `roadmap/infrastructure/persistence/`
- **Rationale:** Infrastructure concern for serialization/deserialization
- **Migration Impact:** MEDIUM - Multiple import points

#### 5. **persistence.py** (295 lines)
- **Current Usage:** Enhanced YAML validation and recovery
- **Purpose:** File persistence with backup/recovery
- **Recommendation:** Merge into `roadmap/infrastructure/storage/` or `roadmap/infrastructure/persistence/`
- **Rationale:** Infrastructure layer responsibility
- **Migration Impact:** MEDIUM - Check all import references

### 🟡 Priority: MEDIUM - Utility Modules

#### 6. **file_utils.py** (387 lines)
- **Current Usage:** Security-focused file operations
- **Purpose:** Secure file I/O wrapper functions
- **Recommendation:** Consolidate with `security.py` or move to `roadmap/shared/file_operations.py`
- **Rationale:** Cross-cutting utility
- **Migration Impact:** MEDIUM - Many potential consumers

#### 7. **file_locking.py** (357 lines)
- **Current Usage:** File-based locking mechanism
- **Purpose:** Prevent concurrent file modification
- **Recommendation:** Move to `roadmap/infrastructure/storage/locking.py`
- **Rationale:** Infrastructure concern for data consistency
- **Migration Impact:** LOW - Likely few import points

#### 8. **security.py** (312 lines)
- **Current Usage:** Security utilities (path validation, permissions)
- **Purpose:** Security primitives
- **Recommendation:** Move to `roadmap/shared/security/`
- **Rationale:** Cross-cutting security concern
- **Migration Impact:** MEDIUM - Check all security-related imports

#### 9. **datetime_parser.py** (235 lines)
- **Current Usage:** Parse various datetime formats
- **Purpose:** Flexible datetime parsing
- **Recommendation:** Merge into `timezone_utils.py` or move to `roadmap/shared/datetime/`
- **Rationale:** Related to timezone handling
- **Migration Impact:** LOW - Likely absorbed by timezone_utils

### 🟢 Priority: LOW - Configuration/Metadata

#### 10. **settings.py** (117 lines)
- **Purpose:** Application settings/config constants
- **Recommendation:** Keep in root or move to `roadmap/config.py`
- **Rationale:** Top-level config is acceptable in root
- **Migration Impact:** NONE - Can stay where it is

#### 11. **version.py** (3 lines)
- **Purpose:** Version string constant
- **Recommendation:** Keep in root
- **Rationale:** Standard Python package convention
- **Migration Impact:** NONE

#### 12. **models.py** (DEPRECATED)
- **Current Usage:** Legacy model definitions
- **Purpose:** Old domain models before refactor
- **Recommendation:** **DELETE** - Replaced by `roadmap/domain/`
- **Rationale:** Superseded by layered architecture
- **Migration Impact:** HIGH - Requires full audit to ensure no lingering imports

#### 13. **logging.py** (DEPRECATED?)
- **Purpose:** Logging configuration
- **Recommendation:** Move to `roadmap/shared/logging.py` or delete if unused
- **Rationale:** Cross-cutting concern
- **Migration Impact:** LOW

### ⚫ Priority: DELETE - Deprecated/Duplicate

#### 14. **git_hooks_v2.py**
- **Status:** DEPRECATED
- **Replacement:** `roadmap/infrastructure/git_hooks.py` (just restored)
- **Recommendation:** **DELETE** immediately
- **Rationale:** Superseded by new implementation
- **Migration Impact:** NONE - No imports found

#### 15. **bulk_operations.py**
- **Purpose:** Bulk issue operations
- **Recommendation:** Audit for usage, then either:
  - Move to `roadmap/application/services/bulk_service.py` if used
  - **DELETE** if unused
- **Rationale:** Application layer service if needed
- **Migration Impact:** Unknown - needs usage audit

#### 16. **data_processing.py**
- **Purpose:** Similar to data_utils?
- **Recommendation:** Audit for duplication with `data_utils.py`
  - Merge into `data_utils.py` or delete if redundant
- **Rationale:** Avoid duplicate functionality
- **Migration Impact:** Unknown - needs audit

#### 17. **credentials.py**
- **Purpose:** Credential management (keyring integration)
- **Recommendation:** Move to `roadmap/infrastructure/credentials/`
- **Rationale:** Infrastructure concern
- **Migration Impact:** MEDIUM - Check all auth-related imports

---

## Migration Priority Matrix

| Priority | Module | Action | Est. Effort | Blocker Risk |
|----------|--------|--------|-------------|--------------|
| **P0** | `git_hooks_v2.py` | DELETE | 5 min | None |
| **P0** | `models.py` | DELETE/Audit | 30 min | HIGH (lingering imports?) |
| **P1** | `timezone_utils.py` | Move to `shared/` | 15 min | LOW |
| **P1** | `progress.py` | Move to `application/services/` | 20 min | LOW |
| **P1** | `data_utils.py` | Move to `application/data/` | 15 min | LOW |
| **P2** | `parser.py` | Move to `infrastructure/persistence/` | 45 min | MEDIUM |
| **P2** | `persistence.py` | Merge into `infrastructure/storage/` | 30 min | MEDIUM |
| **P2** | `file_utils.py` | Move to `shared/file_operations.py` | 30 min | MEDIUM |
| **P2** | `security.py` | Move to `shared/security/` | 30 min | MEDIUM |
| **P3** | `file_locking.py` | Move to `infrastructure/storage/` | 20 min | LOW |
| **P3** | `datetime_parser.py` | Merge into `timezone_utils.py` | 20 min | LOW |
| **P3** | `credentials.py` | Move to `infrastructure/credentials/` | 25 min | MEDIUM |
| **P3** | `bulk_operations.py` | Audit/Delete or Move | TBD | LOW |
| **P3** | `data_processing.py` | Audit/Merge or Delete | TBD | LOW |
| **P3** | `logging.py` | Move to `shared/` or delete | 10 min | LOW |
| **P4** | `settings.py` | Keep or rename to `config.py` | 5 min | NONE |
| **P4** | `version.py` | Keep | 0 min | NONE |

---

## Why These Weren't Migrated Initially

Based on the architecture documentation review, these modules were likely left behind because:

1. **Cross-cutting Concerns:** `file_utils`, `security`, `timezone_utils` are used across multiple layers
2. **Utility Nature:** Easy to delay as they don't define core domain logic
3. **Low Coupling:** Most don't directly depend on core domain models
4. **Legacy Compatibility:** May have been left to avoid breaking existing imports
5. **Incomplete Refactor:** Migration stopped before reaching infrastructure/shared layers

---

## Recommended Migration Path

### Phase 1: Cleanup (< 1 hour)
1. Delete `git_hooks_v2.py` (immediate)
2. Audit and delete/migrate `models.py` (requires careful search)
3. Audit `bulk_operations.py` and `data_processing.py`

### Phase 2: Quick Wins (< 2 hours)
1. Move `timezone_utils.py` to `shared/`
2. Move `progress.py` to `application/services/`
3. Move `data_utils.py` to `application/data/`

### Phase 3: Infrastructure Migration (< 3 hours)
1. Move `parser.py` to `infrastructure/persistence/`
2. Merge `persistence.py` into `infrastructure/storage/`
3. Move `file_locking.py` to `infrastructure/storage/`
4. Move `credentials.py` to `infrastructure/credentials/`

### Phase 4: Shared Utilities (< 2 hours)
1. Move `file_utils.py` to `shared/file_operations.py`
2. Move `security.py` to `shared/security/`
3. Merge `datetime_parser.py` into `timezone_utils.py`
4. Move or delete `logging.py`

---

## Import Update Strategy

For each migration, use this pattern:

```python
# Before
from roadmap.timezone_utils import now_utc

# After
from roadmap.shared.timezone_utils import now_utc
```

**Automation:** Can use `sed` or `ruff` to batch-update imports:
```bash
# Example for timezone_utils
find . -name "*.py" -exec sed -i '' 's/from roadmap\.timezone_utils/from roadmap.shared.timezone_utils/g' {} +
```

---

## Testing Strategy

After each migration:
1. Run full test suite: `poetry run pytest`
2. Check for import errors: `ruff check .`
3. Verify type hints: `pyright .`
4. Run affected module's tests specifically

---

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking imports in `future/` modules | Accept for now - future features not priority |
| Circular imports introduced | Review dependency graph before moving |
| Lost functionality | Git history preserves all code |
| Test failures | Fix incrementally, one module at a time |

---

## Next Steps

1. **Immediate:** Delete `git_hooks_v2.py` (safe, no imports found)
2. **Today:** Audit `models.py` for lingering imports and remove
3. **This Week:** Complete Phase 1 + Phase 2 migrations
4. **Next Sprint:** Complete Phase 3 + Phase 4 if time permits

---

## Files to Delete (Candidate List)

Files that appear to be duplicates, deprecated, or unused:

1. **git_hooks_v2.py** - Replaced by `roadmap/infrastructure/git_hooks.py`
2. **models.py** - Replaced by `roadmap/domain/` modules
3. **Possibly:**
   - `bulk_operations.py` (if unused)
   - `data_processing.py` (if duplicate of data_utils.py)
   - `logging.py` (if replaced by shared/logging)

**Action:** Search codebase for imports before deleting:
```bash
grep -r "from roadmap.models import\|from roadmap import models" .
grep -r "from roadmap.git_hooks_v2 import" .
grep -r "from roadmap.bulk_operations import" .
```
