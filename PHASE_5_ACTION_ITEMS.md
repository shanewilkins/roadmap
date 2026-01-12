# Phase 5 - Immediate Action Items

## URGENT: Import Updates Required (Before Tests Pass)

The following 20 files must update their imports to make tests pass:

### Priority 1: Test Files (14 files to update)

```
1. tests/unit/core/services/validators/test_health_status_utils.py
   Line 5: from roadmap.core.services.base_validator import HealthStatus
   Change to: from roadmap.core.services.validator_base import HealthStatus

2. tests/unit/core/services/validators/test_archivable_milestones_validator.py
   Line 8: from roadmap.core.services.base_validator import HealthStatus
   Change to: from roadmap.core.services.validator_base import HealthStatus

3. tests/unit/core/services/validators/test_orphaned_milestones_validator.py
   Line 5: from roadmap.core.services.base_validator import HealthStatus
   Change to: from roadmap.core.services.validator_base import HealthStatus

4. tests/unit/core/services/validators/test_orphaned_issues_validator.py
   Line 7: from roadmap.core.services.base_validator import HealthStatus
   Change to: from roadmap.core.services.validator_base import HealthStatus

5. tests/unit/core/services/validators/test_folder_structure_validator_root.py
   Line 9: from roadmap.core.services.base_validator import HealthStatus
   Change to: from roadmap.core.services.validator_base import HealthStatus

6. tests/unit/core/services/validators/test_archivable_issues_validator.py
   Line 8: from roadmap.core.services.base_validator import HealthStatus
   Change to: from roadmap.core.services.validator_base import HealthStatus

7. tests/unit/core/services/validators/test_duplicate_milestones_validator.py
   Line 5: from roadmap.core.services.base_validator import HealthStatus
   Change to: from roadmap.core.services.validator_base import HealthStatus

8. tests/unit/core/services/validators/test_data_integrity_validator.py
   Line 9: from roadmap.core.services.base_validator import HealthStatus
   Change to: from roadmap.core.services.validator_base import HealthStatus

9. tests/unit/core/services/validators/test_duplicate_issues_validator.py
   Line 5: from roadmap.core.services.base_validator import HealthStatus
   Change to: from roadmap.core.services.validator_base import HealthStatus

10. tests/unit/core/test_backup_validator_errors.py
    Lines 226, 243, 258, 272, 290: from roadmap.core.services.base_validator import HealthStatus
    Change all to: from roadmap.core.services.validator_base import HealthStatus
```

### Priority 2: Source Files (6 files to update)

```
11. roadmap/core/services/data_integrity_validator_service.py
    Line 8: from roadmap.core.services.base_validator import HealthStatus
    Change to: from roadmap.core.services.validator_base import HealthStatus

12. roadmap/core/services/validators/duplicate_issues_validator.py
    Line 6: from roadmap.core.services.base_validator import BaseValidator, HealthStatus
    Change to: from roadmap.core.services.validator_base import BaseValidator, HealthStatus

13. roadmap/core/services/validators/data_integrity_validator.py
    Line 6: from roadmap.core.services.base_validator import HealthStatus
    Change to: from roadmap.core.services.validator_base import HealthStatus

14. roadmap/core/services/validators/archivable_issues_validator.py
    Line 5: from roadmap.core.services.base_validator import HealthStatus
    Change to: from roadmap.core.services.validator_base import HealthStatus

15. roadmap/core/services/validators/folder_structure_validator.py
    Line 6: from roadmap.core.services.base_validator import BaseValidator, HealthStatus
    Change to: from roadmap.core.services.validator_base import BaseValidator, HealthStatus

16. roadmap/core/services/validators/orphaned_issues_validator.py
    Line 7: from roadmap.core.services.base_validator import HealthStatus
    Change to: from roadmap.core.services.validator_base import HealthStatus

17. roadmap/core/services/validators/backup_validator.py
    Line 69 (in docstring): from roadmap.core.services.base_validator import HealthStatus
    Change to: from roadmap.core.services.validator_base import HealthStatus
```

## Quick Fix Script (Copy & Paste)

```bash
# Update all test files
sed -i '' 's/from roadmap\.core\.services\.base_validator import/from roadmap.core.services.validator_base import/g' \
  tests/unit/core/services/validators/*.py \
  tests/unit/core/test_backup_validator_errors.py

# Update all source files
sed -i '' 's/from roadmap\.core\.services\.base_validator import/from roadmap.core.services.validator_base import/g' \
  roadmap/core/services/data_integrity_validator_service.py \
  roadmap/core/services/validators/*.py
```

## Verification Command

After updates, verify all imports are fixed:

```bash
grep -r "from roadmap.core.services.base_validator import" --include="*.py" roadmap tests || echo "✅ All imports updated!"
```

## Post-Update Steps

1. **Run Tests**
   ```bash
   poetry run pytest
   ```
   Expected: 1928+ tests passing, only pre-existing 6 failures

2. **Verify No Regressions**
   - All test counts should match pre-refactoring
   - No new failures introduced

3. **Check Import Success**
   ```bash
   poetry run pytest -k "health_status" -v
   ```
   Should show tests passing with validator_base imports

## Files Created (Don't Delete Old Ones Yet!)

These are NEW files created during Stage 1:
- ✅ `roadmap/core/services/status_change_service.py`
- ✅ `roadmap/core/services/issue_filter_service.py`
- ✅ `roadmap/core/services/validator_base.py`

These are STILL NEEDED for backward compatibility:
- `roadmap/core/services/base_validator.py` (keep for now)
- `roadmap/core/services/helpers/` directory (keep for backward compat)
- `roadmap/core/services/issue_helpers/` directory (keep for backward compat)

## Phase 5 Stage 1 Completion Checklist

- [x] Create status_change_service.py
- [x] Create issue_filter_service.py
- [x] Create validator_base.py
- [x] Update core/services/__init__.py with exports
- [x] Update helpers/__init__.py for re-exports
- [x] Update issue_helpers/__init__.py for re-exports
- [ ] Update 20 import statements in validators/tests
- [ ] Run full test suite and verify passing
- [ ] Confirm backward compatibility works

## Stage 1 Completion Verification

Run this to verify Stage 1 is complete:

```bash
# 1. Check all new files exist
test -f roadmap/core/services/status_change_service.py && echo "✅ status_change_service.py" || echo "❌ status_change_service.py"
test -f roadmap/core/services/issue_filter_service.py && echo "✅ issue_filter_service.py" || echo "❌ issue_filter_service.py"
test -f roadmap/core/services/validator_base.py && echo "✅ validator_base.py" || echo "❌ validator_base.py"

# 2. Check re-exports are in place
grep "status_change_service" roadmap/core/services/__init__.py && echo "✅ status_change_service exported" || echo "❌"
grep "issue_filter_service" roadmap/core/services/__init__.py && echo "✅ issue_filter_service exported" || echo "❌"

# 3. Check imports are updated
! grep "from roadmap.core.services.base_validator import" roadmap tests -r && echo "✅ All imports updated" || echo "⚠️ Updates needed"

# 4. Run tests
poetry run pytest --tb=short
```

## Next Phase After This

Once these imports are updated and tests pass:
1. Move to Phase 5 Stage 2 (reorganize core/services)
2. See `PHASE_5_REFACTORING_PLAN.md` for detailed Stage 2 plan
3. Expect similar approach: move files, update imports, test

## Time Estimate

- Update imports: 5 minutes
- Run tests: 2-3 minutes
- Verify: 2 minutes
- **Total: ~10 minutes to complete Stage 1**
