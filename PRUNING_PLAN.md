# V1.0 Aggressive Pruning Plan

## Analysis Summary

- **V1.0 Target**: Core project roadmap tracking with GitHub integration
- **Current State**: 30,312 lines across 55 modules
- **Identified for Removal**: 7,788 lines from 12 known post-1.0 features (25.7%)
- **Additional Opportunity**: ~8,000-10,000 more lines from advanced CLI features

---

## Phase 1: Safe Removal (Post-1.0 Enterprise Features)

Removing **7,788 lines (25.7% of codebase)** - these are clearly post-1.0:

| Module | Lines | Reason |
|--------|-------|--------|
| `predictive.py` | 1,354 | ML-driven forecasting; advanced feature |
| `repository_scanner.py` | 937 | Auto-GitHub scanning; post-1.0 |
| `curation.py` | 920 | Data curation workflows |
| `ci_tracking.py` | 782 | CI/CD integration; enterprise feature |
| `analytics.py` | 730 | Burn-down/velocity metrics; advanced |
| `enhanced_github_integration.py` | 648 | Enterprise GitHub features |
| `timezone_migration.py` | 669 | Can use simpler date handling in v1.0 |
| `identity.py` | 410 | Advanced identity/auth management |
| `webhook_server.py` | 303 | Integration server; not core |
| `enhanced_analytics.py` | 493 | ML analytics predictions |
| `cli/analytics.py` | 40 | Depends on analytics.py |

**Total: 7,788 lines removed**

---

## Phase 2: Advanced CLI Features (3,700 lines)

Optional but recommended for leaner v1.0:

| Module | Lines | Reason |
|--------|-------|--------|
| `cli/ci.py` | 1,544 | CI commands; depends on ci_tracking.py |
| `cli/team.py` | 1,012 | Advanced team management |
| `cli/user.py` | 504 | User management; GitHub reference sufficient |
| `cli/activity.py` | 531 | Activity timeline; analytics feature |
| `cli/release.py` | 368 | Release management; not core tracking |
| `cli/timezone.py` | 240 | Timezone commands; not essential |

**Total: 3,700 lines removed**

---

## Phase 3: Cleanup (Dead Code)

Remove with confidence:

- `cli/deprecated.py` (151 lines) - Obviously deprecated

---

## Phase 4: Review & Consolidation

Needs investigation:

| Module | Lines | Issue |
|--------|-------|-------|
| `git_hooks.py` + `git_hooks_v2.py` | 1,049 | Why two versions? Consolidate |
| `visualization.py` | 1,488 | Charts are advanced; archive if possible |
| `git_integration.py` | 656 | Check for post-1.0 features |
| `persistence.py` | 370 | Potential overlap with database.py |
| `cli/__init__.py` | 507 | Check if bloated |

---

## Impact Summary

### Conservative (Phase 1 only)
- **Remove**: 7,788 lines (25.7%)
- **Keep**: 22,524 lines
- **Result**: Cleaner codebase, all v1.0 features intact

### Recommended (Phases 1-2)
- **Remove**: 11,488 lines (37.9%)
- **Keep**: 18,824 lines
- **Result**: Lean v1.0; easy to expand post-1.0

### Aggressive (Phases 1-4 with consolidation)
- **Remove**: ~14,000 lines (46%)
- **Keep**: ~16,300 lines
- **Result**: Minimal focused core

---

## Core Modules to Keep

**Must Keep for V1.0:**
- `models.py` - Data models
- `core.py` - RoadmapCore class
- `database.py` - SQLite persistence
- `parser.py` - YAML parsing
- `cli/issue.py` - Issue management
- `cli/milestone.py` - Milestone management
- `cli/progress.py` - Progress tracking
- `cli/core.py` - CLI entry point
- Plus utilities: `data_utils.py`, `validation.py`, `error_handling.py`, etc.

---

## Archival Strategy

1. Create `archive/` directory in repo
2. Move removed modules there (preserve structure)
3. Document what was archived and why
4. Update imports to reference archived versions if needed
5. Post-1.0: Can restore features cleanly

---

## Execution Order

1. **Archive** removed files to `archive/` directory
2. **Update** imports in remaining code
3. **Remove** CLI command registrations
4. **Test** to ensure no breakage
5. **Update** documentation
