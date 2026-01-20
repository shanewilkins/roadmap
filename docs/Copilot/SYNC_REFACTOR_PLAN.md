# Sync Refactor Plan

Status: Draft — baseline captured, CC measured.

## Purpose
Create a safe, incremental plan to decouple analysis from execution in the sync pipeline, extract mixed concerns, and reduce cyclomatic complexity (CC) so the code is easier to test, reason about, and maintain.

## Baseline
- Baseline commit: created (pre-refactor snapshot in repository). Note: pre-commit hooks ran; `pyright` reported one non-blocking diagnostic during commit steps.
- Cyclomatic complexity (radon) baseline (scan of sync-related modules):
  - Average complexity (scanned blocks): A (4.70)
  - Notable high-complexity hotspots:
    - `roadmap/adapters/cli/sync.py::sync` — F (127)
    - `roadmap/adapters/sync/sync_merge_orchestrator.py::sync_all_issues` — F (63)
    - `roadmap/core/services/sync_state_comparator.py::analyze_three_way` — E (34)
    - `roadmap/adapters/sync/backends/github_sync_backend.py::pull_issue` — D (21)
    - `roadmap/adapters/sync/sync_cache_orchestrator.py::_get_baseline_with_optimization` — C (16)
    - `roadmap/adapters/sync/sync_merge_orchestrator.py::_match_and_link_remote_issues` — C (18)
    - `roadmap/adapters/sync/services/issue_state_service.py::sync_issue_to_issue` — C (16)
    - `roadmap/adapters/sync/services/sync_linking_service.py::find_duplicate_by_title` — B (9)

(Full radon output is in the terminal log; this file contains key highlights.)

## Mixed Concerns Identified
These responsibilities are currently interleaved in the sync call path and should be separated:

- Matching / Auto-linking (currently mutates DB/files during analysis)
- Remote fetch & authentication (network, retries, rate-limit handling)
- Baseline retrieval & caching (DB reads/writes and git history reconstruction)
- Three-way comparison / conflict detection (pure analysis)
- Conflict resolution (pure decision-making vs persistence)
- Execution / Apply (pushing/pulling, local file writes, DB writes)
- State persistence & transactions (save_base_state, remote_links)
- Progress / UI / Reporting (CLI rendering & progress bars)
- Batching vs per-item applies (push_issues/pull_issues)
- Retry, backoff, and rate-limit handling (in backend clients)
- Logging, telemetry, and error classification
- Idempotency and safety checks (pre-apply validations)
- Test seams / dependency injection for core components

## High-level Architecture (target)
- Analyzer: pure component that consumes local, remote, baseline snapshots and returns a `SyncPlan` (list of `Action`s) + `SyncReport` (metrics). No side effects.
- Action model: typed representation of granular operations (PushAction, PullAction, LinkAction, CreateLocalAction, UpdateBaselineAction, etc.). Each action has `describe()` and `apply(executor)` semantics.
- Executor: consumes a `SyncPlan`, performs side-effects inside safe transaction boundaries, batches where beneficial, and supports `dry_run` mode (simulate only). All writes go through the executor/persister.
- BaselineRetriever: encapsulates DB & git-based baseline logic; returns baseline objects for analyzer but does not mutate DB when called from analysis.
- RemoteFetcher: encapsulates backend API calls (auth + fetches) and exposes snapshots for analyzer; includes retry/rate-limit strategy.
- ConflictResolver: pure service that suggests resolutions; persists nothing during analysis.
- Persister / StatePersister: central place to persist baseline updates, remote links, and other DB mutations executed by Executor.
- Presenter (CLI): renders `SyncPlan`/`SyncReport` and interacts with user (confirmations, progress bars). Keeps UI concerns out of analyzer/executor.

## Incremental, Low-Risk Plan
We will refactor in small steps, each safe to review and unit-test.

1. Add `SyncPlan` and `Action` models (non-invasive)
   - Create `roadmap/core/services/sync_plan.py` with `Action` base and concrete subclasses.
   - Add `SyncPlan` dataclass to hold actions and meta (counts, conflicts).
   - Tests: serialization/describe outputs.

2. Extract analysis into `analyze_all_issues()` (pure)
   - Refactor `SyncMergeOrchestrator.sync_all_issues` to extract the analysis portion that constructs `updates`, `pulls`, `conflicts` into `analyze_all_issues()` returning a `SyncPlan` and `SyncReport` (no DB writes).
   - Replace in-place matching/linking with action creation (e.g., produce `LinkAction` or `CreateLocalAction`), not immediate writes.
   - Keep `sync_all_issues()` as a thin wrapper for backward compatibility that calls `analyze_all_issues()` then `execute_plan()`.
   - Tests: verify analyzer output is identical regardless of `dry_run` and does not perform writes (mock DB/backend).

3. Implement `Executor.execute_plan(plan, dry_run=False)`
   - Implement the executor that applies actions, handles batching, and updates baseline via `Persister`.
   - Ensure `dry_run=True` produces the same outcomes in reports without mutating state.
   - Tests: ensure no DB/backend calls on dry-run; verify transactional behavior on real-run (mock DB commit calls).

4. Extract BaselineRetriever & RemoteFetcher
   - Move baseline/construction logic into `BaselineRetriever` and caching into `BaselineCache`.
   - RemoteFetcher wraps backend auth/fetch with retry and rate-limit logic.
   - Tests: unit tests for baseline builders and fetcher (simulate backends and git history).

5. Move matching/linking to return actions
   - Convert `_match_and_link_remote_issues` and related services to produce actions instead of performing writes in analysis.
   - Tests: verify produced `LinkAction`/`CreateLocalAction` semantics.

6. Refactor conflict resolution to be pure
   - Ensure `SyncConflictResolver` returns resolved decisions and does not persist state during analysis.
   - Map resolved decisions to `Action`s for executor.

7. Improve batching & apply logic
   - Executor decides when to batch pushes/pulls for performance and updates report accounting.
   - Tests: ensure batching is invoked and report is correct.

8. Add safety checks and persister
   - Implement `StatePersister` to centralize DB writes (remote_links, baseline save, state updates) and wrap in transactions.
   - Executor invokes persister only when `dry_run=False`.
   - Tests: integration tests that persist expected records for a sample plan.

9. Add observability and error classification
   - Add tracing points to analyzer and executor; add clear error classes (recoverable vs fatal) used by presenter.

10. Run full test suite and CC measurement
   - Run `poetry run pytest` and fix regressions.
   - Re-run radon CC and compare with baseline.

11. Iterate and document
   - Repeat on other hotspots (backends, comparator) until CC metrics improve.

## Metrics & Acceptance
- Primary metric: reduction in average cyclomatic complexity for the sync code regions and lowering of the worst hotspots.
- Secondary metrics: increased unit-test coverage for analyzer & executor; fewer side-effecting paths in analyzer.
- Success criteria: significant drop in CC grade for `sync_all_issues` and `cli/sync.py` from F→D/C, plus stable tests.

## Commands (how to reproduce)
- Run radon CC for sync areas:

```bash
python -m pip install --upgrade radon
radon cc -s roadmap/adapters/sync roadmap/adapters/cli/sync.py roadmap/core/services -a
```

- Run tests:

```bash
poetry run pytest -q
```

## Notes & Risks
- Large backends like GitHub involve network and rate limits; extract retry/limit handling early to avoid brittle tests.
- Keep changes small and gated by tests; prefer additive refactor (new methods) over big rewrites.
- Maintain CLI behavior during transition by keeping `sync_all_issues()` wrapper compatibility.

## Next Steps
- Start implementing Step 1: add `Action` classes and `SyncPlan` model, then Step 2: extract `analyze_all_issues()`.
- I updated the workspace TODOs to reflect the plan.

---
Created by: automated refactor planning tool
Date: 2026-01-10

## Phased Roadmap (6-10 Phases)

We will execute the refactor in discrete phases to limit blast radius, keep behavior stable, and measure improvements after each phase. Each phase should be small enough to review and test independently.

Phase 1 — Discovery & Safe scaffolding
- Goals: Add `SyncPlan` and `Action` models; add lightweight interfaces for `BaselineRetriever`, `RemoteFetcher`, `Executor`, and `Persister`.
- Scope: Add new files and types only; no behavior change. Add unit tests for models.
- Success metric: New models exist, tests pass, no changes to runtime behavior.

Phase 2 — Extract Pure Analyzer
- Goals: Move analysis (three-way compare) into `analyze_all_issues()` that returns a `SyncPlan` and `SyncReport` without side effects.
- Scope: Refactor `SyncMergeOrchestrator.sync_all_issues` to call `analyze_all_issues()`; replace in-analysis writes with action creation.
- Success metric: Analyzer returns identical actionable summary versus pre-refactor analysis for sample inputs; dry-run behavior unchanged.

Phase 3 — Action Executor & Persister
- Goals: Implement `Executor.execute_plan(plan, dry_run)` and `StatePersister` to centralize DB/file mutations and transactional safety.
- Scope: Implement executor to apply `Action`s, support batching, and wrap persister calls in a transaction boundary.
- Success metric: Non-dry runs apply identical changes; `dry_run` produces no writes; add tests asserting transactional commits and rollbacks.

Phase 4 — Baseline & Remote Separation
- Goals: Extract `BaselineRetriever` (DB + git fallback + cache) and `RemoteFetcher` (auth, fetch, retry policy) as explicit collaborators used by the analyzer and executor.
- Scope: Move baseline-building and backend fetch code into new services and add unit tests mocking external systems.
- Success metric: Baseline and remote logic are testable, and analyzer consumes their snapshots without causing writes.

Phase 5 — Matching, Linking & Conflict Resolution as Action Producers
- Goals: Convert matching/linking and conflict resolution components to pure decision-makers that produce `Action`s instead of performing side effects.
- Scope: Refactor `_match_and_link_remote_issues`, `SyncLinkingService`, and `SyncConflictResolver` to emit actions; ensure executor persists outcomes.
- Success metric: Analyzer produces `LinkAction`/`CreateLocalAction`/`ResolveAction` for all cases previously mutated in-analysis.

Phase 6 — Presenter / CLI & UX Decoupling
- Goals: Move all progress UI, confirmations, and rendering into a `Presenter` that operates on `SyncPlan`/`SyncReport` and invokes `Executor` on confirmation.
- Scope: Simplify `roadmap/adapters/cli/sync.py` to call `analyze_all_issues()` for preview and `Executor.execute_plan()` for apply; keep the CLI behaviour unchanged.
- Success metric: CLI preview and apply UX preserved; progress and verbose outputs implemented by presenter; smaller `sync()` function CC.

Phase 7 — Hardening, Observability & Rate-Limit Handling
- Goals: Add retry/backoff for remote calls, classify errors (recoverable/fatal), add tracing/metrics around analyzer/executor, and enforce `is_safe_for_writes` before applying.
- Scope: Extend `RemoteFetcher`/backend wrappers with throttling + observability hooks; instrument executor and persister.
- Success metric: Improved reliability under network failure scenarios; structured metrics emitted.

Phase 8 — Tests, Metrics & CC Re-measure
- Goals: Add comprehensive unit and integration tests for analyzer and executor; run full test suite and re-run radon CC to measure improvement.
- Scope: Update CI to run CC checks and break builds if CC above agreed threshold for critical files. Commit changes and update CHANGELOG.
- Success metric: Reduction in CC for `sync_all_issues`, CLI `sync`, and comparator; all tests green; commit with changelog.

## Execution & Timing
- Work in small branches per phase (e.g., `sync-refactor/phase-1-action-models`).
- Each phase should include: (1) implementation, (2) unit tests, (3) small integration test if applicable, (4) radon CC snapshot for changed files.
- Aim for ~1-3 day cycles per phase depending on approval and testing.

## Measurement
- After each phase, run radon CC for targeted files and record the delta in the PR description:

```bash
radon cc -s roadmap/adapters/sync roadmap/adapters/cli/sync.py roadmap/core/services -a
```

- Track: worst-function CC, average CC, and number of functions in F/E/D grades. Prefer incremental visible reductions.

## Governance
- Open a PR per phase with tests and CC diff. Keep changes small for reviewability.
- If phase causes regressions, revert and split into smaller sub-phases.

---
End of phased roadmap.
