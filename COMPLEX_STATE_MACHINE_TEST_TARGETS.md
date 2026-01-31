# Complex State-Machine Functions Requiring High-Quality Tests

## Summary
Identified 3 complex state-machine functions beyond SyncStateManager that need high-quality field-level tests:

---

## 1. **ThreeWayMerger** (Core sync logic)
**Location:** `roadmap/core/services/sync/three_way_merger.py`

**Complexity:** HIGH - Core algorithm for intelligent conflict detection
- **Input:** 3 versions of each field (base, local, remote)
- **Logic:** Compares all three to determine if conflict exists
- **Output:** `FieldMergeResult` with status (CLEAN/CONFLICT), merged value, reason

**State Transitions:**
- No Change (base=local=remote) → CLEAN
- Only Local Changed (base≠local, base=remote) → CLEAN (take local)
- Only Remote Changed (base=remote, base≠local) → CLEAN (take remote)
- Both Changed Same Way (local=remote≠base) → CLEAN (take either)
- Both Changed Differently (local≠remote, both≠base) → CONFLICT

**Edge Cases:**
- NULL fields (None vs empty string vs missing)
- Type mismatches in comparisons
- Empty lists vs single-element lists
- Timestamp precision in date comparisons

**Current Test Coverage:** 67 tests in `test_three_way_merger.py` (good coverage, but needs field-level validation)

**What's Missing:**
- Explicit field-by-field assertions (not just `is_conflict()` checks)
- Reason field validation (why was decision made?)
- Parametrized scenarios for all state transition combinations
- Edge cases: None handling, empty collections, special values

---

## 2. **ConflictResolver** (Field-level resolution strategy)
**Location:** `roadmap/core/services/sync/conflict_resolver.py`

**Complexity:** MEDIUM-HIGH - Rule-based conflict resolution
- **Input:** field name, base value, local value, remote value
- **Logic:** Maps field to strategy, applies strategy-specific logic
- **Output:** `(resolved_value, is_flagged)` tuple

**Strategies:**
1. **FLAG_FOR_REVIEW** - Return None, mark for manual review
2. **GITHUB_WINS** - Always take remote value
3. **LOCAL_WINS** - Always take local value
4. **MERGE_UNION** - For lists: combine and deduplicate (labels)
5. **MERGE_APPEND** - For text: concatenate with separator (comments)

**Field Rules (RULES dict):**
- Critical: status, assignee, milestone → FLAG_FOR_REVIEW
- Merge-friendly: labels, description, comments
- Metadata: created_at, updated_at → GITHUB_WINS
- Unknown fields → Default to FLAG_FOR_REVIEW

**Edge Cases:**
- Single value vs list value for MERGE_UNION
- Empty strings vs None values
- Mixed type conflicts (string vs number)
- Circular references in append operations

**Current Test Coverage:** 21 tests in `test_conflict_resolver.py` (partial coverage)

**What's Missing:**
- Field-by-field rule validation (not just strategy enum values)
- Parametrized all field+strategy combinations
- Actual resolved value validation (not just flagged status)
- Edge case matrix: null×strategy, type mismatch×strategy
- Merge append: verify separator format, marker placement
- Merge union: verify no duplicates, correct union result

---

## 3. **SyncConflictResolver** (Higher-level resolution orchestrator)
**Location:** `roadmap/core/services/sync/sync_conflict_resolver.py`

**Complexity:** MEDIUM - Orchestrates conflict resolution with multiple strategies
- **Input:** `Conflict` object, strategy choice
- **Logic:** Routes to appropriate handler (KEEP_LOCAL, KEEP_REMOTE, AUTO_MERGE)
- **Output:** Resolved `Issue` object

**Strategies:**
1. **KEEP_LOCAL** - Return local issue unchanged
2. **KEEP_REMOTE** - Convert remote to local format and return
3. **AUTO_MERGE** - Intelligent merge based on timestamps and change detection

**Auto-Merge Logic:**
- If local is newer (updated_ts): keep local
- If remote is newer: keep remote
- If timestamps equal: keep local (tie-breaker)
- If remote has no timestamp: keep local (fallback)

**State Management:**
- Tracks conflict metadata (updated_at, field_names, local_issue, remote_issue)
- Handles batch resolution with error collection
- Converts between remote and local issue formats

**Current Test Coverage:** ~15 tests in sync layer (insufficient for complexity)

**What's Missing:**
- Timestamp comparison field-by-field validation
- Batch operation error handling with partial success
- Strategy routing validation (correct strategy applied)
- Remote→Local conversion integrity
- Conflict field name preservation
- Batch operation: verify error collection without throwing

---

## Recommended High-Quality Test Priorities

### Tier 1 (Critical - Test ASAP)
1. **ConflictResolver** - Direct field mapping with rules; most important to validate
   - Estimated: 40-50 tests (all strategy×field combinations)
   - Value: Validates core merge logic correctness

2. **ThreeWayMerger** - Core algorithm for conflict detection
   - Estimated: 30-40 tests (state transitions, edge cases)
   - Value: Ensures conflicts detected correctly (fewer false positives/negatives)

### Tier 2 (Important - Test after Tier 1)
3. **SyncConflictResolver** - Higher-level orchestration
   - Estimated: 20-25 tests (strategy selection, batch handling)
   - Value: Ensures correct strategies applied to conflicts

---

## Quality Test Pattern Template

```python
def test_resolver_with_field_validation(self):
    """Test that exact field values are resolved correctly."""
    resolver = ConflictResolver()

    # GIVEN: A specific field conflict
    result_value, is_flagged = resolver.resolve_conflict(
        field="labels",
        base=["bug"],
        local=["bug", "urgent"],
        remote=["bug", "feature"],
    )

    # THEN: Verify exact result
    assert set(result_value) == {"bug", "urgent", "feature"}  # Not just != []
    assert is_flagged is False  # Not just boolean
    assert len(result_value) == 3  # Exact count
    assert "bug" in result_value  # All expected values present
```

---

## Implementation Roadmap

1. **Phase 1:** ConflictResolver (40-50 tests)
   - All 5 strategies × all field types
   - Null handling, type mismatches, edge cases
   - Parametrize for coverage

2. **Phase 2:** ThreeWayMerger (30-40 tests)
   - All 4 state transitions + edge cases
   - Reason field validation
   - Parametrized scenarios

3. **Phase 3:** SyncConflictResolver (20-25 tests)
   - Strategy selection routing
   - Batch operation with errors
   - Timestamp comparison logic

**Total: ~100-120 new high-quality tests** ensuring core sync logic is bulletproof.
