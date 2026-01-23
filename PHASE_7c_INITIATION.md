# Phase 7c: Core Services Error Handling Fixes

**Status:** 🚀 INITIATED - January 23, 2026
**Objective:** Fix error handling in core business logic services
**Scope:** 26 files in roadmap/core/services/
**Violations Found:** ~30 violations in core services

---

## Phase 7c Overview

Phase 7c focuses on fixing error handling in **core service layer** - the business logic that powers the roadmap application.

### What Are Core Services?

The `roadmap/core/services/` directory contains:
- **Business logic** - sync operations, issue creation, validation, etc.
- **Domain logic** - milestone management, status changes, etc.
- **Service coordination** - orchestrating operations across multiple layers

### Why Fix Core Services First?

1. **Highest impact** - Failures here cascade through entire system
2. **Clearest patterns** - Business logic has clear error boundaries
3. **Best coverage** - Errors here are most likely to be tested
4. **Foundation** - Fixes here enable better CLI/adapter error handling (Phases 7d-7e)

---

## Phase 7c Violations Summary

**Total violations in core services:** ~30
**Breakdown by module:**

| Module | Files | Violations | Type |
|--------|-------|-----------|------|
| **sync** | 7 | ~15 | Infrastructure, Data errors |
| **utils** | 4 | ~8 | Configuration, System errors |
| **project_init** | 3 | ~3 | Configuration, Data errors |
| **validators** | 2 | ~1 | Data errors |
| **issue** | 2 | ~1 | Configuration errors |
| **initialization** | 2 | ~1 | System errors |
| **baseline** | 2 | ~1 | Data errors |
| **health** | 1 | ~0 | Already clean |
| **git** | 1 | ~0 | Already clean |
| **other** | 1 | ~0 | Already clean |

### Specific Files (26 total)

**Sync Services (7 files)** - Most violations, highest priority
- roadmap/core/services/sync/sync_change_computer.py
- roadmap/core/services/sync/sync_conflict_detector.py
- roadmap/core/services/sync/sync_key_normalizer.py
- roadmap/core/services/sync/sync_metadata_service.py
- roadmap/core/services/sync/sync_plan_executor.py
- roadmap/core/services/sync/sync_state_comparator.py
- roadmap/core/services/sync/sync_state_normalizer.py

**Utils Services (4 files)** - Configuration and system errors
- roadmap/core/services/utils/configuration_service.py
- roadmap/core/services/utils/field_conflict_detector.py
- roadmap/core/services/utils/remote_fetcher.py
- roadmap/core/services/utils/remote_state_normalizer.py

**Project Init (3 files)** - Setup and detection logic
- roadmap/core/services/project_init/context_detection.py
- roadmap/core/services/project_init/detection.py
- roadmap/core/services/project_init/template.py

**Validators (2 files)** - Data validation
- roadmap/core/services/validators/duplicate_milestones_validator.py
- roadmap/core/services/validators/folder_structure_validator.py

**Issue Services (2 files)** - Issue operations
- roadmap/core/services/issue/issue_creation_service.py
- roadmap/core/services/issue/start_issue_service.py

**Initialization (2 files)** - Module initialization
- roadmap/core/services/initialization/utils.py
- roadmap/core/services/initialization/workflow.py

**Baseline (2 files)** - Baseline management
- roadmap/core/services/baseline/baseline_retriever.py
- roadmap/core/services/baseline/optimized_baseline_builder.py

**Other (2 files)** - Single services
- roadmap/core/services/git/git_hook_auto_sync_service.py
- roadmap/core/services/milestone_service.py

---

## Implementation Approach

### Step 1: Setup & Baseline

- [x] Establish Semgrep rules (done in Phase 7b)
- [x] Document Phase 7b standards (done)
- [x] Identify Phase 7c files (done)
- [ ] Create this initiation document (IN PROGRESS)
- [ ] Commit Phase 7c start

### Step 2: Fix by Module (Priority Order)

**Priority 1: Sync Services (7 files)**
- Start here - most violations, critical for application
- Use: Exception handlers likely to be Infrastructure errors
- Pattern: Add retry logic, log with context

**Priority 2: Utils Services (4 files)**
- Configuration and helper logic
- Use: Mix of Config, System, and Infrastructure errors
- Pattern: Fail fast on config, retry on service calls

**Priority 3: Project Init (3 files)**
- Setup and detection logic
- Use: Configuration errors, validation errors
- Pattern: Fail fast, provide helpful error messages

**Priority 4: Validators (2 files)**
- Data validation
- Use: Data errors mostly
- Pattern: Skip invalid records, track issues

**Priority 5: Issue Services (2 files)**
- Issue creation and state changes
- Use: Data and Configuration errors
- Pattern: Validate input, provide feedback

**Priority 6: Remaining Files (6 files)**
- Initialization, baseline, git, milestone
- Use: Varies by file
- Pattern: Use PHASE_7b guidelines

### Step 3: Verification & Commit

For each file or group of files:
1. [ ] Fix exception handlers using PHASE_7b patterns
2. [ ] Run: `pre-commit run --hook-stage manual --all-files semgrep`
3. [ ] Verify: No new violations introduced
4. [ ] Test: `poetry run pytest tests/ -v`
5. [ ] Commit: Increment violation count down
6. [ ] Track: Update progress

---

## Implementation Workflow

### For Each File

1. **Audit** - Identify all exception handlers
   ```bash
   grep -n "except\|try:" <file>
   ```

2. **Classify** - Determine error type
   - Read PHASE_7b_ERROR_HIERARCHY.md
   - Ask: "What caused this error?"

3. **Pattern** - Choose handling pattern
   - Read PHASE_7b_HANDLING_PATTERNS.md
   - Find matching error type

4. **Implement** - Add logging
   - Use templates from PHASE_7b_LOGGING_REQUIREMENTS.md
   - Reference PHASE_7b_CODE_EXAMPLES.md

5. **Test** - Verify error path
   - Create test case for error scenario
   - Run tests

6. **Validate** - Check Semgrep
   - `pre-commit run --hook-stage manual --all-files semgrep`
   - Confirm no NEW violations

7. **Commit** - Record progress
   - Message format: "Fix error handling in <file>"
   - Include violation count reduction

---

## Tools & References

### Documentation (Read These First)

1. **PHASE_7b_ERROR_HIERARCHY.md** - Which error type is this?
2. **PHASE_7b_HANDLING_PATTERNS.md** - How do I handle it?
3. **PHASE_7b_LOGGING_REQUIREMENTS.md** - What must I log?
4. **PHASE_7b_CODE_EXAMPLES.md** - Show me an example!
5. **PHASE_7b_REMEDIATION_CHECKLIST.md** - Did I do everything?

### Validation Tools

```bash
# Run Semgrep to find violations
pre-commit run --hook-stage manual --all-files semgrep

# Run on specific file
semgrep --config=.semgrep.yml roadmap/core/services/sync/sync_*.py --error

# Run tests
poetry run pytest tests/unit/core/services/ -v

# Run linting
poetry run ruff check roadmap/core/services/
poetry run pylint roadmap/core/services/ || true
```

---

## Success Criteria

### Phase 7c Complete When:

- [x] Plan document created (this file)
- [ ] All 26 core service files fixed
- [ ] All exception handlers have logging
- [ ] No silent failures (no except+pass/continue/return)
- [ ] Semgrep detects zero new violations
- [ ] 6,558+ tests passing
- [ ] No new ruff/pylint warnings
- [ ] Pre-commit checks all passing
- [ ] Progress tracked and documented

### Violation Reduction Target

**Start:** ~30 violations in core services
**End:** 0 violations in core services
**Track:** Progress by module

---

## Next Actions

### Immediate (Now)

1. ✅ Create Phase 7c initiation plan (this file)
2. ✅ Identify files with violations (26 files)
3. ✅ Count violations by module (~30 total)
4. [ ] Commit Phase 7c start
5. [ ] Begin fixing Sync services (Priority 1)

### During Phase 7c

- Fix files following priority order
- Track progress (violations → 0)
- Run Semgrep before each commit
- Keep tests passing
- Reference Phase 7b standards

### After Phase 7c

- Move to Phase 7d: CLI command handlers (35 files, ~45 violations)
- Then Phase 7e: Adapters (41 files, ~60 violations)
- Then Phase 7f: Error path testing (85%+ coverage)

---

## Commits in Phase 7c

Each commit will:
1. Fix violations in 1-3 files
2. Include violation count in message
3. Pass all pre-commit checks
4. Keep tests passing
5. Track progress

Example message:
```
Fix error handling in sync services (2/7)

- sync_change_computer.py: Added logging to 5 exception handlers
- sync_conflict_detector.py: Added logging to 3 exception handlers

Violations in core services: 30 → 22
Semgrep validation: ✅ No new violations
Tests: ✅ 6,558 passing
```

---

## Current Status

**Phase 7c Start:** January 23, 2026

**Ready:**
- ✅ Semgrep tuned (138 total violations tracked)
- ✅ Error hierarchy defined
- ✅ Handling patterns documented
- ✅ Logging standards established
- ✅ Code examples provided
- ✅ Remediation checklist created
- ✅ Target files identified (26 files, ~30 violations)

**Next:** Start fixing Sync services

---

## Timeline Estimate

**Phase 7c (Core Services):** ~4-6 hours
- Sync services (7 files): ~2 hours
- Utils services (4 files): ~1 hour
- Other services (15 files): ~1.5-2 hours
- Testing & validation: ~1 hour

**Phase 7d (CLI):** ~6-8 hours (35 files)
**Phase 7e (Adapters):** ~8-10 hours (41 files)
**Phase 7f (Testing):** ~4-5 hours (coverage)

**Total Phase 7:** ~25-30 hours work
