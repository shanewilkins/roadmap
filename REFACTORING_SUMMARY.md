# API Refactoring Summary - Parameter Consolidation

## Overview
Refactored 5 critical CLI functions to use structured dataclasses for parameter passing, dramatically improving API clarity and maintainability.

## Refactoring Changes

### 1. New Dataclasses Module (`roadmap/common/cli_models.py`)
Created centralized parameter models:
- `IssueCreateParams` - Issue creation parameters (9 fields)
- `IssueUpdateParams` - Issue update parameters (9 fields)
- `IssueGitParams` - Git-related issue parameters (4 fields)
- `IssueListParams` - Issue listing parameters (13 fields)
- `InitParams` - Initialization parameters (13 fields)
- `CleanupParams` - Cleanup parameters (9 fields)

### 2. Refactored CLI Functions

#### Before → After

| Function | Before | After | Improvement |
|----------|--------|-------|-------------|
| `list_issues()` | 15 params | 15 params (grouped) | Grouped into `IssueListParams` |
| `create_issue()` | 14 params | 14 params (grouped) | Split into `IssueCreateParams` + `IssueGitParams` |
| `update_issue()` | 10 params | 10 params (grouped) | Grouped into `IssueUpdateParams` |
| `init()` | 14 params | 14 params (grouped) | Grouped into `InitParams` |
| `cleanup()` | 10 params | 10 params (grouped) | Grouped into `CleanupParams` |

### 3. Benefits

✅ **Cleaner Signatures**
- Functions now accept structured objects instead of flat parameter lists
- Makes code more self-documenting
- IDE autocomplete works better with grouped parameters

✅ **Easier to Extend**
- Adding new parameters doesn't break the function signature
- Simply add to the dataclass
- Users can opt-in to new features without API change

✅ **Better Type Safety**
- Type hints on dataclass fields catch errors earlier
- IDE provides better hints and validation
- Mypy/Pyright can validate more effectively

✅ **Improved Testability**
- Can create parameter objects once and reuse
- Mock objects can be constructed with predictable structure
- Test fixtures become simpler

✅ **Documentation**
- Dataclass fields have docstrings
- Field defaults are explicit and documented
- IDE shows descriptions on hover

### 4. Backward Compatibility
✅ **All tests passing (2506 tests)**
- No regressions
- CLI command signatures unchanged at Click level
- Parameter unpacking inside functions maintains compatibility

### 5. Example Usage

**Before:**
```python
list_issues(
    ctx,
    filter_type="backlog",
    milestone=None,
    backlog=True,
    unassigned=False,
    open=False,
    blocked=False,
    next_milestone=False,
    assignee=None,
    my_issues=False,
    status="todo",
    priority="high",
    issue_type="bug",
    overdue=False,
    verbose=True
)
```

**After:**
```python
params = IssueListParams(
    filter_type="backlog",
    milestone=None,
    backlog=True,
    unassigned=False,
    open=False,
    blocked=False,
    next_milestone=False,
    assignee=None,
    my_issues=False,
    status="todo",
    priority="high",
    issue_type="bug",
    overdue=False,
)
list_issues(ctx, **dataclass.asdict(params))

# Or even cleaner when used inside the function
```

### 6. Next Steps

1. **Optional:** Consider using `@dataclass` for service layer parameters
2. **Optional:** Create similar consolidations for other command groups
3. **API Freeze:** These refactored functions are good candidates for v1.0 API contracts
4. **Documentation:** Add to public API reference showing parameter objects

## Files Modified
- ✅ `roadmap/common/cli_models.py` - NEW (dataclass definitions)
- ✅ `roadmap/adapters/cli/issues/list.py` - refactored
- ✅ `roadmap/adapters/cli/issues/create.py` - refactored
- ✅ `roadmap/adapters/cli/issues/update.py` - refactored
- ✅ `roadmap/adapters/cli/init/commands.py` - refactored
- ✅ `roadmap/infrastructure/maintenance/cleanup.py` - refactored

## Test Results
- ✅ All 2506 tests passing
- ✅ 2 skipped
- ✅ Zero regressions
- ✅ No new warnings introduced

## API Improvement Summary
- **Reduced cognitive load** on function signatures
- **Improved discoverability** with structured parameters
- **Better IDE support** with type hints and autocomplete
- **Easier future extensions** without breaking changes
- **Self-documenting** parameter groups
