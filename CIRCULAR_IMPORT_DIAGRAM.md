# Circular Import Dependency Diagram

## Import Cycle Visualization

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CIRCULAR DEPENDENCY CHAIN                       │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────┐
    │  roadmap.infrastructure.coordination.core                        │
    │  (RoadmapCore)                                                   │
    │                                                                  │
    │  Line 28-33:                                                     │
    │  from roadmap.core.services import (                             │
    │      ConfigurationService,                                       │
    │      GitHubIntegrationService,                                   │
    │      IssueService,                                               │
    │      MilestoneService,                                           │
    │      ProjectService,  ◄─── FORCES IMPORT OF core/services       │
    │  )                                                               │
    └────────────┬─────────────────────────────────────────────────────┘
                 │
                 │ Forces module init
                 ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │  roadmap.core.services.__init__                                  │
    │                                                                  │
    │  WITHOUT LAZY LOADING (WOULD IMPORT):                            │
    │  ┌────────────────────────────────────────────────────────────┐ │
    │  │ from .health.health_check_service import                   │ │
    │  │     HealthCheckService                                     │ │
    │  │                                                            │ │
    │  │ from .project.project_status_service import               │ │
    │  │     ProjectStatusService                                  │ │
    │  │                                                            │ │
    │  │ from .git.git_hook_auto_sync_service import               │ │
    │  │     GitHookAutoSyncService                                │ │
    │  └────────────────────────────────────────────────────────────┘ │
    │                                                                  │
    │  CURRENT (WITH LAZY LOADING):                                   │
    │  _lazy_modules = {                                              │
    │      "HealthCheckService": ("health.health_check_service", ...) │
    │      "ProjectStatusService": ("project.project_status_service"..│
    │      ...                                                         │
    │  }                                                               │
    │  def __getattr__(name): ...  # Dynamic import on first use      │
    └────────────┬─────────────────────────────────────────────────────┘
                 │
                 │ Would import (without lazy loading)
                 │
          ┌──────┴──────────────────────────────────────┐
          │                                              │
          ▼                                              ▼
    ┌──────────────────────┐                   ┌──────────────────────┐
    │ health_check_        │                   │ project_status_      │
    │ service.py           │                   │ service.py           │
    │                      │                   │                      │
    │ Line 11:             │                   │ Line 10:             │
    │ from roadmap.        │                   │ from roadmap.        │
    │ infrastructure.      │                   │ infrastructure.      │
    │ coordination.core    │                   │ coordination.core    │
    │ import RoadmapCore ──┼───────┬───────────┼─> import RoadmapCore│
    └──────────────────────┘       │           └──────────────────────┘
                                   │
                                   │ CIRCULAR!
                                   │
                        ┌──────────▼──────────┐
                        │ Still initializing  │
                        │ RoadmapCore - ERROR │
                        └─────────────────────┘
```

## Import Timeline with Lazy Loading (How It's Avoided)

```
TIME →

1. Code imports RoadmapCore:
   from roadmap.infrastructure.coordination.core import RoadmapCore

2. RoadmapCore.__init__ imports services:
   from roadmap.core.services import ProjectService

3. core/services/__init__.py loads:
   - Eagerly imports: BaselineRetriever, BaselineStateRetriever, etc.
   - DOES NOT import HealthCheckService (uses lazy loading)
   - __getattr__ function is registered
   ✓ No error yet - HealthCheckService not imported

4. RoadmapCore initializes repositories, coordinators, etc.
   ✓ RoadmapCore now fully initialized

5. Later (when needed):
   service = HealthCheckService(core)

   Python doesn't find HealthCheckService in __dict__
   → Calls __getattr__("HealthCheckService")
   → Dynamically imports roadmap.core.services.health.health_check_service
   → Which imports RoadmapCore
   ✓ RoadmapCore already exists - no circular dependency!
```

## Module Dependency Graph (Simplified)

```
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ coordination/core.py (RoadmapCore)                  │       │
│  │                                                     │       │
│  │ Imports: IssueService, MilestoneService,           │       │
│  │          ProjectService, etc.                      │       │
│  └────────────────────┬────────────────────────────────┘       │
│                       │                                        │
│                       ▼                                        │
│  coordination/{issue,milestone,project}_coordinator.py        │
│  coordination/{issue,milestone,project}_operations.py         │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        │ depends on
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ core/services/__init__.py                           │       │
│  │                                                     │       │
│  │ Eager imports (safe):                              │       │
│  │ - BaselineRetriever                                │       │
│  │ - CommentService                                   │       │
│  │ - IssueService, IssueCreationService               │       │
│  │ - MilestoneService                                 │       │
│  │ - etc.                                             │       │
│  │                                                     │       │
│  │ Lazy imports (TO BREAK CYCLE):                     │       │
│  │ - HealthCheckService                               │       │
│  │ - ProjectStatusService                             │       │
│  │ - GitHookAutoSyncService                           │       │
│  │ - DataIntegrityValidatorService                    │       │
│  │ - etc.                                             │       │
│  └────────────────┬──────────────────────────────────┘       │
│                   │                                            │
│     ┌─────────────┼──────────────┬────────────────────┐       │
│     ▼             ▼              ▼                    ▼       │
│  health/       project/       git/             sync/          │
│  services      services       services         services        │
│                                                                │
│  These import RoadmapCore ◄──────────┐                       │
│                                       │                        │
│                                  (WOULD CAUSE CYCLE             │
│                                   WITHOUT LAZY LOADING)         │
│                                                                │
│  Adapters also import services:                              │
│  adapters/sync/sync_merge_orchestrator.py                   │
│    ↓ imports SyncStateComparator, etc.                       │
│    ↓ imports RoadmapCore                                     │
│                                                                │
└─────────────────────────────────────────────────────────────┘
        │
        │ imports repositories, domain models
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  ADAPTERS LAYER (persistence, git, etc.)                        │
│  DOMAIN LAYER (Issue, Milestone, Project, etc.)                 │
│  COMMON LAYER (utilities, constants, logging)                   │
└─────────────────────────────────────────────────────────────────┘
```

## TYPE_CHECKING Solution Architecture

```
BEFORE (WITH LAZY LOADING):

    roadmap/core/services/__init__.py
    ┌──────────────────────────────────┐
    │ _lazy_modules = {...}            │
    │ def __getattr__(name):           │  ◄── Complex mechanism
    │     module = __import__(...)     │      to defer imports
    │     return getattr(...)          │
    └──────────────────────────────────┘
           ▲
           │ Complex
           │ Runtime dispatch
           │
    HealthCheckService ──► TYPE: RoadmapCore
                          (but import deferred)


AFTER (WITH TYPE_CHECKING):

    roadmap/core/services/__init__.py
    ┌──────────────────────────────────┐
    │ # Clean, simple imports          │
    │ from .health.health_check_service│
    │     import HealthCheckService    │  ◄── Direct imports
    └──────────────────────────────────┘
           │
           │
    HealthCheckService.py
    ┌──────────────────────────────────┐
    │ from typing import TYPE_CHECKING │
    │                                  │
    │ if TYPE_CHECKING:               │
    │     from roadmap.infrastructure. │
    │     coordination.core import     │
    │         RoadmapCore             │  ◄── Import only for type hints
    │                                  │      (not executed at runtime)
    │ class HealthCheckService:        │
    │     def __init__(self,           │
    │         core: "RoadmapCore"  ◄──┼── String quote delays evaluation
    │     ):                           │
    │         self.core = core         │
    └──────────────────────────────────┘
```

## Lazy Loading Trigger Points

```
When services/__init__.py is imported:

IMMEDIATE (Eager Loading):
├─ ConfigurationService ✓
├─ CommentService ✓
├─ IssueService ✓
├─ MilestoneService ✓
├─ GitHub services ✓
├─ Baseline services ✓
├─ Issue services (most) ✓
└─ Sync services (most) ✓

DEFERRED (Lazy Loading - Only when explicitly requested):
├─ HealthCheckService ◄── Imported by RoadmapCore indirectly
├─ ProjectStatusService ◄── Imported by RoadmapCore
├─ GitHookAutoSyncService ◄── Imported by RoadmapCore
├─ DataIntegrityValidatorService ◄── Used by health checks
├─ InfrastructureValidator ◄── Used by health checks
└─ (10+ sync-related services)

Why services/__init__.py can import these immediately:
- They don't import RoadmapCore at the MODULE level
- They only accept it as a CONSTRUCTOR PARAMETER
- By the time they're instantiated, RoadmapCore exists

Why they're currently lazy anyway:
- Extra safety belt
- Clearer intent (marks services that depend on infrastructure)
- Avoids imports that might fail in certain contexts
```

## Import Order Dependency

```
✓ CORRECT ORDER (No Circular Issues):

1. Import RoadmapCore
2. RoadmapCore.__init__ runs:
   2a. Creates repositories
   2b. Creates domain services (IssueService, etc.)
   2c. Creates coordinators
   2d. ✓ RoadmapCore is fully constructed
3. Someone creates HealthCheckService(core)
   3a. HealthCheckService imports RoadmapCore ✓ (already exists)
   3b. No problem!


✗ WRONG ORDER (Why not lazy = bad):

1. Import HealthCheckService at module level
   1a. HealthCheckService imports RoadmapCore
   1b. RoadmapCore.__init__ imports HealthCheckService
   1c. → DEADLOCK / Partial initialization
   1d. ✗ circular import error


✓ CURRENT ORDER (With lazy loading):

1. Import RoadmapCore
2. RoadmapCore imports from core.services.__init__
3. core.services.__init__ registers __getattr__
   3a. HealthCheckService NOT imported yet
   3b. ✓ No circular reference
4. RoadmapCore finishes __init__
5. ✓ Later code can now import HealthCheckService
```
