# Dead Code Analysis - Incomplete Refactorings Identified

## Summary

Found 5 candidate "dead code" files. Analysis reveals these fall into 3 distinct patterns:

### Pattern 1: Intentional Deprecated Facades (Safe to Delete)

**Files:**

- `roadmap/adapters/cli/export_helpers.py`
- `roadmap/adapters/cli/issue_display.py`

**Status:** DEPRECATED - explicitly marked with "DEPRECATED" docstrings
**Purpose:** Backward compatibility shims during migration to new modules
**Impact:** 0 external imports (migration complete)
**Recommendation:** ✅ SAFE TO DELETE - These are successful completed migrations

### Pattern 2: Incomplete Refactorings - Extracted but Not Integrated

**Files:**

- `roadmap/adapters/cli/services/milestone_list_service.py`
- `roadmap/adapters/cli/presentation/milestone_list_presenter.py`
- `roadmap/adapters/cli/presentation/project_initialization_presenter.py`

**Status:** INCOMPLETE REFACTORINGS (similar to HealthCheckService, StatusReportingService, InitializationOrchestrationService that we just fixed)

**Details:**

#### MilestoneListService & MilestoneListPresenter

- **Extracted in:** Phase 10 ("Phase 10: Extract MilestoneListService and MilestoneListPresenter")
- **Service contains:** MilestoneFilterService, MilestoneProgressService, MilestoneListService (200+ lines of business logic)
- **Presenter contains:** MilestoneTablePresenter, MilestoneListPresenter (136 lines of display logic)
- **Current usage:** NONE - milestones/list.py command uses `MilestoneTableFormatter` directly instead
- **Import status:** 0 external imports (self-referencing only)
- **Problem:** Service/Presenter extracted but CLI command never updated to use them
- **Solution:** Similar to what we did for HealthCheckService:
  - Integrate MilestoneListService into milestones/list.py
  - Use MilestoneTablePresenter instead of direct MilestoneTableFormatter calls
  - Or delete both if they're unnecessary abstractions

#### ProjectInitializationPresenter

- **Extracted in:** Phase 8 ("Phase 8: Extract ProjectInitializationService and Presenter from core.py")
- **Contains:** 230+ lines of project initialization UI logic (show_detected_context, prompts, creation status, etc.)
- **Current usage:** NONE in production code (only in unit tests)
- **Contrast:** CoreInitializationPresenter IS used in init/commands.py and status.py
- **Problem:** ProjectInitializationPresenter extracted but never integrated into init/commands.py
- **Note:** CoreInitializationPresenter appears to be a separate presenter for different purpose (core initialization workflow vs project creation workflow)
- **Solution:** Investigate why ProjectInitializationPresenter exists separately from CoreInitializationPresenter, then either:
  - Integrate into init command workflow
  - Delete if CoreInitializationPresenter is the intended replacement
  - Merge functionality if they should be the same

## Architectural Pattern

This mirrors the situation we just resolved:

**Similar to our recent refactoring:**

- HealthCheckService: Extracted, existing code used HealthCheck instead → FIXED by updating status.py
- StatusReportingService: Extracted, but no command used it → FIXED by implementing generate-report command
- InitializationOrchestrationService: Extracted, init command had duplicate logic inline → FIXED by delegating to service

**Current incomplete refactorings:**

- MilestoneListService/Presenter: Extracted in Phase 10, but milestones/list.py still uses old pattern
- ProjectInitializationPresenter: Extracted in Phase 8, but init/commands.py uses different presenter

## Recommendations

**Immediate:** DO NOT DELETE yet. These are evidence of architectural improvements in progress.

**Investigation needed:**

1. MilestoneListService: Are the filtering/progress calculations needed? Or is MilestoneTableFormatter sufficient?
2. MilestoneListPresenter: Is the presenter abstraction valuable, or should milestones/list.py continue using direct rendering?
3. ProjectInitializationPresenter: Why does a separate presenter exist? Was it superseded by CoreInitializationPresenter?

**Decision points:**

- If MilestoneList* are redundant: Delete both
- If MilestoneList* are valuable: Integrate into milestones/list.py (like we did for health check)
- If ProjectInitializationPresenter is superseded: Delete it
- If ProjectInitializationPresenter should be used: Refactor init/commands.py to use it
