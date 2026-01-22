# Known Issue: Semgrep + Import-Linter Dependency Conflict

**Status:** BLOCKED - Semgrep cannot be added to `pyproject.toml` until fixed
**Workaround:** Semgrep available locally via pre-commit
**Target Resolution:** Q1/Q2 2026 (waiting for Semgrep upstream fix)

---

## The Problem

**Semgrep all 1.x versions** require: `rich >=13.5.2,<13.6.0` (pinned exactly to 13.5.x)
**Import-linter 2.9** (our current version) requires: `rich >=14.2.0`

These constraints cannot both be satisfied in Poetry. The dependency tree cannot resolve.

```
roadmap-cli depends on:
  ├─ import-linter ^2.9 → requires rich >=14.2.0
  └─ semgrep ^1.x → requires rich 13.5.2 to <13.6.0 (INCOMPATIBLE)
```

**Impact:** Cannot add Semgrep to `pyproject.toml` without breaking architecture enforcement.

---

## Current Workaround (Local Only - Manual Mode)

Semgrep is installed locally and runs via **pre-commit managed hook in manual mode**:

**File:** `.pre-commit-config.yaml`
```yaml
- repo: https://github.com/returntocorp/semgrep
  rev: v1.45.0
  hooks:
    - id: semgrep
      args: [--config=.semgrep.yml, --error]
      stages: [manual]  # DISABLED by default
```

**How it works:**
- Pre-commit runs in its own isolated virtual environment
- Semgrep is installed there (no conflict with Poetry's `rich`)
- Hook is set to `stages: [manual]` so it doesn't run automatically on `git commit`
- Developers can run manually: `pre-commit run semgrep --all-files`
- CI does NOT run Semgrep yet (uses custom audit script as fallback)

**To enable for local development:**
```bash
# Run Semgrep manually before committing
pre-commit run semgrep --all-files

# Or update .pre-commit-config.yaml to remove `stages: [manual]` when ready
```

**Current limitation:**
- Baseline feature not available in v1.45.0
- Catches existing violations (would block commits if auto-enabled)
- Will be enabled automatically in Phase 7b once baseline feature available

**Consequence:**
- ✅ Developers CAN run Semgrep to check for violations
- ⚠️ Doesn't block commits automatically (not critical during Phase 7 refactoring)
- ⚠️ CI won't catch new violations yet
- ✅ Custom audit script provides fallback enforcement

---

## Permanent Solution (When Resolved)

Once **Semgrep fixes their `rich` dependency constraint** (GitHub issue TBD):

1. Add Semgrep to `pyproject.toml`:
   ```bash
   poetry add -D semgrep
   ```

2. Update `.pre-commit-config.yaml` to use Poetry hook:
   ```yaml
   - repo: local
     hooks:
       - id: semgrep
         entry: poetry run semgrep
   ```

3. Add to CI/CD (`.github/workflows/tests.yml`):
   ```yaml
   - name: Run Semgrep
     run: poetry run semgrep --config=.semgrep.yml roadmap/
   ```

4. Remove custom audit script from production use

---

## Why We Accept This Temporary Gap

1. **Semgrep fix is not in our control** - depends on upstream maintainer
2. **Local protection is most valuable** - developers get feedback immediately
3. **CI still enforces via custom script** - not unprotected, just using fallback
4. **Temporary architectural inconsistency is acceptable** during Phase 7 refactoring
5. **Clear upgrade path exists** - resolution is straightforward once dependency resolved

---

## Developer Notes

### Running pre-commit locally

```bash
# Run all pre-commit hooks (including Semgrep)
pre-commit run --all-files

# Run only Semgrep
pre-commit run semgrep --all-files

# Bypass pre-commit (NOT RECOMMENDED)
git commit --no-verify
```

### Semgrep baseline

The `.semgrep-baseline.json` file tracks known violations so pre-commit doesn't block existing issues while we refactor in Phase 7b-7e.

To regenerate baseline (after fixing violations):
```bash
semgrep --config=.semgrep.yml roadmap/ --json > .semgrep-baseline.json
```

### When Semgrep dependency is fixed

Monitor: [Semgrep GitHub Issues](https://github.com/returntocorp/semgrep/issues)

Search for issues related to `rich` versioning constraints. Once fixed in upstream release:

1. Try `poetry add -D semgrep` again
2. If it resolves, proceed with permanent solution above
3. Update this document

---

## Phase 7 Impact

**Phase 7a-7e (Refactoring):**
- Local developers use Semgrep via pre-commit ✅
- CI uses custom audit script as fallback ⚠️
- No blocker to Phase 7 progress

**Phase 7f (Testing):**
- Add test cases for error handling
- Test cases serve as backup enforcement

**Post-Phase 7:**
- Once Semgrep dependency fixed: migrate to Poetry + CI
- Archive custom audit script to reference only

---

## Historical Context

Added January 22, 2026 as part of Phase 7a tooling analysis.

Decision: Use Semgrep locally despite dependency conflict, rather than waiting for fix or compromising on architecture enforcement tool (import-linter).
