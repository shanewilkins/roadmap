# Project Cleanup Recommendations

**Generated:** 2025-11-19

## Summary

This document identifies files and directories that can be safely deleted or need attention.

---

## 🗑️ SAFE TO DELETE - High Confidence

### 1. Deprecated/Superseded Modules

#### `roadmap/git_hooks_v2.py` ✅ SAFE
- **Status:** Superseded by `roadmap/infrastructure/git_hooks.py`
- **Imports Found:** Only self-imports (for git hook scripts)
- **Action:** DELETE immediately
- **Command:** `rm roadmap/git_hooks_v2.py`

#### `roadmap/bulk_operations.py` ✅ SAFE
- **Status:** No imports found anywhere in codebase
- **Purpose:** Bulk issue operations (likely experimental or unused)
- **Action:** DELETE
- **Command:** `rm roadmap/bulk_operations.py`

#### `roadmap/data_processing.py` ✅ SAFE
- **Status:** No imports found anywhere in codebase
- **Purpose:** Data processing utilities (likely duplicate of data_utils.py)
- **Action:** DELETE or audit for unique functionality
- **Command:** `rm roadmap/data_processing.py`

### 2. Test Files with Deprecated Content

#### `tests/unit/presentation/test_cli_extended_deprecated.py.skip` ✅ SAFE
- **Status:** Skipped test file (`.skip` extension)
- **Action:** DELETE
- **Command:** `rm tests/unit/presentation/test_cli_extended_deprecated.py.skip`

### 3. Script/Helper Files

#### `fix_imports.py` ⚠️ CONDITIONAL
- **Status:** One-time migration script (already used)
- **Action:** Keep for reference or delete after confirming all imports fixed
- **Decision:** Archive to `scripts/archive/` or delete

#### `fix_test_imports.py` ⚠️ CONDITIONAL
- **Status:** One-time migration script (already used)
- **Action:** Keep for reference or delete after confirming all imports fixed
- **Decision:** Archive to `scripts/archive/` or delete

---

## ⚠️ NEEDS AUDIT - Medium Risk

### 1. `roadmap/models.py`

**Status:** CRITICAL - Imports found in `future/` directory only

**Found Imports:**
- `future/user_management.py` (line 11)
- `future/curation.py` (line 12)
- `future/team_management.py` (line 16)
- `demo-project/demos/comment_demo.py` (line 16)

**Recommendation:**
- These are `future/` features (post-1.0) and demo code
- Main codebase doesn't import `roadmap.models` anymore
- **Action:** Update `future/` imports to use `roadmap.domain` instead
- **Then:** DELETE `roadmap/models.py`

**Migration Commands:**
```bash
# Update future/ imports
sed -i '' 's/from roadmap\.models import/from roadmap.domain import/g' future/*.py
sed -i '' 's/from roadmap import models/from roadmap import domain/g' future/*.py

# Update demo imports
sed -i '' 's/from roadmap\.models import/from roadmap.domain import/g' demo-project/demos/*.py

# Then delete
rm roadmap/models.py
```

### 2. Demo Files

#### `demo-project/demos/_template_demo.py`
- **Status:** Template file with commented-out imports
- **Action:** Update template to use new architecture or delete if not used
- **Decision:** Update comment to reference `roadmap.domain`

---

## 📦 CAN BE ARCHIVED

### 1. Debug/Analysis Scripts (Move to `scripts/archive/`)

- `debug_test.py` (if exists) - One-time debugging
- `fix_imports.py` - Migration complete
- `fix_test_imports.py` - Migration complete
- `curation_demo.json` - Demo data
- `pruning_analysis_report.json` - Analysis output

**Command:**
```bash
mkdir -p scripts/archive
mv fix_imports.py scripts/archive/
mv fix_test_imports.py scripts/archive/
```

### 2. Documentation Files (Optional cleanup)

- `CICD_RECOMMENDATION.md` - Decision made, can archive after implementing
- `test-hooks.md` - May be superseded by updated docs

---

## 🚫 DO NOT DELETE

### Files That Look Old But Are Still Used

1. **`roadmap/parser.py`** - Still actively used for YAML frontmatter
2. **`roadmap/persistence.py`** - Still used for file backup/recovery
3. **`roadmap/timezone_utils.py`** - Imported by 3 service modules
4. **`roadmap/data_utils.py`** - Imported by visualization
5. **`roadmap/progress.py`** - Imported by CLI
6. **`roadmap/file_utils.py`** - Security utilities still in use
7. **`roadmap/security.py`** - Core security functions
8. **`roadmap/credentials.py`** - Credential management
9. **`roadmap/datetime_parser.py`** - Datetime parsing utilities
10. **`roadmap/file_locking.py`** - File locking mechanism
11. **`roadmap/settings.py`** - Configuration constants
12. **`roadmap/version.py`** - Package version
13. **`roadmap/logging.py`** - Logging configuration

---

## 📋 Action Plan

### Phase 1: Immediate Deletions (< 10 minutes)

```bash
# Safe to delete immediately
rm roadmap/git_hooks_v2.py
rm roadmap/bulk_operations.py
rm roadmap/data_processing.py
rm tests/unit/presentation/test_cli_extended_deprecated.py.skip

# Archive migration scripts
mkdir -p scripts/archive
mv fix_imports.py scripts/archive/
mv fix_test_imports.py scripts/archive/
```

### Phase 2: Update Future Features (< 30 minutes)

```bash
# Update future/ imports to use roadmap.domain
find future -name "*.py" -exec sed -i '' 's/from roadmap\.models import/from roadmap.domain import/g' {} +
find demo-project -name "*.py" -exec sed -i '' 's/from roadmap\.models import/from roadmap.domain import/g' {} +

# Verify no more imports
grep -r "from roadmap.models import\|from roadmap import models" .

# Then delete models.py
rm roadmap/models.py
```

### Phase 3: Verify (< 5 minutes)

```bash
# Run tests
poetry run pytest

# Check for import errors
ruff check .

# Verify no broken imports
pyright .
```

---

## 🎯 Expected Results

**Files to Delete:** 6 files
- `roadmap/git_hooks_v2.py`
- `roadmap/bulk_operations.py`
- `roadmap/data_processing.py`
- `roadmap/models.py` (after updating future/ imports)
- `tests/unit/presentation/test_cli_extended_deprecated.py.skip`
- `fix_imports.py` (archived)
- `fix_test_imports.py` (archived)

**Disk Space Saved:** ~50KB of Python code

**Risk Level:** LOW
- All deletions verified via grep search
- No active imports found in main codebase
- Future/ imports can be easily updated

---

## 🔍 Files That Need Investigation

### 1. Potential Duplicates in `roadmap/`

Based on the analysis, check if these have overlapping functionality:
- `file_utils.py` vs `security.py` (both handle file operations)
- `datetime_parser.py` vs `timezone_utils.py` (both handle datetimes)
- `persistence.py` vs `infrastructure/storage/` (both handle persistence)

**Action:** Code review to identify consolidation opportunities

### 2. Unused Test Fixtures

Run this to find unused test fixtures:
```bash
pytest --collect-only 2>&1 | grep "WARN" | grep "fixture"
```

### 3. Pycache and Bytecode

Clean up compiled Python files:
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
```

---

## 📊 Metrics

**Current State:**
- Python files in `roadmap/` root: 18 files
- Files identified for deletion: 6 files
- Files needing migration: 12 files (see ARCHITECTURE_MIGRATION_STATUS.md)

**After Cleanup:**
- Python files in `roadmap/` root: 12 files (33% reduction)
- Better architectural clarity
- Less confusion for new contributors

---

## Next Steps

1. ✅ Review this document
2. ⏳ Execute Phase 1 deletions
3. ⏳ Execute Phase 2 import updates
4. ⏳ Run tests to verify
5. ⏳ Commit changes
6. ⏳ Address files in ARCHITECTURE_MIGRATION_STATUS.md
