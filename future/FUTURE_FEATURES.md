# Future Features (Post-1.0)

This directory contains features archived for post-1.0 development. These modules have been removed from the v1.0 core release to simplify the codebase and focus on essential functionality.

## Migration Summary

**Modules Moved**: 20 Python modules (11,488 lines)
**Tests Moved**: 15 test files (related test coverage)
**Date Archived**: November 18, 2025
**Reason**: Aggressive v1.0 simplification - keep core, defer advanced features

---

## Feature Categories

### Phase 1: Enterprise Analytics & Advanced Features (7,788 lines)

#### Analytics Suite
- **`analytics.py`** - Advanced project analytics (burn-down, velocity metrics)
- **`enhanced_analytics.py`** - ML-driven analytics and predictions
- **`predictive.py`** (1,354 lines) - Predictive forecasting and modeling
- **`analytics_commands.py`** - CLI commands for analytics features

#### GitHub Enterprise
- **`enhanced_github_integration.py`** - Enterprise-level GitHub features
- **`repository_scanner.py`** - Automatic GitHub repository analysis

#### CI/CD Integration
- **`ci_tracking.py`** - CI/CD pipeline tracking and metrics

#### Data & Workflow Management
- **`curation.py`** - Data curation and cleanup workflows
- **`timezone_migration.py`** - Comprehensive timezone handling

#### Infrastructure
- **`identity.py`** - Advanced identity and authentication management
- **`webhook_server.py`** - Webhook server infrastructure for integrations

### Phase 2: Advanced CLI Commands (3,700 lines)

#### Team & User Management
- **`team_management.py`** (from `cli/team.py`) - Advanced team management
- **`user_management.py`** (from `cli/user.py`) - User management commands

#### CI/CD Commands
- **`ci_commands.py`** (from `cli/ci.py`) - CI/CD integration commands (1,544 lines)

#### Release Management
- **`release_management.py`** (from `cli/release.py`) - Release coordination commands

#### Timezone & Activity
- **`timezone_commands.py`** (from `cli/timezone.py`) - Timezone commands
- **`activity_tracking.py`** (from `cli/activity.py`) - Activity timeline features

#### Deprecated
- **`deprecated_commands.py`** (from `cli/deprecated.py`) - Old/deprecated commands

---

## Restoring Features for Post-1.0 Development

To restore a feature:

1. **Move the module back** to `roadmap/`:
   ```bash
   mv future/analytics.py roadmap/
   mv future/ci_commands.py roadmap/cli/ci.py
   ```

2. **Restore related tests** to `tests/`:
   ```bash
   mv future/tests/test_analytics.py tests/
   ```

3. **Register CLI commands** (if applicable) in `roadmap/cli/__init__.py`:
   ```python
   from roadmap.cli import analytics  # Register analytics commands
   ```

4. **Update imports** in any remaining code that references the feature

5. **Run tests** to ensure proper integration:
   ```bash
   poetry run pytest tests/test_analytics.py -v
   ```

---

## Import Strategy

All future modules **still import from core**:
- `from roadmap.models import Issue, Milestone`
- `from roadmap.core import RoadmapCore`
- `from roadmap.database import StateManager`
- etc.

This ensures that when features are restored, they'll work seamlessly with the core v1.0 functionality.

---

## V1.0 Core (What Remains)

The v1.0 release includes only:
- **Issue Management**: Create, list, update, delete issues
- **Milestone Tracking**: Create milestones, track progress
- **Basic Progress**: Simple progress percentage calculation
- **GitHub Integration**: Basic GitHub import/sync
- **Data Persistence**: SQLite-based storage
- **CLI Core**: Essential commands for roadmap management

---

## Statistics

| Category | Lines | Modules |
|----------|-------|---------|
| Phase 1: Post-1.0 Features | 7,788 | 11 |
| Phase 2: Advanced CLI | 3,700 | 8 |
| **Total Archived** | **11,488** | **19** |

**Remaining in v1.0**: ~18,824 lines across core modules

---

## Timeline

- **v1.0**: Core features only
- **v1.1-1.x**: Add back analytics, team management, advanced GitHub features
- **v2.0+**: Predictive analytics, ML models, webhook infrastructure

---

## Questions?

Refer to `PRUNING_PLAN.md` for the original analysis and decision rationale.
