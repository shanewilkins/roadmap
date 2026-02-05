# Sync Entity Breakdown - Architecture Proposal

## Executive Summary

Currently, the sync system tracks only **issues** at a granular level. **Milestones** and **Projects** exist in the codebase but are not fully integrated into the sync reporting and UI. This proposal outlines how to extend sync to handle all three entity types with proper breakdown in both dry-run and post-sync reports.

## Current State Analysis

### Entity Types in Codebase
1. **Issue** - Fully tracked in sync
2. **Milestone** - Partially synced (pulled as dependencies, pushed as needed)
3. **Project** - NOT currently synced to GitHub

### Current Sync Report Structure
```python
@dataclass
class SyncReport:
    # Local counts
    total_issues: int = 0
    total_milestones: int = 0

    # Remote counts
    remote_total_issues: int = 0
    remote_total_milestones: int = 0

    # Analysis (ISSUE-ONLY currently)
    issues_up_to_date: int = 0
    issues_needs_push: int = 0
    issues_needs_pull: int = 0
    conflicts_detected: int = 0  # Mixed entity types?

    # Application results (ISSUE-ONLY)
    issues_pushed: int = 0
    issues_pulled: int = 0

    changes: list[IssueChange] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
```

### Current UI Output
```
📈 Sync Analysis
   ✓ Up-to-date: 0
   📤 Needs Push: 1828
   📥 Needs Pull: 1869
   ✓ Potential Conflicts: 0
```

**Problem**: This doesn't distinguish between issues, milestones, and projects.

## Key Questions & Answers

### Q1: Do we need to sync Projects to GitHub?

**Answer: NO (for now)**

**Reasoning**:
- GitHub doesn't have a native "Project" entity that maps to our domain model
- GitHub Projects is a separate feature (project boards) that doesn't align with our Project concept
- Our `Project` is more like a local organizational construct that groups milestones
- Milestones provide the GitHub integration point

**Recommendation**: Projects remain local-only. Sync focuses on **Issues** and **Milestones**.

### Q2: What about "Potential Conflicts"?

**Current Implementation**:
```python
conflicts_detected: int = 0  # Issues with changes in both directions
```

This is calculated from IssueChange objects where:
```python
change.has_conflict = True  # Both local and remote changed from baseline
```

**Issue**: The term "Potential Conflicts" is misleading:
- These are *actual* conflicts detected during three-way merge analysis
- "Potential" suggests they might happen, but they're already identified
- They're only counted for **issues**, not milestones

**Recommendation**: Rename to "Conflicts" and track per entity type.

### Q3: Are "updates" included in push/pull counts?

**Current Behavior**:
- **Push counts**: Local-only changes (new or modified locally)
- **Pull counts**: Remote-only changes (new or modified remotely)
- **Conflicts**: Both sides changed (bidirectional updates)

**Key Point**: Conflicts are EXCLUDED from push/pull counts currently. This is correct for a three-way merge model.

**Calculation Logic**:
```python
push_changes = [c for c in changes if c.is_local_only_change()]
pull_changes = [c for c in changes if c.is_remote_only_change()]
conflicts = [c for c in changes if c.has_conflict]
```

So the categories are mutually exclusive:
- **Push**: Local changed, remote unchanged from baseline
- **Pull**: Remote changed, local unchanged from baseline
- **Conflict**: Both changed from baseline

## Proposed Solution

### 1. Extend SyncReport Data Structure

```python
@dataclass
class EntitySyncStats:
    """Sync statistics for a single entity type."""
    # Pre-sync analysis counts
    up_to_date: int = 0
    needs_push: int = 0
    needs_pull: int = 0
    conflicts: int = 0
    errors: int = 0  # Analysis/fetch errors

    # Post-sync result counts
    pushed: int = 0
    pulled: int = 0
    push_errors: int = 0  # Failed pushes
    pull_errors: int = 0  # Failed pulls

@dataclass
class SyncReport:
    # Entity-specific statistics
    issue_stats: EntitySyncStats = field(default_factory=EntitySyncStats)
    milestone_stats: EntitySyncStats = field(default_factory=EntitySyncStats)
    project_stats: EntitySyncStats = field(default_factory=EntitySyncStats)  # For future use

    # Legacy fields (computed from entity stats for backward compatibility)
    @property
    def issues_up_to_date(self) -> int:
        return self.issue_stats.up_to_date

    @property
    def issues_needs_push(self) -> int:
        return self.issue_stats.needs_push

    # ... etc

    # Aggregated totals
    @property
    def total_needs_push(self) -> int:
        return (self.issue_stats.needs_push +
                self.milestone_stats.needs_push +
                self.project_stats.needs_push)

    @property
    def total_needs_pull(self) -> int:
        return (self.issue_stats.needs_pull +
                self.milestone_stats.needs_pull +
                self.project_stats.needs_pull)

    @property
    def total_conflicts(self) -> int:
        return (self.issue_stats.conflicts +
                self.milestone_stats.conflicts +
                self.project_stats.conflicts)
```

### 2. Category Completeness Analysis

**Critical Finding**: The current categories (push/pull/conflicts) are **mutually exclusive but NOT jointly exhaustive**.

#### Complete State Space

There are **5 distinct categories** for sync states:

| Category | `local_changes` | `remote_changes` | `has_conflict` | `conflict_type` | Currently Displayed? |
|----------|----------------|------------------|----------------|-----------------|---------------------|
| **Up-to-date** | ❌ (empty) | ❌ (empty) | ❌ | `"no_change"` | ❌ **Missing in dry-run detail** |
| **Needs Push** | ✅ (non-empty) | ❌ (empty) | ❌ | `"local_only"` | ✅ Yes |
| **Needs Pull** | ❌ (empty) | ✅ (non-empty) | ❌ | `"remote_only"` | ✅ Yes |
| **Conflicts** | ✅ (non-empty) | ✅ (non-empty) | ✅ | `"both_changed"` | ✅ Yes |
| **Errors** | N/A | N/A | N/A | N/A | ❌ **Missing in dry-run** |

**Problems Identified**:
1. Up-to-date issues are counted in `report.issues_up_to_date` but not shown in dry-run detail view
2. Errors are tracked in `report.errors` dict but not included in category breakdown
3. Current dry-run only shows 3 of 5 categories

**Code Evidence**:
```python
# In sync_three_way.py - all 4 change categories created:
if change.local_changes and change.remote_changes:
    change.conflict_type = "both_changed"
elif change.local_changes:
    change.conflict_type = "local_only"
elif change.remote_changes:
    change.conflict_type = "remote_only"
else:
    change.conflict_type = "no_change"  # <-- UP-TO-DATE!

# In dry_run_display.py - only 3 categories displayed:
push_changes = [c for c in changes if c.is_local_only_change()]
pull_changes = [c for c in changes if c.is_remote_only_change()]
conflicts = [c for c in changes if c.has_conflict]
# Missing: up_to_date and errors!
```

### 3. New UI - Dry-Run Analysis Table (Entity Columns × Status Rows)

```
📈 Sync Analysis

┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Status       ┃ Issues      ┃ Milestones  ┃ Projects    ┃ TOTAL       ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Up-to-date   │ 1,234       │ 56          │ 3           │ 1,293       │
│ Needs Push   │ 1,828       │ 12          │ 0           │ 1,840       │
│ Needs Pull   │ 1,869       │ 8           │ 0           │ 1,877       │
│ Conflicts    │ 0           │ 0           │ 0           │ 0           │
│ Errors       │ 5           │ 0           │ 0           │ 5           │
└──────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

**Why this orientation**:
- Easier to scan across entity types for a given status
- Status categories are the primary concern (what needs action?)
- Entity types are secondary grouping
- TOTAL column shows aggregate impact

### 4. New UI - Post-Sync Report Table (Entity Columns × Status Rows)

```
📊 Sync Complete

┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Status       ┃ Issues      ┃ Milestones  ┃ Projects    ┃ TOTAL       ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Pushed       │ 1,823       │ 12          │ 0           │ 1,835       │
│ Pulled       │ 1,864       │ 8           │ 0           │ 1,872       │
│ Conflicts    │ 0           │ 0           │ 0           │ 0           │
│ Errors       │ 10          │ 0           │ 0           │ 10          │
└──────────────┴─────────────┴─────────────┴─────────────┴─────────────┘

⚠️  10 errors occurred during sync (see details below)

Error Details:
  • 5 push failures (rate limit exceeded)
  • 5 pull failures (network timeout)
```

**Post-sync categories**: Only 4 categories needed (no "up-to-date" or "needs X" - just results)

### 5. MilestoneChange Data Class

Currently we only have `IssueChange`. We need:

```python
@dataclass
class MilestoneChange:
    """Represents changes to a single milestone during sync."""
    milestone_id: str
    name: str

    # Three-way states
    baseline_state: MilestoneBaseState | None = None
    local_state: Milestone | None = None
    remote_state: dict[str, Any] | None = None

    # Analyzed changes
    local_changes: dict[str, Any] = field(default_factory=dict)
    remote_changes: dict[str, Any] = field(default_factory=dict)

    # Conflict analysis
    conflict_type: str = "no_change"
    has_conflict: bool = False
    flagged_conflicts: dict[str, Any] = field(default_factory=dict)

    def is_local_only_change(self) -> bool:
        return bool(self.local_changes and not self.remote_changes)

    def is_remote_only_change(self) -> bool:
        return bool(self.remote_changes and not self.local_changes)
```

## Implementation Plan

### Phase 1: Data Model Extension (2-3 hours)
1. Create `EntitySyncStats` dataclass
2. Add `issue_stats`, `milestone_stats` to `SyncReport`
3. Add computed properties for backward compatibility
4. Create `MilestoneChange` dataclass

### Phase 2: Analysis Service Updates (3-4 hours)
1. Update `SyncStateComparator` to generate `MilestoneChange` ob (status rows × entity columns)
2. Add up-to-date and error sections to dry-run detail view
3. Create `_display_sync_results_table()` for post-sync report (status rows × entity columns)
4. Update `present_analysis()` in sync_presenter.py to use table format
5. Update `SyncReport.display_brief()` method with new table
6. Ensure error details are shown after post-sync table
### Phase 3: UI Updates (2-3 hours)
1. Create `_display_sync_analysis_table()` in dry_run_display.py
2. Create `_display_sync_results_table()` for post-sync report
3. Update `present_analysis()` in sync_presenter.py
4. Update `SyncReport.display_brief()` method

### Phase 4: Testing & Validation (2 hours)
1. Unit tests for `EntitySyncStats` calculations
2. Integration tests for multi-entity sync scenarios
3. Manual testing with real GitHub sync

**Total Estimate**: 9-12 hours

## Migration Strategy

### Backward Compatibility
- Keep all existing `SyncReport` fields as computed properties
- Existing code accessing `report.issues_needs_push` will continue to work
- New code can use `report.issue_stats.needs_push` for clarity

### Rollout
1. Implement data model with computed properties (no breaking changes)
2. Update internal services to use entity stats
3. Update UI to show tables
4. Remove legacy fields in next major version (optional)

## Open Questions
values.

2. **How to handle milestone-only sync (no issues)?**
   - **Recommendation**: System should handle naturally with entity breakdown

3. **What about archived entities?**
   - **Recommendation**: Archived entities are not synced. Report only active entities.

4. **Should conflicts be auto-resolved or always require user input?**
   - **Current behavior**: Depends on `--interactive` flag
   - **Recommendation**: Keep current behavior, but show conflict count in all cases

5. **Should we show up-to-date items in dry-run detail view?**
   - **Recommendation**: No in detail (too verbose), yes in summary table
   - Shows "nothing to do" status clearly

6. **How to display error details after sync?**
   - Completeness**: All 5 categories visible (up-to-date, push, pull, conflicts, errors)
3. **Debugging**: Easier to identify if milestone sync is failing while issues succeed
4. **Consistency**: Same table orientation for dry-run and post-sync reports
5. **Actionable**: Clear distinction between items needing action vs. errors vs. up-to-date
6. **Scannable**: Status rows make it easy to find "what needs my attention"
7. **Future-proof**: Ready for project sync if we decide to implement it
8    * Error message
     * Suggested action
   - **Current behavior**: Depends on `--interactive` flag
   - **Recommendation**: Keep current behavior, but show conflict count in all cases

## Benefits

1. **Clarity**: Users see exactly what's happening to each entity type
2. **Debugging**: Easier to identify if milestone sync is failing while issues succeed
3. **Future-proof**: Ready for project sync if we decide to implement it
4. **Consistency**: Same table format for dry-run and post-sync reports
5. **Monitoring**: Better metrics for sync health and performance

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking changes | Use computed properties for backward compat |
| UI too verbose | Use Rich tables for clean formatting |
| Performance impact | Entity stats are just counters, minimal overhead |
| Milestone sync bugs | Thorough testing of milestone change detection |
complete 5-category breakdown (up-to-date, push, pull, conflicts, errors)
- ✅ Dry-run table uses status rows × entity columns orientation
- ✅ Post-sync shows 4-category breakdown (pushed, pulled, conflicts, errors)
- ✅ Post-sync table uses same orientation as dry-run
- ✅ Error details shown after post-sync table with actionable information
- ✅ All existing tests pass
- ✅ New tests cover all 5 categories per entity type
- ✅ Manual sync with GitHub shows correct counts per entity
- ✅ Backward compatibility maintained (no breaking changes)
- ✅ Zero counts displayed with dim styling for clarity
- ✅ New tests cover entity-specific stats
- ✅ Manual sync with GitHub shows correct counts per entity
- ✅ Backward compatibility maintained (no breaking changes)

## Next Steps

1. **Review & Approval**: Get feedback on this proposal
2. **Implementation**: Follow phased approach above
3. **Testing**: Comprehensive test coverage
4. **Documentation**: Update user guide with new UI examples
5. **Deployment**: Roll out in next release
