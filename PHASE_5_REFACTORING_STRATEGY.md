# Phase 5: Refactoring Strategy

## Overview
24 layer violations to fix. Split into two tiers: HIGH IMPACT first, then TRANSITIVE.

## TIER 1: HIGH IMPACT (11 violations) - Start Here

### 1. Persistence Abstraction (7 violations)
Services importing `roadmap.adapters.persistence.*` directly:
- `baseline_state_retriever` → `persistence.parser.frontmatter`, `persistence.parser.issue`
- `milestone_service` → `persistence.parser`
- `project_service` → `persistence.parser`
- `project_init.detection` → `persistence.parser`
- `data_integrity_validator` → `persistence.parser`
- `infrastructure_validator_service` → `persistence.storage`

**Solution:**
- Create `roadmap.infrastructure.persistence_gateway.py`
- Define interfaces for common queries (get_frontmatter, get_issues, get_project, etc.)
- Have services call gateway instead of adapter directly
- Gateway handles actual adapter imports

**Effort:** ~2-3 hours (pattern extraction + interface design)

---

### 2. Sync Service Abstraction (2 violations)
- `git_hook_auto_sync_service` → `adapters.sync.backend_factory`, `adapters.sync.sync_cache_orchestrator`

**Solution:**
- Create `roadmap.infrastructure.sync_gateway.py`
- Wrap sync backend initialization and orchestration
- Services request syncs through gateway

**Effort:** ~1 hour (smaller scope)

---

### 3. GitHub Integration Abstraction (2 violations)
- `github_integration_service` → `adapters.github.github`
- `github_issue_client` → `adapters.github.github`, `adapters.github.handlers.base`

**Solution:**
- Create `roadmap.infrastructure.github_gateway.py`
- Wrap GitHub adapter and handler access
- Services call gateway for GitHub operations

**Effort:** ~1 hour (similar pattern to sync)

---

## TIER 2: INFRASTRUCTURE TRANSITIVE (13 violations)

### 4. Infrastructure Coordination Layer (10 violations)
All Core → Infrastructure → Adapters chains through `coordination.*`:
- `coordination.core` imports git adapters, persistence adapters
- `coordination.issue_operations` imports persistence
- `coordination.milestone_coordinator` imports persistence
- etc.

**Investigation Needed:**
- Should these coordination classes move to adapters?
- Or should infrastructure have adapters imports but not core?
- This determines the refactoring approach

**Options:**
- A) Move coordination to adapters (adapters.coordination.*)
- B) Have infrastructure import adapters (allowed), keep core isolated
- C) Create intermediate service layer in infrastructure

**Effort:** ~3-4 hours (design-dependent)

---

### 5. Git Adapter (2 violations)
- `initialization.workflow` → `coordination.core` → `git.sync_monitor`
- `initialization.validator` → `coordination.core` → `git.git_hooks`

**Solution:** Part of Tier 2 coordination resolution

---

### 6. Other (1 violation)
- `sync_plan_executor` → `adapters.sync.services.sync_linking_service`

**Solution:** May be covered by Sync Gateway

---

## Execution Plan

### Phase 5A: Persistence, Sync, GitHub Gateways (Tier 1)
**Time:** 4-5 hours
**Risk:** Low (isolated abstraction layers)
**Testing:** Unit test each gateway, integration tests for services

1. Create persistence gateway with interfaces
2. Refactor 7 services to use gateway
3. Verify tests still pass
4. Repeat for sync gateway (2 violations fixed)
5. Repeat for GitHub gateway (2 violations fixed)
6. Run full pre-commit + tests

### Phase 5B: Coordination/Infrastructure (Tier 2)
**Time:** 4-6 hours
**Risk:** Medium (requires architectural decision)

1. Analyze coordination layer design
2. Decide: move to adapters vs. allow infrastructure imports?
3. Implement refactoring
4. Update import-linter contracts if needed
5. Verify tests pass

---

## Success Criteria

- [ ] All 24 violations in import-linter output = 0
- [ ] All 6,567 tests still passing
- [ ] No new complexity violations (radon pass)
- [ ] Pre-commit hook passes (0 broken contracts)
- [ ] `violation_baseline.csv` updated with "fixed" status

---

## Next Action

**Start with Tier 1:** Create persistence gateway first. It's the highest-impact violation set and uses the clearest pattern.
