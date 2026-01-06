# Sync Improvements: Backend-Agnostic Remote ID Tracking

## The Problem

Currently, sync operations fail to match local and remote issues correctly:

- **Local issues** are keyed by internal UUID (e.g., `7e99d67b`)
- **Remote issues** are keyed by backend ID (e.g., `gh-42` for GitHub)
- **Comparator** tries to match by key and fails
- **Result**: All issues treated as new every sync, creating duplicates

## Root Causes

1. **GitHub-specific domain model**: `github_issue` field hardcoded for GitHub only
2. **No ID mapping layer**: Comparator has no way to know which local issue matches which remote issue
3. **No backend interface methods**: Backends don't tell sync layer how to match IDs

## The Solution

### Phase 1: Foundation (This Sprint)
- Add generic `remote_ids: dict[str, str | int]` to Issue model (keyed by backend name)
- Keep `id: str` as immutable internal UUID (source of truth)
- Add backwards-compatible `github_issue` property

### Phase 2: Backend Integration
- Add `get_backend_name()` to `SyncBackendInterface`
- Update `GitHubBackend.get_issues()` to return issues keyed by GitHub number
- Implement `_normalize_local_to_remote_keys()` in `SyncStateComparator`

### Phase 3: Comparator Awareness
- Pass backend instance to `SyncStateComparator`
- Normalize keys before comparison
- Match issues by remote ID before falling back to UUID

### Phase 4: Manual Linking (Current Priority)
- Add `roadmap sync --link <local-id> <remote-id>` command
- Add `roadmap sync --unlink <local-id>` command
- These explicitly set/remove `remote_ids[backend_name]`

### Phase 5: Smart Matching (Future)
- Auto-match by title during first sync
- Ask user confirmation for ambiguous cases
- Auto-link on push/pull operations

## Consistency Guarantees

**Invariant 1**: Local UUID never changes
```python
assert issue.id == original_uuid_from_creation
```

**Invariant 2**: One local issue per remote ID
```python
assert len([i for i in issues if i.remote_ids.get("github") == 42]) <= 1
```

**Invariant 3**: Matching is deterministic
```python
if issue.remote_ids.get("github"):
    # Will be matched to GitHub issue
```

## Key Benefits

✅ Backend-agnostic - any backend can store multiple remote IDs
✅ Consistent - single UUID never changes
✅ Extensible - add backends without schema changes
✅ Backwards compatible - existing code still works
✅ Accurate matching - no more false duplicates

## Integration Points

| Component | Change |
|-----------|--------|
| Issue domain model | Add `remote_ids` dict field |
| SyncBackendInterface | Add `get_backend_name()` method |
| SyncStateComparator | Accept backend, normalize keys before compare |
| SyncMergeOrchestrator | Pass backend to comparator |
| CLI | Add `--link` and `--unlink` flags to sync command |
| Persistence | YAML serialization of `remote_ids` dict |

## No Breaking Changes

- `issue.github_issue` property still works (reads/writes `remote_ids["github"]`)
- Existing sync workflow unchanged (just works better)
- Migration automatic on first write
