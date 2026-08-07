# Global Singleton Audit & Findings

**Date**: January 30, 2026
**Status**: ✅ Analyzed - No Critical Issues Found
**Flakiness Risk**: LOW - All identified singletons properly managed

---

## Executive Summary

Conducted a codebase-wide search for global singleton objects that could cause test flakiness. Found **3 global singletons**, all properly managed with no immediate flakiness risk:

| Singleton | Location | Cleared? | Risk Level |
|-----------|----------|----------|-----------|
| `_session_cache` | [roadmap/common/cache.py](roadmap/common/cache.py#L148) | ✅ Now cleared by autouse fixture | LOW |
| `_tracer` | [roadmap/common/observability/otel_init.py](roadmap/common/observability/otel_init.py#L12) | ✅ Manually cleared in tests | LOW |
| `_profiler` | [roadmap/common/services/profiling.py](roadmap/common/services/profiling.py#L275) | ✅ Has public API | LOW |

---

## Detailed Findings

### 1. Session Cache (`_session_cache`) ⚠️ → ✅ FIXED

**Location**: [roadmap/common/cache.py](roadmap/common/cache.py#L148)

```python
_session_cache = SessionCache()
```

**Issue**: Global singleton persisting between tests → caused flakiness
**Status**: ✅ FIXED with autouse fixture
**Clear Function**: `clear_session_cache()`
**Cleanup Mechanism**: [tests/conftest.py](../tests/conftest.py) - autouse fixture runs before/after each test

**Evidence**: All 6616 tests pass consistently, including previously flaky `test_milestone_assign_invalid_target`

---

### 2. Global Tracer (`_tracer`) ✅ PROPERLY MANAGED

**Location**: [roadmap/common/observability/otel_init.py](roadmap/common/observability/otel_init.py#L12)

```python
_tracer: object | None = None
```

**Status**: ✅ LOW RISK - Tests manually clear before use

**Clear Mechanism**:
```python
# From tests/unit/common/formatters/test_otel_init.py
otel_module._tracer = None  # Clear before each test
```

**Risk Assessment**:
- ✅ Tests explicitly set `_tracer = None` before initialization
- ✅ No autouse fixture needed (tests control initialization)
- ✅ Default value is `None`, so no lingering state
- ✅ Tracing only enabled in specific tests, not by default

**Recommendation**: No action needed - current test pattern is appropriate for this use case

---

### 3. Global Profiler (`_profiler`) ✅ PROPERLY MANAGED

**Location**: [roadmap/common/services/profiling.py](roadmap/common/services/profiling.py#L275)

```python
_profiler = PerformanceProfiler()
```

**Status**: ✅ LOW RISK - Has public clear() method

**Public API**:
```python
def get_profiler() -> PerformanceProfiler:
    """Get the global profiler instance."""
    return _profiler

# PerformanceProfiler class has:
def clear(self) -> None:
    """Clear all recorded operations."""
    ...
```

**Risk Assessment**:
- ✅ Public accessor `get_profiler()`
- ✅ `clear()` method exists on PerformanceProfiler class
- ✅ Tests instantiate fresh PerformanceProfiler() instead of using global
- ✅ Global `_profiler` used for production code only
- ✅ No state leakage observed in 6616 tests

**Recommendation**: No action needed - tests already use independent instances

---

## Search Methodology

### What Was Searched

1. **Pattern 1**: Module-level assignments with session/cache keywords
   ```regex
   ^[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*(?:.*Session|.*Cache|.*Config)
   ```

2. **Pattern 2**: Underscore-prefixed module variables
   ```regex
   ^_[a-zA-Z0-9_]*\s*=
   ```

3. **Pattern 3**: Global state keywords
   ```regex
   \b_cache\b|\b_state\b|\b_store\b|\b_registry\b
   ```

4. **Manual inspection**: OpenTelemetry integration for additional globals

### Files Scanned
- All `roadmap/**/*.py` files
- Focus on `roadmap/common/` for shared utilities
- Infrastructure layers (gateway, observability, services)
- Adapter layers (CLI, persistence, sync)

### Results Summary
- ✅ Found 3 global singletons total
- ✅ All 3 properly managed
- ✅ Zero problematic patterns identified
- ✅ Zero new flakiness risks detected

---

## Current Test Coverage for Singletons

### Session Cache Tests
- **File**: [tests/unit/common/test_cache.py](../../tests/unit/common/test_cache.py)
- **Tests**: Coverage of cache operations, TTL, clear()
- **Validation**: All pass

### Tracer Tests
- **File**: [tests/unit/common/formatters/test_otel_init.py](../../tests/unit/common/formatters/test_otel_init.py)
- **Pattern**: Explicit `_tracer = None` before each test
- **Validation**: All pass

### Profiler Tests
- **File**: [tests/unit/common/test_profiling.py](../../tests/unit/common/test_profiling.py)
- **Pattern**: Fresh instances via `PerformanceProfiler()`
- **Validation**: All pass

---

## Lessons from Cache Singleton Flakiness

### What Worked
1. ✅ **Autouse fixtures** - Automatically clear state before/after ALL tests
2. ✅ **Explicit cleanup** - Don't assume implicit cleanup
3. ✅ **Public API** - Expose `clear_*` functions for cleanup

### What Didn't Work (Before Fix)
1. ❌ **No cleanup mechanism** - `clear_session_cache()` existed but wasn't called
2. ❌ **No autouse fixture** - Tests didn't know they needed cleanup
3. ❌ **Module-level global** - Persisted across entire test process

### Pattern to Apply Going Forward

When introducing a new global singleton:

```python
# DO THIS:
class MyCache:
    def clear(self) -> None:
        """Clear all cached state."""
        ...

_my_cache = MyCache()

def get_cache() -> MyCache:
    return _my_cache

# AND THIS (in tests/conftest.py):
@pytest.fixture(autouse=True)
def clear_my_cache_between_tests():
    from roadmap.common.cache import get_cache
    get_cache().clear()
    yield
    get_cache().clear()
```

---

## Recommendations

### 🟢 No Immediate Action Required
All global singletons are properly managed. Tests pass consistently.

### 🟡 For Future Development

**When adding new global singletons:**

1. **Always provide a clear/reset function**
   ```python
   def reset_my_service() -> None:
       """Reset service state between tests."""
       global _my_service_instance
       _my_service_instance = MyService()
   ```

2. **Add to the test cleanup fixture**
   - Locate [tests/conftest.py](../tests/conftest.py)
   - Add call to your reset function in `clear_session_cache_between_tests()`

3. **Document in TEST_INDEPENDENCE_PATTERNS.md**
   - See [docs/developer_notes/TEST_INDEPENDENCE_PATTERNS.md](../../docs/developer_notes/TEST_INDEPENDENCE_PATTERNS.md)

4. **Test the pattern**
   ```bash
   # Run in isolation
   poetry run pytest tests/path/to/test.py::test_name
   # Should PASS

   # Run in full suite
   poetry run pytest
   # Should PASS and be consistent across multiple runs
   ```

---

## Verification

### Test Suite Status
```
Total Tests: 6616
Passing: 6616
Failing: 0
Skipped: 9
Flakiness: 0 detected (5+ runs each on critical tests)
```

### Specific Flakiness Verification
```bash
# Previously flaky test - 5 consecutive runs
✅ Run 1: PASSED
✅ Run 2: PASSED
✅ Run 3: PASSED
✅ Run 4: PASSED
✅ Run 5: PASSED
```

---

## Related Documentation

- [TEST_INDEPENDENCE_PATTERNS.md](../../docs/developer_notes/TEST_INDEPENDENCE_PATTERNS.md) - Comprehensive patterns guide
- [FLAKINESS_INVESTIGATION_SUMMARY.md](../../docs/developer_notes/FLAKINESS_INVESTIGATION_SUMMARY.md) - Detailed investigation report
- [Cache Implementation](roadmap/common/cache.py) - Session cache design

---

## Conclusion

The codebase has good practices for global singleton management:
- Clear public APIs provided
- Tests use explicit cleanup or independent instances
- No widespread state leakage patterns detected
- Fix applied to the one problematic case (session cache)

**Risk Level: LOW** - All identified singletons are properly managed. Future flakiness is unlikely if the patterns documented in TEST_INDEPENDENCE_PATTERNS.md are followed when new singletons are introduced.
