# Phase 6: Comprehensive Layer Violation Hunt

## Objective
Identify and fix all architectural layer violations to ensure proper separation of concerns and maintain clean dependency boundaries.

## Layer Dependency Rules (Allowed Imports)

### ✅ Allowed Import Directions

```
Adapters (CLI)
    ↓ can import from Core, Common, Shared
    
Core (Application/Services)
    ↓ can import from Common, Shared
    
Common (Shared Utilities)
    ↓ can import from Shared
    
Shared (Infrastructure)
    ↓ no dependencies (leaf layer)
```

### ❌ Forbidden Import Directions

- Core importing from Adapters ❌
- Core importing from Infrastructure directly (should go through interfaces) ❌
- Common importing from Adapters ❌
- Common importing from Core ❌
- Shared importing from anything ❌
- Adapters importing from Infrastructure directly (should use services) ❌

## Scanning Strategy

### Phase 6a: Identify Violations
1. Scan all imports in each layer
2. Build dependency graph
3. Identify backwards/lateral dependencies
4. Categorize by severity

### Phase 6b: Generate Report
1. List all violations with line numbers
2. Suggest fixes
3. Estimate refactoring effort

### Phase 6c: Fix Violations
1. High priority violations first
2. Use dependency injection and interfaces
3. Test after each fix

## Expected Issues

Based on architecture analysis, likely violations:
- Direct Core → Adapters imports (should use dependency injection)
- Direct Common → Core imports (circular dependencies)
- Infrastructure imports scattered across layers
- Shared imports in wrong places

## Success Criteria

✅ No imports from lower layers to upper layers
✅ Clean dependency graph (acyclic)
✅ All circular dependencies eliminated
✅ All imports validated by architecture checker
✅ All 6,558+ tests passing after fixes

## Timeline

- **Phase 6a**: Scan & identify (20-30 min)
- **Phase 6b**: Report generation (10-15 min)
- **Phase 6c**: Fix violations (1-2 hours)
- **Verification**: Full test suite validation (15-20 min)
