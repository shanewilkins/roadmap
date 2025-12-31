# Integration Test Helper Extension Proposal

## Current State

We've refactored 6 integration test files (87 tests total) using `IntegrationTestBase` helpers. However, the helpers currently support a limited subset of CLI parameters:

### IntegrationTestBase.create_issue() Supports:
- `title` (required)
- `description`
- `priority`
- `milestone`
- `assignee`

### IntegrationTestBase.create_milestone() Supports:
- `name` (required)
- `description`
- `due_date`

## Gap Analysis

### Issue Create Command - CLI Supports But Helper Doesn't:
- `--type` (feature, bug, other) - **COMMON in tests**
- `--labels` - used in some tests
- `--estimate` - used in test_cli_issue_commands.py
- `--depends-on` - used in test_cli_issue_commands.py
- `--blocks` - used in test_cli_issue_commands.py
- Git-related: `--git-branch`, `--checkout`, `--branch-name`, `--force`

### Milestone Create Command - CLI Supports But Helper Doesn't:
- `--project` (project ID assignment) - rarely used but available

## Evidence of Gaps in Refactored Tests

1. **test_today_command_expanded.py** (line 54):
   - Collects `_issue_type` parameter but **ignores it** because helper doesn't support `--type`
   - Created workaround: iterate over type but don't use it
   - Impact: Tests don't fully exercise issue type variations

2. **test_cli_issue_commands.py** (line 59):
   - Uses direct CLI invocation: `["--type", "feature", "--priority", "high", "--estimate", "4.5"]`
   - Cannot be refactored to use helper without losing `--type` and `--estimate` coverage
   - Impact: Blocks broader refactoring of test_cli_issue_commands.py

## Unrefactored Tests Still Using --type

Files discovered that still use manual CLI invocations with `--type`:
- `test_overdue_filtering.py` (3 uses)
- `test_git_integration.py` (2 uses)
- `test_archive_restore_lifecycle.py` (1 use)
- `test_view_commands.py` (1 use)
- `test_archive_restore_commands.py` (1 use)
- `test_cli_issue_commands.py` (2 uses)
- `test_git_cli_smoke.py` (2 uses)

**Total: ~12 files with `--type` usage, blocking full refactoring**

## Decision Required

### Option A: Extend Helpers (Recommended)
**Pros:**
- Enables full refactoring of remaining tests (~50+ tests)
- Eliminates workarounds in test_today_command_expanded.py
- Cleaner, more maintainable test setup
- Better documentation of what CLI supports
- Reduces boilerplate across all integration tests (~200+ lines of savings)

**Cons:**
- 30-45 minutes implementation time
- Requires updating helper class
- Need to verify parameter validation

**Scope:**
```python
def create_issue(
    cli_runner: CliRunner,
    title: str,
    description: str = "",
    issue_type: str | None = None,        # ADD
    priority: str | None = None,
    labels: str | None = None,             # ADD
    estimate: float | None = None,         # ADD
    depends_on: list[str] | None = None,  # ADD
    blocks: list[str] | None = None,      # ADD
    milestone: str | None = None,
    assignee: str | None = None,
) -> dict[str, Any]:
    ...
```

### Option B: Accept Current Limitations
**Pros:**
- No immediate work required
- Helpers remain simple and focused

**Cons:**
- Cannot refactor ~50+ remaining tests
- Test coverage gaps (issue_type variations)
- Inconsistent test setup patterns across codebase
- More boilerplate in new tests going forward

## Recommendation

**Extend the helpers now** because:

1. **Minimal effort** for high ROI (enables refactoring 50+ more tests)
2. **Blocks current progress** - we've discovered gaps while refactoring
3. **Already in momentum** - we have the patterns established
4. **Future-proof** - new tests will use proper helpers instead of workarounds
5. **Code quality** - fixes test coverage gaps we've identified

## Next Steps if Approved

1. Extend `IntegrationTestBase.create_issue()` to support: `issue_type`, `labels`, `estimate`, `depends_on`, `blocks`
2. Update `test_today_command_expanded.py` to remove `_issue_type` workaround
3. Update any tests that collected parameters they couldn't use
4. Continue refactoring remaining integration tests with fuller helper support
5. Create follow-up refactoring list for ~50+ remaining tests

## Metrics

**Current State (6 refactored files, 87 tests):**
- Lines saved: ~650
- Coverage: Basic CRUD operations

**If Extended (All files, ~140 tests):**
- Lines saved: ~1200+
- Coverage: Full CLI parameter variations
- Maintenance: Consistent patterns across entire test suite
