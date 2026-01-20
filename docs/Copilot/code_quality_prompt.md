
# AI_REFACTOR_SPEC.md

## Purpose
This document defines a phased, tool-driven refactor plan to raise this Python CLI codebase to professional quality: maintainable architecture, consistent style, strong static guarantees, robust tests, structured observability, and deterministic builds.

This document is written as operating instructions for an AI assistant or senior contributor.

---

## Non-Negotiables

### Change discipline
- Make changes in small, reviewable change sets (ideally one phase per change set).
- Do not mix refactors with behavior changes unless explicitly required by the phase.
- Preserve public CLI behavior and exit codes unless explicitly changed.
- Every change set must include:
  - What changed
  - Why it changed
  - Risks / tradeoffs
  - Validation performed

### Definition of Done (global)
- All CI checks pass.
- Tool thresholds satisfied (lint, type, complexity, security).
- Test coverage ≥ 85% (with documented exclusions).
- Test runtime ≤ 3 minutes on CI runner.
- pytest + pytest-mock used consistently.
- structlog used consistently for application logging.
- No silent failures; actionable error handling.

---

## Tooling Stack

- Formatting/Lint: ruff, ruff-format
- Security: bandit
- Complexity: radon
- Dead code: vulture
- Lint (secondary): pylint
- Types: pyright
- Docs: pydocstyle
- Tests: pytest, pytest-mock, pytest-cov
- Logging: structlog

---

## Global Policies

### Python & Dependencies
- Supported Python versions declared in pyproject.toml and CI.
- Legacy compatibility shims removed once versions are locked.
- Dependencies and tooling pinned or locked to ensure deterministic builds.

### Logging (structlog)
- All application logging uses structlog.get_logger().
- Structured logs with stable keys.
- stdout: primary CLI output
- stderr: logs, warnings, errors
- No silent exception handling.

### Testing
- pytest only; no unittest.
- pytest-mock for mocking.
- Prefer fixtures, factories, and parametrization.
- Tests must assert meaningful behavior.

---

## Phase Plan

### Phase 0 — Lock platform and versions
**Goal:** Establish deterministic builds and eliminate version-related warnings.

Actions:
1. Choose supported Python versions.
2. Update pyproject.toml (requires-python, deps, tooling).
3. Update CI matrix.
4. Remove obsolete compatibility code.
5. Add lockfile if applicable.

Acceptance:
- CI matches declared versions.
- Reduced deprecation warnings.
- Deterministic installs.

---

### Phase 1 — Dead code removal
**Goal:** Remove unused code before refactoring.

Actions:
- Run vulture and ruff unused checks.
- Delete confirmed dead code.
- Validate via tests.

Acceptance:
- Tests pass.
- No behavior changes.

---

### Phase 2 — Type checking
**Goal:** Establish a clean pyright baseline.

Actions:
- Fix pyright errors.
- Improve annotations at boundaries.
- Remove unreachable code.

Acceptance:
- Zero pyright errors.

---

### Phase 3 — Complexity reduction
**Goal:** Reduce cyclomatic complexity.

Actions:
- Identify functions with CC > 20.
- Refactor via extraction and simplification.
- Add CI enforcement.

Acceptance:
- Complexity thresholds enforced.

---

### Phase 4 — Separation of concerns
**Goal:** Eliminate god objects and mixed responsibilities.

Actions:
- Split large files/classes.
- Enforce architecture layers.
- Maintain inward-only dependencies.

Acceptance:
- Clear module boundaries.

---

### Phase 5 — Layer violations & directory hygiene
**Goal:** Improve readability and navigability.

Actions:
- Fix import direction violations.
- Refactor directories with >15 files.
- Ensure descriptive filenames.

Acceptance:
- Documented layers.
- Clean directory structure.

---

### Phase 6 — DRY and test fixtures
**Goal:** Reduce harmful duplication.

Actions:
- Refactor duplicated logic where appropriate.
- Introduce fixture factories.
- Reduce decorator-heavy tests.

Acceptance:
- Less duplication.
- Cleaner tests.

---

### Phase 7 — Error handling & logging
**Goal:** Improve observability and robustness.

Actions:
- Standardize structlog usage.
- Implement error taxonomy.
- Route output correctly.

Acceptance:
- No silent failures.
- Consistent structured logs.

---

### Phase 8 — Coverage & pytest modernization
**Goal:** Improve reliability.

Actions:
- Increase test coverage.
- Migrate remaining unittest code.
- Add coverage reporting.

Acceptance:
- ≥85% coverage.

---

### Phase 9 — Test data hygiene
**Goal:** Improve test robustness.

Actions:
- Replace hardcoded data with factories.
- Reduce brittle formatting assertions.

Acceptance:
- Stable, behavior-focused tests.

---

### Phase 10 — Mock reduction
**Goal:** Test behavior, not implementation.

Actions:
- Remove excessive mocks.
- Mock only true boundaries.
- Standardize on pytest-mock.

Acceptance:
- Resilient tests.

---

### Phase 11 — Assertion quality
**Goal:** Ensure tests actually validate behavior.

Actions:
- Add meaningful assertions.
- Remove vague or empty tests.

Acceptance:
- Every test asserts value.

---

### Phase 12 — Test performance
**Goal:** Fast feedback.

Actions:
- Identify slow tests.
- Optimize fixtures.
- Remove obsolete skips.

Acceptance:
- Tests run <3 minutes.

---

### Phase 13 — Warning burn-down
**Goal:** Eliminate risky warnings.

Actions:
- Capture recurring warnings.
- Fix or justify each.
- Repeat until clean.

Acceptance:
- No substantial warnings.

---

### Phase 14 — Additional best practices
**Goal:** Catch remaining improvements.

Checklist:
- CLI UX
- Config handling
- Security posture
- Documentation accuracy

Acceptance:
- Improvements justified and measurable.

---

### Phase 15 — Senior review and grading
**Goal:** Final quality assessment.

Actions:
- Review architecture, tests, logging, CI.
- Produce prioritized findings.
- Assign grade (A+ to F).

---

## CI Gate Order (Recommended)
1. ruff format --check
2. ruff check
3. pydocstyle
4. pylint
5. pyright
6. bandit
7. radon
8. vulture (informational or gated)
9. pytest (with coverage)

---

## Per-Phase Output Requirements
Each phase must produce:
- Summary
- Rationale
- Risk
- Validation
- Metrics (before/after)

Append results to REFRACTOR_LOG.md.
