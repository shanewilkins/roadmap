# Comprehensive Regex Cleanup Plan

## Executive Summary

Current codebase has 43 regex usages. We need to systematize them while maintaining architecture and avoiding DRY violations. This plan categorizes each pattern and proposes a layered solution.

---

## CATEGORY 1: Output Parsing (Most Brittle - Priority 1)

These parse CLI output to extract data. **High risk of breaking on UI changes.**

### Pattern A: Issue ID Extraction (CRITICAL - 12 occurrences)
**Files affected:**
- `tests/integration/test_cli_commands.py:107,114`
- `tests/integration/test_integration.py:290,297,308,315,326,333,503,511,581`
- `tests/integration/test_view_commands.py:86,93`
- `tests/integration/test_archive_restore_cleanup.py:101,109`
- `tests/unit/domain/test_estimated_time.py:197,203,260,267,281,288`

**Current patterns:**
```python
re.search(r"issue_id=([^\s]+)", line)     # Extract from logs
re.search(r"\[([^\]]+)\]", result.output)  # Extract from brackets [ID]
```

**Risk:** These break when:
- Issue creation output format changes
- Log format changes
- Bracket notation changes to ID display

**Solution:** Create `issue_id_extractor` utility in `CLIOutputParser`

### Pattern B: Project/Milestone ID Extraction (CRITICAL - 1 refactored + similar patterns)
**Files affected:**
- `tests/integration/test_view_commands.py:116-122` (ALREADY REFACTORED)

**Current pattern:** Regex on table output

**Risk:** Breaks when table format changes (which we just did!)

**Solution:** Already migrated to JSON - use as template for others

---

## CATEGORY 2: Validation Patterns (Low Risk - Priority 3)

These validate format/structure, not extracting user data. **Safe to leave.**

### Pattern C: Security Validation Patterns
**Files affected:**
- `tests/security/test_git_integration_and_privacy.py:137,155,189,206,239,266,322,326,358,362,415,479`

**Purpose:** Validate branch names, URLs, SHAs, tokens, etc.

**Risk:** Low - these are intentionally strict validation patterns
**Action:** LEAVE AS-IS - these are security tests, not output parsing

---

## CATEGORY 3: Text Cleaning Utilities (Low Risk - Priority 3)

These normalize/clean text for comparison, not parse output.

### Pattern D: ANSI Code Removal
**Files affected:**
- `tests/unit/shared/test_utils.py:50,54` (in `strip_ansi()`)

**Purpose:** Remove ANSI color codes from output

**Risk:** Low - this is a utility, not parsing
**Action:** LEAVE AS-IS - move to shared utils if not already there

### Pattern E: Whitespace Normalization
**Files affected:**
- `tests/unit/shared/test_utils.py:66,68` (in `normalize_whitespace()`)

**Purpose:** Normalize spaces/newlines

**Risk:** Low - this is a utility function
**Action:** LEAVE AS-IS

---

## CATEGORY 4: Test Helper Methods (Medium Risk - Priority 2)

These are framework methods that need consolidation.

### Pattern F: Regex-based Test Assertions
**Files affected:**
- `tests/fixtures/click_testing.py:100,122,130,144`

**Current methods:**
- `assert_matches_regex(pattern)` - generic regex assertion
- `extract_first_match(pattern)` - extract via regex
- `extract_all_matches(pattern)` - extract all via regex

**Risk:** Medium - these are convenience methods
**Action:** Keep for generic pattern matching, but add JSON-based alternatives

---

## CATEGORY 5: Simple Assertions (Low Risk - Priority 3)

These just check if patterns exist, not parse/extract data.

### Pattern G: Presence Assertions
**Files affected:**
- `tests/integration/test_view_commands.py:232` - `assert re.search(r"\d+/\d+", ...)`
- `tests/integration/test_today_command.py:144` - `assert re.search(r"\d+", ...)`

**Purpose:** Simple pattern existence check

**Risk:** Low - not extracting data
**Action:** Consider replacing with `assert "pattern" in output` for clarity, but not critical

---

## PROPOSED ARCHITECTURE

### Layer 1: Utilities (Non-UI-dependent)
**File:** `tests/common/cli_test_helpers.py`

```
CLIOutputParser:
  ├── extract_json(output) → dict|list
  ├── extract_issue_id(output) → str          [NEW]
  ├── extract_milestone_id(output) → str      [NEW]
  ├── extract_project_id(output) → str        [NEW]
  ├── extract_from_logs(output, key) → str    [NEW - for issue_id=X pattern]
  └── extract_from_brackets(output) → str     [NEW - for [ID] pattern]

TextUtils (already exists in test_utils.py):
  ├── strip_ansi(text)
  └── normalize_whitespace(text)
```

**Key principle:** Only parse to JSON or use domain-level assertions

### Layer 2: Test Fixtures
**File:** `tests/fixtures/click_testing.py`

```
ClickTestResult:
  ├── assert_matches_regex(pattern)     [KEEP - generic]
  ├── extract_json() → dict|list        [NEW - delegate to CLIOutputParser]
  └── get_json_data(key_path) → Any     [NEW - path-based access]

ClickTestHelper:
  ├── extract_table_data()              [REPLACE with JSON-based]
  ├── extract_issue_id()                [NEW - delegate to CLIOutputParser]
  ├── extract_project_id()              [NEW - delegate to CLIOutputParser]
  └── extract_milestone_id()            [NEW - delegate to CLIOutputParser]
```

**Key principle:** Delegate to CLIOutputParser for specific extractions

### Layer 3: Integration Tests
**Files:** All `tests/integration/*.py`

**Usage pattern:**
```python
# Old (brittle):
match = re.search(r"issue_id=([^\s]+)", line)
issue_id = match.group(1)

# New (robust):
issue_id = CLIOutputParser.extract_issue_id(result.output)
# OR
issue_id = ClickTestHelper.extract_issue_id(result.output)
```

---

## IMPLEMENTATION ROADMAP

### Phase 1: Create Consolidated Utilities (High Priority)
1. Expand `tests/common/cli_test_helpers.py` with:
   - `extract_issue_id(output) → str`
   - `extract_milestone_id(output) → str`
   - `extract_project_id(output) → str`
   - `extract_from_logs(output, key) → str`
   - `extract_from_brackets(output) → str`

2. Add tests for each utility function

### Phase 2: Refactor Test Fixtures (Medium Priority)
1. Update `ClickTestHelper` to delegate to `CLIOutputParser`
2. Add `extract_json()` method
3. Update `extract_table_data()` to use JSON when available

### Phase 3: Migrate Integration Tests (High Priority - 12 files)
**Order of migration:**
1. `tests/integration/test_view_commands.py` (11 tests, already partially done)
2. `tests/integration/test_cli_commands.py` (2 tests)
3. `tests/integration/test_integration.py` (8 tests)
4. `tests/integration/test_archive_restore_cleanup.py` (2 tests)
5. `tests/unit/domain/test_estimated_time.py` (8 tests)

### Phase 4: Evaluate Simple Assertions (Low Priority)
1. Replace `re.search()` simple checks with string containment where possible
2. Keep regex for complex patterns

---

## DRY & Separation of Concerns

### Avoiding Duplication
- **Single source of truth:** `CLIOutputParser` is the only place that does output parsing
- **No test-specific logic in utilities:** Only parsing, no test logic
- **Delegate pattern:** Test helpers delegate to utilities

### Maintaining Layer Separation
```
Domain Layer: Tests domain logic directly (no CLI parsing needed)
    ↓
Presentation Layer: ClickTestHelper provides CLI-specific testing utilities
    ↓
Infrastructure Layer: CLIOutputParser handles low-level output parsing
    ↓
Utilities Layer: Text utilities (strip_ansi, normalize_whitespace)
```

### Separation of Concerns
1. **Output parsing** → `CLIOutputParser`
2. **Test framework** → `ClickTestHelper` + `ClickTestResult`
3. **Domain testing** → Direct function/class calls (avoid CLI when possible)
4. **Text utilities** → Shared `test_utils.py`

---

## Success Criteria

✅ All 12 issue ID extraction patterns consolidated into single utility
✅ All table/list parsing uses JSON format (not regex)
✅ No regex duplication across test files
✅ All tests still pass
✅ New tests for parsing utilities
✅ Clear documentation for test authors

---

## Estimated Effort

- Phase 1: 2-3 hours (utilities)
- Phase 2: 1-2 hours (fixtures)
- Phase 3: 3-4 hours (migration)
- Phase 4: 1 hour (evaluation)
- **Total: 7-10 hours**

---

## Risk Assessment

**Low Risk:**
- Utilities are pure functions
- Tests are comprehensive
- Can migrate incrementally

**Mitigation:**
- Test utilities as we build them
- Run full suite after each phase
- Keep old patterns as fallback temporarily
