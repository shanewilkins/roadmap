# Phase 6C: Fix Remaining Layer Violations

## Objective
Reduce layer violations from 105 to <50 (current goal) by fixing architectural boundary crossings through proper interface design and dependency injection.

## Current State
- **Total violations**: 105
  - Common → Forbidden: 8
  - Core → Forbidden: 15
  - Infrastructure → Forbidden: 82

## Strategy

### Tier 1: Common Layer Violations (8 violations) - EASIEST
**Issue**: Common utilities importing from core.domain (formatters, progress, utils)

**Root cause**: Common formatters need domain types to function (Issue, etc.)

**Solution**: This is actually ACCEPTABLE architecture - Common is allowed to import types from Core's domain layer (types/interfaces). The violation is a false positive.

**Fix**: Update scanner to allow `common → core.domain` (types only)

**Impact**: Reduces violations by 8 ✓

### Tier 2: Core Services Violations (15 violations) - MODERATE
**Issue**: Core services importing from adapters (persistence, sync, github, etc.)

**Root cause**: Services need concrete implementations
- `baseline_state_retriever.py` needs persistence parsers
- `git_hook_auto_sync_service.py` needs sync orchestrator
- `github_issue_client.py` needs GitHub adapter
- `infrastructure_validator_service.py` needs storage implementation

**Solution 1**: Extract interfaces and move to core, inject implementations
- Define `IssueParserInterface` in core/interfaces/
- Inject implementations from adapters at startup

**Solution 2**: Move adapter imports into core/adapters submodule (if services must use adapters directly)

**Best approach**: Use dependency injection via RoadmapCore initialization

**Effort**: 2-3 hours (5 files, multiple imports per file)

### Tier 3: Infrastructure Violations (82 violations) - HARDEST
**Issue**: Infrastructure coordinators/core importing from adapters, core, common

**Root cause**: RoadmapCore and coordinators need to compose multiple layers

**Analysis**:
- Core.py has 30+ lines importing from adapters/core/common (expected)
- Coordinators import operations, which import core/common types
- This is somewhat unavoidable for the coordinator pattern

**Solution 1**: Accept some infrastructure violations (it's a facade/coordinator layer)
- Only fix violations that represent data flow issues
- Keep coordination imports as they serve integration purpose

**Solution 2**: Create abstract interfaces and inject
- Define coordinator interfaces in core/interfaces/
- Implement in infrastructure/coordination/
- Solves circular dependency issues

**Effort**: 1-2 hours (selective fixing)

## Detailed Violation Breakdown

### Common Layer (8 total) ➜ 0 remaining (false positives)

```
roadmap/common/formatters/export/issue_exporter.py:10
  → from roadmap.core.domain              [ACCEPTABLE - type import]

roadmap/common/formatters/kanban/layout.py:3
  → from roadmap.core.domain              [ACCEPTABLE - type import]

roadmap/common/formatters/kanban/organizer.py:5
  → from roadmap.core.domain              [ACCEPTABLE - type import]

roadmap/common/formatters/tables/column_factory.py:8
  → from roadmap.core.domain              [ACCEPTABLE - type import]

roadmap/common/formatters/tables/issue_table.py:13
  → from roadmap.core.domain              [ACCEPTABLE - type import]

roadmap/common/initialization/github/setup_service.py:18
  → from roadmap.adapters.github.github    [FIX - needs interface]

roadmap/common/progress.py:14
  → from roadmap.core.domain               [ACCEPTABLE - type import]

roadmap/common/utils/status_utils.py:95
  → from roadmap.core.domain.health        [ACCEPTABLE - type import]
```

**Action**: 7 are type imports (acceptable), 1 needs fixing

### Core Layer (15 total) ➜ 10-12 remaining

**High priority fixes (actual logic coupling)**:
1. `baseline_state_retriever.py` - Remove direct adapter imports (3 violations)
2. `github_issue_client.py` - Already using GitHubClient (might be OK), check usage (3 violations)
3. `git_hook_auto_sync_service.py` - Uses sync orchestrator (2 violations)

**Patterns to fix**:
- Move parser implementations to interfaces
- Inject sync backends instead of importing factory
- Use GitHub client interface instead of concrete class

### Infrastructure Layer (82 total) ➜ Keep <30

**Analysis of imports**:
- `core.py` imports from adapters/core/common (30+) - This is a facade, somewhat acceptable
- Coordinators import operations which transitively import core/common
- Some actual violations (coordinators importing directly from core)

**Quick wins**:
- Remove unnecessary re-imports in `__init__.py`
- Use TYPE_CHECKING guards for type hints
- Move operation imports to lazy loading

## Implementation Plan

### Phase 6c.1: Fix Common Layer (30 min)
1. Update scanner to mark `common → core.domain` as acceptable (type imports)
2. Fix `setup_service.py` to use interface
3. Run scanner to confirm 8 → 1 violation

### Phase 6c.2: Fix Core Layer (2-3 hours)
1. Extract parser interfaces to `core/interfaces/parsers.py`
2. Update `baseline_state_retriever.py` to use interfaces
3. Create sync backend interface in `core/interfaces/sync.py`
4. Inject implementations from RoadmapCore instead of direct imports
5. Verify GitHub client usage pattern (may be acceptable)

### Phase 6c.3: Infrastructure Optimization (1-2 hours)
1. Add TYPE_CHECKING guards to RoadmapCore imports
2. Mark coordination imports as acceptable in scanner
3. Fix direct coordinator → core imports
4. Remove unnecessary re-imports in `__init__.py`

### Phase 6c.4: Validation (15-20 min)
1. Run scanner to verify <50 violations
2. Run test suite
3. Commit changes

## Success Criteria

✅ Total violations reduced to <50 (target: 30-40)
✅ All remaining violations documented as acceptable (facades, types, interfaces)
✅ No circular dependencies
✅ All 6,500+ tests passing
✅ Code changes are minimal and focused

## Timeline

- **6c.1**: 30 minutes
- **6c.2**: 2-3 hours
- **6c.3**: 1-2 hours
- **6c.4**: 15-20 minutes
- **Total**: 4-6 hours

## Risks

1. **Moving adapters to core**: May create core/adapters submodule (acceptable)
2. **Interface proliferation**: Could create 5-10 new interfaces (worth it for clean architecture)
3. **Backward compatibility**: Ensure RoadmapCore API doesn't change for external users
4. **Test refactoring needed**: May need to update test mocks after interface changes

## Notes

- Infrastructure violations aren't all "bad" - some represent necessary coordination
- Common → core.domain is actually OK (types are part of the interface)
- Core → adapters should be eliminated through dependency injection
- After 6c, focus on Phase 6d (test refactoring) before 6e
