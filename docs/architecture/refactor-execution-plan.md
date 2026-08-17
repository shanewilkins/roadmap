# Roadmap 0.2 refactor execution plan

- Status: Approved
- Execution status: Phase 4 checkpoint passed on 2026-08-17; stop and obtain
  maintainer approval before Phase 5
- Date: 2026-08-16
- Baseline commit: `61595a6e`
- Current release: 0.1.1
- Target release: 0.2.0
- Executor: Codex, with maintainer review between every phase
- Governing documents: ADR-0001 through ADR-0010,
  [refactor-implementation.md](refactor-implementation.md), and
  [roadmap-0.2.md](roadmap-0.2.md)

## Execution contract

The refactor proceeds sequentially. Codex will complete only one phase at a
time, stop, run the complete checkpoint, report the evidence, and wait for the
maintainer before beginning the next phase.

No phase is accepted while any required check is failing. Codex will not:

- dismiss a failure as unrelated, flaky, or acceptable;
- skip, delete, weaken, or mark a retained-behavior test as expected-failing to
  obtain a green checkpoint;
- change an accepted ADR silently;
- carry two production implementations of a migrated behavior into the next
  phase;
- commit, create a branch, push, or publish without the authorization required
  by repository policy; or
- begin the next phase before delivering the checkpoint report and receiving
  explicit approval to continue.

Production Python CLOC is also a hard ratchet. Phase 0 records the baseline with
one fixed command and tool version. For every later phase, production CLOC under
`roadmap/` must be less than or equal to the preceding accepted checkpoint. A
phase that increases production CLOC is `NO-GO`; it must be simplified within
that phase before the full checkpoint can pass. Tests, fixtures, scripts, and
documentation are measured and reported separately and do not offset production
growth.

The maintainer explicitly exempted the one-time Phase 0A lifecycle repair from
the no-increase decision gate so correctness fixes could establish a trustworthy
baseline. Phase 0A still measured and reported CLOC and finished below the Phase
0 value. Its accepted 54,206-line result becomes the normal hard ceiling for
Phase 1.

If a failure appears, work remains in the current phase. Codex will diagnose it,
fix it within the approved scope, and rerun the failed check followed by the
entire checkpoint. If fixing it requires a product decision, ADR change, public
compatibility break outside the plan, or material scope expansion, Codex will
stop and ask for direction.

## Standard phase checkpoint

Every phase ends with the same seven-part checkpoint. Phase-specific tests and
journeys are added to this minimum.

### 1. Freeze and inspect

- Stop implementation work.
- Review `git status`, the complete diff, deleted files, and generated files.
- Run `git diff --check`.
- Confirm the phase changed only its declared scope.
- Run the fixed production CLOC command and compare its `Python/code` value with
  the preceding accepted phase:

  ```bash
  cloc roadmap \
    --include-lang=Python \
    --exclude-dir=__pycache__ \
    --csv \
    --quiet
  ```

- Record the CLOC version, production file count, blank lines, comment lines,
  code lines, absolute delta, and percentage delta.
- Record architecture-baseline counts, runtime dependencies, and remote-sync
  code remaining when relevant.
- Mark the phase `NO-GO` if production Python code lines exceed the preceding
  accepted checkpoint, even when every test passes.

### 2. Dependency and static-quality gate

Run the repository's CI-equivalent commands:

```bash
uv lock --check
uv run --locked ruff format --config config/ruff.toml --check roadmap tests
uv run --locked ruff check --config config/ruff.toml roadmap tests
uv run --locked pyright
uv run --locked bandit -c config/bandit.toml -r roadmap --severity-level=high
```

After Phase 2, this section also runs the architecture policy and verifies that
the exact violation baseline did not grow.

### 3. Complete automated test suite

Run the same complete suite and coverage collection used by CI:

```bash
uv run --locked pytest \
  --cov=roadmap \
  --cov-config=config/.coveragerc \
  --cov-report=term-missing
```

Record total passed, failed, skipped, xfailed, coverage, and elapsed time. Any
change in skipped or expected-failure counts must be explained. A reduction in
test count is allowed only when the phase intentionally removes approved public
behavior or provably duplicate tests; the checkpoint report lists those tests.

### 4. Distribution boundary

Build both artifacts in a fresh temporary output directory and run the existing
isolated installation smoke test against each:

```bash
uv build --out-dir <temporary-artifact-directory>
python scripts/smoke_package.py <wheel>
python scripts/smoke_package.py <source-distribution>
```

The smoke environment must not inherit `PYTHONPATH` or import Roadmap from the
source checkout.

### 5. Application journeys

Run the cumulative retained-journey smoke set in a disposable workspace. The
set grows as slices migrate and never substitutes for the complete suite:

1. install, `--help`, and `--version`;
2. initialize a new workspace and safely reopen it;
3. create, find, view, update, transition, archive, and restore an issue;
4. create and inspect a project and milestone, assign an issue, and verify
   derived progress;
5. request and parse supported machine-readable output;
6. edit a canonical document manually and verify that Roadmap observes it;
7. delete or corrupt only the disposable SQLite projection and verify an
   equivalent rebuild without canonical-file changes;
8. run health diagnosis and a non-mutating repair preview;
9. inspect local Git context with network access unavailable; and
10. from Phase 9 onward, dry-run and execute migration of a 0.1.1 fixture, then
    reopen it and verify semantic equivalence.

Before a journey is migrated, the checkpoint uses its characterized 0.1.1
behavior. After migration, it uses the approved 0.2 contract. Removed behavior
is tested for intentional absence and clear replacement guidance.

### 6. CI checkpoint

When the maintainer authorizes a checkpoint commit and push, wait for the full
GitHub Actions matrix to pass before starting the next phase. Local success is
not used to override a failing supported-platform job.

### 7. Stop and report

Deliver a phase report containing:

- behavior added, preserved, replaced, and removed;
- important files changed and deleted;
- requirement IDs advanced;
- focused-test results;
- full-suite and coverage results;
- wheel and source-distribution smoke results;
- cumulative application-journey results;
- architecture violations removed or remaining;
- data compatibility and rollback evidence;
- known risks and deliberately deferred work; and
- production CLOC before, after, and delta, with confirmation that the ratchet
  passed; and
- a clear `GO` or `NO-GO` recommendation.

Then wait. The next phase does not start automatically.

## Phase 0 — establish the unchanged baseline

### Objective

Prove that commit `61595a6e` is a reproducible good baseline and create a stable
checkpoint harness before refactoring production code.

### Work

- Run the complete standard checkpoint against the unchanged codebase.
- Record CLOC 2.10 output as the initial production-code ratchet. The observed
  pre-refactor value is 54,225 Python code lines across 504 counted files; Phase
  0 verifies that value against baseline commit `61595a6e` rather than assuming
  it.
- Record the exact CLI command tree, documented options, exit categories,
  structured formats, runtime dependencies, production/test counts, test
  outcomes, and coverage.
- Create a sanitized 0.1.1 compatibility fixture containing a project,
  milestone, visible issue, closed issue, archived issue, dependency, comment,
  external reference, user-authored Markdown, legacy IDs, and current SQLite
  projections.
- Record canonical-file digests separately from derived-state files.
- Add a reusable installed-artifact journey runner that operates only in a
  temporary directory and cannot touch the repository's live `.roadmap` data.
- Document the exact checkpoint commands so subsequent phases use one process.

### Boundaries

- No production behavior or package layout changes.
- Do not repair pre-existing failures invisibly. A failing baseline is a hard
  stop and becomes a separately reported baseline blocker.
- The compatibility fixture contains no real credentials, tokens, private
  remotes, or user-specific paths.

### Focused verification

- Tests prove the journey runner rejects a non-temporary or repository-local
  target.
- The fixture loads successfully through the 0.1.1 CLI.
- Re-running the fixture inspection produces identical semantic output and
  canonical digests.

### Exit condition

The unchanged full suite, artifacts, and baseline journeys pass, or the
refactor stops with a concrete baseline defect report. The verified Phase 0
production CLOC becomes the maximum allowed at Phase 1.

## Phase 0A — repair baseline lifecycle defects

Phase 0A was the separately approved remediation triggered by the Phase 0
`NO-GO`. It repaired comment persistence and failure status, archive/restore
canonical and SQLite consistency, legacy lifecycle schema migration, archived
projection rebuild, and milestone-to-project persistence. It also added the
sanitized 0.1.1 fixture and safe installed-artifact checkpoint runner.

The complete checkpoint passed on 2026-08-16. See
[phase-0a-lifecycle-repair-2026-08-16.md](checkpoints/phase-0a-lifecycle-repair-2026-08-16.md).
Execution stops after this result and waits for explicit approval before Phase
1.

## Phase 1 — freeze the 0.2 public contract

### Objective

Decide exactly which released behaviors the refactor preserves, deliberately
replaces, removes, or treats as internal before production modules move.

### Work

- Triage the user and technical requirement registers.
- Accept the Must requirements that define 0.2, assign every scheduled row a
  phase target, and defer or reject post-0.2 and removed behavior explicitly.
- Create a compatibility inventory for commands, options, exit categories,
  configuration keys, canonical fields, stable IDs, JSON/CSV schemas, Git
  behaviors, and migration fixtures.
- Mark every inventory item `Preserve`, `Replace`, `Remove`, or `Internal` with
  its evidence and destination phase.
- Resolve ambiguous top-level commands such as provider sync, comments,
  analysis, cleanup, and automatic Git mutation before their code is touched.
- Correct current documentation claims that conflict with the approved 0.2
  boundary.

### Boundaries

- Documentation, requirements, inventories, and contract fixtures only.
- No production package moves or behavioral changes.
- Existing stable IDs and canonical user content cannot be classified Internal.

### Focused verification

- CSV schema and ID/reference validation for both requirement registers.
- A policy check fails for a documented public command or configuration key
  missing from the inventory.
- Every `Remove` item has replacement or migration guidance.

### Exit condition

Every currently released surface has one disposition, owner, evidence fixture,
and target phase; no Draft row is silently treated as committed scope.

## Phase 2 — enforce the target architecture

### Objective

Install a mechanical ratchet before any production migration.

### Work

- Add `architecture.toml` with the exact Domain, Application, inbound adapter,
  outbound adapter, and Bootstrap dependency rules.
- Implement the AST import checker and its pytest policy entry point.
- Add one positive fixture and one focused negative fixture for every rule.
- Generate `architecture-baseline.toml` from current imports, then review every
  entry for source, target, rule, reason, and planned removal phase.
- Fail on new violations, stale entries, duplicates, malformed entries, cycles,
  and removed namespaces after their deletion phase.
- Replace any wrapper that converts architecture failures to success.
- Add the policy to local instructions and CI.
- Repair Pyright configuration sufficiently that its success is meaningful and
  record any temporary, exact type-check baseline separately.

### Boundaries

- No production module relocation.
- No broad exception pattern or wildcard baseline.
- Generated baseline entries require human-readable reasons and phase owners.

### Focused verification

- Every invalid fixture fails with the expected rule and source/target pair.
- Removing a used baseline entry fails as a new violation.
- Leaving an unused baseline entry fails as stale.
- The unchanged production tree passes only with its exact reviewed baseline.

### Exit condition

Architecture enforcement is a real local and CI gate, its baseline is exact,
and deliberately introduced violations fail.

## Phase 3 — create Bootstrap without changing behavior

### Objective

Make `roadmap.bootstrap` the only place that selects and constructs concrete
implementations while preserving all 0.1.1 behavior.

### Work

- Introduce a composition root that constructs the existing collaborators.
- Move process-wide initialization, configuration discovery, console creation,
  telemetry initialization, and command dependency construction behind
  explicit Bootstrap factories.
- Change the console entry point to request a constructed CLI from Bootstrap.
- Remove module-import side effects and compatibility imports from the CLI entry
  point where characterization proves they are unnecessary.
- Retain existing use cases and adapters temporarily; this phase changes
  construction, not business behavior.

### Boundaries

- Do not introduce a dependency-injection framework or service locator.
- Do not move Domain, persistence, or CLI feature modules yet.
- Do not alter command names, options, output, or workspace files.

### Focused verification

- Importing the CLI performs no filesystem, keyring, network, or telemetry I/O.
- Bootstrap construction is deterministic from explicit inputs.
- Commands obtain collaborators through context/factories rather than importing
  `RoadmapCore` or concrete gateways.
- Installed `--help` and `--version` remain independent of workspace state.

### Exit condition

The installed CLI is composed through Bootstrap, all public behavior matches
the baseline, and the architecture violation baseline has shrunk or stayed
constant.

## Phase 4 — extract Domain and Application contracts

### Objective

Create the framework-free business kernel and narrow use-case contracts that
all later vertical slices will use.

### Work

- Define opaque stable IDs, titles/names, workflow status, retention lifecycle,
  timestamps, priority, and typed relationship values in Domain.
- Define Issue, Project, and Milestone aggregate invariants without Pydantic,
  Click, paths, SQLite rows, provider IDs, logging, or global time.
- Define typed Domain failures and Application failure categories.
- Define Application request/response DTOs, clocks, repository capabilities,
  unit of work, projection maintenance, and local Git-inspection ports.
- Inventory and map existing model fields; preserve unknown canonical fields at
  the document boundary rather than adding them to Domain without meaning.
- Add exhaustive transition tables for workflow and retention state.

### Boundaries

- Contracts and pure behavior only; no CLI route switches.
- No generic CRUD repository, backend, gateway, manager, or universal Result
  abstraction.
- One port represents one capability required by a concrete retained use case.

### Focused verification

- Domain imports only the standard library and Domain.
- Application imports only Domain and Application.
- Table tests cover every permitted and rejected lifecycle transition.
- Stable IDs survive rename, reassignment, close, archive, and restore.
- Domain tests require no filesystem, database, Click, Pydantic, Git, or network.

### Exit condition

The target inward contracts are stable enough to support persistence and CLI
slices without leaking a boundary type inward.

## Phase 5 — implement canonical persistence and projection maintenance

### Objective

Implement one safe persistence boundary in which Markdown/YAML is authoritative
and SQLite is a disposable, one-way projection.

### Work

- Implement outbound document mappings between canonical frontmatter/body and
  Domain/Application types while preserving supported unknown fields and
  user-authored Markdown.
- Implement workspace-scoped locking, optimistic content checks, atomic
  same-filesystem replacement, multi-document transaction intent, and
  deterministic recovery.
- Implement repository capabilities and the Application-owned unit of work.
- Implement SQLite projection refresh after canonical commits.
- Detect manual and Git-authored canonical changes by schema/content identity
  and perform incremental refresh or full rebuild.
- Treat missing, stale, corrupt, or incompatible SQLite as rebuildable derived
  state; never use it to overwrite canonical documents.
- Characterize and reuse safe existing local file-to-SQLite behavior only after
  separating it from remote-sync abstractions.

### Boundaries

- Support the current canonical layout during this phase; the versioned path
  migration occurs in Phase 9.
- No remote/provider synchronization, generic sync backend, or second writable
  source.
- Projection failure cannot roll back a successful canonical commit.

### Focused verification

- Repository contract tests cover valid, malformed, unknown-field, Unicode,
  duplicate, missing, and externally edited documents.
- Failure injection at each write stage recovers to the complete old or new
  canonical state.
- Concurrent writers and unexpected external edits produce conflicts rather
  than silent overwrite.
- Delete, corrupt, truncate, and schema-age SQLite; rebuild repeatedly and
  compare semantic query results and canonical digests.
- Force projection refresh failure after canonical commit and verify stale-state
  reporting plus later recovery.

### Exit condition

Canonical and projection contract suites pass, no test treats SQLite as
authority, and the cumulative installed journeys remain unchanged.

## Phase 6 — migrate issue queries

### Objective

Move read-only issue behavior through Domain, Application, Bootstrap, document
storage, and SQLite without changing its approved CLI contract.

### Work

- Implement issue lookup, list, filter, search, sort, and detail use cases.
- Resolve unambiguous CLI ID prefixes at the inbound boundary and pass complete
  IDs inward.
- Make lifecycle scope explicit for visible, closed, archived, and all-state
  queries.
- Use SQLite to select candidate IDs where valid, then load canonical documents;
  retain a correct full-scan fallback.
- Route issue `list`, `view`, and lookup behavior through the new use cases.
- Preserve deterministic plain, rich, JSON, and CSV contracts selected in
  Phase 1.
- Delete superseded issue read services, coordinators, gateways, presenters,
  and duplicate tests as each command switches.

### Boundaries

- No issue mutation migration in this phase.
- No output formatter inside Domain or Application.
- Do not retain the old query path as a fallback after a command switches.

### Focused verification

- Golden contract tests cover every supported filter, empty result, ordering,
  Unicode, archived lookup, ambiguous prefix, malformed canonical file, stale
  projection, and structured output.
- Query equivalence holds with healthy, absent, and rebuilt SQLite.
- Old and new paths are compared before cutover; only the new path remains
  afterward.

### Exit condition

Every retained issue query has one production path through the target
architecture and passes installed-artifact journeys.

## Phase 7 — migrate issue mutations and relationships

### Objective

Move the complete retained issue lifecycle and cross-issue behavior onto the
safe unit-of-work boundary.

### Work

- Implement create, update, prioritize, assign, start, progress, block,
  unblock, review, close/reopen, archive/restore, and approved delete/purge
  behavior.
- Implement retained dependency, comment, branch/reference, and evidence
  relations according to the Phase 1 disposition.
- Validate single-aggregate rules in Domain and cross-aggregate existence,
  cycles, uniqueness, and write scope in Application.
- Refresh SQLite only after canonical commit.
- Route each retained issue command through Bootstrap and the new use case.
- Delete superseded mutation services, CRUD bases, coordinators, repositories,
  fixers, and duplicate tests command by command.

### Boundaries

- No physical file move for close, archive, restore, rename, assignment, or
  milestone changes in the target behavior.
- Destructive operations require the approved preview/confirmation contract.
- An invalid transition or relationship leaves canonical and derived state
  unchanged.

### Focused verification

- Exhaustive transition and idempotency tests.
- Dependency tests for missing targets, self-links, duplicates, cycles, closed
  and archived targets.
- Multi-document failure injection for assignment and relationship changes.
- Installed lifecycle journey from creation through archive and restoration.
- Canonical Git diffs show content changes rather than lifecycle path moves once
  the target layout is active.

### Exit condition

The retained issue journey has one target implementation, all mutation and
recovery contracts pass, and obsolete issue paths are gone.

## Phase 8 — migrate projects, milestones, and planning views

### Objective

Complete the smallest coherent planning product on the same architecture.

### Work

- Implement retained project and milestone create, list, view, update, assign,
  close, archive, restore, and approved purge use cases.
- Calculate milestone/project progress from canonical linked issues through one
  Application-owned policy.
- Migrate retained board, daily, dependency/critical-path, and planning views.
- Make lifecycle and time scopes explicit; inject the clock.
- Route inbound commands and presenters through the new use cases.
- Delete superseded planning services, calculation paths, CRUD bases,
  coordinators, gateways, and duplicate tests.

### Boundaries

- Project or milestone archive does not silently cascade to issues.
- Derived counts are not persisted as independent authority.
- No analytics or predictive framework is introduced.

### Focused verification

- Progress reconciles after issue creation, assignment, transition, manual edit,
  archive, restore, and projection rebuild.
- Empty, overdue, partial, closed, and archived planning fixtures.
- Cross-aggregate transaction interruption and recovery.
- Installed project/milestone journey with parsed structured output.

### Exit condition

Issues, projects, milestones, and retained planning views share one domain and
calculation model with no legacy production path.

## Phase 9 — migrate configuration, schemas, paths, and lifecycle storage

### Objective

Safely upgrade existing 0.1.1 workspaces to versioned configuration and stable
ID-based canonical paths.

### Work

- Classify every configuration key by project, user, secret, environment, or
  invocation scope and define an immutable resolved snapshot.
- Remove ambient settings access from migrated code.
- Define workspace and canonical schema versions.
- Implement migration preflight, dry-run, backup/recovery guidance, duplicate
  and collision detection, unsupported-future-version rejection, and
  idempotency.
- Move canonical entities to flat `<collection>/<complete-id>.md` paths while
  preserving every existing ID, relationship, timestamp, supported unknown
  field, and user-authored body.
- Replace active/archive directory moves with lifecycle metadata.
- Discard and rebuild projections only after canonical migration commits.
- Provide explicit failure and rollback guidance; never migrate on ordinary
  read.

### Boundaries

- No legacy ID regeneration or heuristic duplicate selection.
- No secrets, machine paths, Git remotes, or transport policy in project config.
- Migration operates on an enumerated write set under the unit of work.

### Focused verification

- Dry-run is byte-for-byte non-mutating.
- Repeated migration is idempotent.
- Inject failure at every migration stage and recover deterministically.
- Test collisions, identical/non-identical duplicates, archive reconciliation,
  future schema, permission loss, and corrupt projection.
- Compare pre/post semantic entities and supported user content; verify stable
  IDs and relationships.
- Exercise the sanitized 0.1.1 compatibility fixture through dry-run, migration,
  reopen, projection rebuild, and retained journeys.

### Exit condition

Supported old workspaces migrate safely and explicitly; new workspaces use the
target layout and configuration; normal reads never rewrite canonical files.

## Phase 10 — migrate reporting, health, recovery, and local Git awareness

### Objective

Finish retained boundary features without allowing them to bypass Application
or mutate canonical state unexpectedly.

### Work

- Migrate deterministic export/report queries and safe overwrite behavior.
- Separate health detection from repair; make every retained fix previewable,
  targeted, recoverable, and followed by validation.
- Migrate backup cleanup and interrupted-transaction recovery.
- Retain only explicit local Git inspection and ordinary external references
  through narrow ports.
- Bound Git subprocess arguments, repository scope, timeout, cancellation, and
  error translation.
- Remove provider credential behavior and network dependencies with no retained
  contract.
- Keep logging/telemetry outside Domain/Application and prevent stdout or secret
  leakage.

### Boundaries

- Roadmap does not fetch, pull, merge, rebase, push, authenticate a remote, or
  reconcile provider entities.
- Health repair never writes from SQLite back into canonical files.
- Machine-readable stdout contains no progress, logging, or Rich markup noise.

### Focused verification

- Golden JSON/CSV tests for empty, Unicode, filtered, null, and error cases.
- Detector/fixer tests for healthy, damaged, ambiguous, permission-denied,
  interrupted, dry-run, and repeated states.
- Git tests for missing executable, dirty tree, nested worktree, unusual path,
  timeout, cancellation, and command failure.
- Run retained core journeys with network access blocked.

### Exit condition

Reporting, diagnosis, recovery, and retained local Git behavior use explicit
boundaries and cannot make derived or remote state authoritative.

## Phase 11 — remove remote/provider synchronization

### Objective

Delete the second distributed-state protocol while retaining the local
canonical-to-SQLite projection pipeline.

### Work

- Remove `roadmap sync`, provider-backed sync commands, GitHub replication,
  baselines, checkpoints, merge engines, conflict reconciliation, provider
  mappings, remote linkage repair, remote sync databases, sync metrics, retries,
  credentials, and configuration.
- Remove the no-op Git sync backend and generic backend factory.
- Delete tests and documentation whose only purpose is approved removed
  behavior; retain or rewrite tests that actually protect canonical-to-SQLite
  refresh, local Git inspection, or ordinary external references.
- Rename retained local behavior to projection refresh, projection rebuild, or
  index maintenance.
- Remove runtime network/provider dependencies that no retained feature uses.
- Add clear 0.2 removal and migration guidance.

### Boundaries

- Do not delete local projection refresh/rebuild behavior.
- Do not delete local Git inspection merely because it shares a legacy module
  with remote sync.
- Do not leave compatibility facades that reconstruct the removed subsystem.

### Focused verification

- Source, CLI, configuration, schema, dependency, and documentation policy tests
  assert the removed remote-sync surface is absent.
- Projection tests from Phase 5 remain unchanged and green.
- Manual/Git-authored canonical edits still refresh SQLite.
- Core journeys pass offline and require no provider credentials.
- Removed commands fail as unknown commands or provide the exact approved
  migration message; no lazy registration warning is emitted.

### Exit condition

Remote/provider synchronization is absent, local projection maintenance remains
fully functional, and every removal is reflected in contracts and docs.

## Phase 12 — dissolve legacy ownership zones and prune dependencies

### Objective

Finish the architecture rather than leaving permanent migration scaffolding.

### Work

- Classify every remaining module under `roadmap.core`, `roadmap.common`,
  `roadmap.infrastructure`, and `roadmap.presentation` by retained behavior.
- Move it to Domain, Application, its owning inbound/outbound adapter, or
  Bootstrap, or delete it.
- Remove duplicate utilities, validators, formatters, error systems, base
  classes, gateways, managers, compatibility imports, and empty packages.
- Remove migration-only adapters after their supported compatibility obligation
  is met or isolate them under the documented migration boundary.
- Reduce runtime dependencies; every remaining dependency receives a named
  adapter/boundary justification.
- Remove the final architecture-baseline entries and forbid reintroduction of
  legacy ownership zones.
- Consolidate documentation sources and remove tracked generated/stale material
  without undertaking a framework redesign.

### Boundaries

- No move-only cleanup without ownership analysis.
- Do not create a new catch-all `shared`, `utils`, `services`, or `managers`
  package.
- Do not delete supported migration readers before the compatibility decision
  permits it.

### Focused verification

- Architecture policy passes with an empty baseline.
- Import-cycle scan passes.
- Package artifact contains only intended modules and data.
- Every runtime dependency is imported by a retained boundary and absent
  dependencies are removed from the lock.
- All cumulative journeys and compatibility fixtures still pass.

### Exit condition

The production tree consists only of Domain, Application, inbound/outbound
Adapters, and Bootstrap; there is one implementation path per retained behavior
and no architecture exceptions.

## Phase 13 — harden, document, and prepare 0.2.0

### Objective

Prove the refactored application from installation and migration boundaries and
prepare—but do not publish—the release without explicit authorization.

### Work

- Run failure-injection, concurrency, projection corruption, migration,
  structured-output, offline, and performance suites at the supported envelope.
- Audit skips, xfails, duplicate tests, assertion-light tests, and stale fixtures.
- Run wheel and source-distribution smoke tests on every supported Python/OS
  combination through CI.
- Verify package metadata, version, changelog, requirements, docs, migration
  guide, removed-feature guide, and CLI help agree.
- Record before/after architecture, module, dependency, test, and performance
  metrics. The production CLOC ratchet remains mandatory but is not used as a
  substitute for correctness, architecture, data safety, or performance.
- Write the portfolio case study around the problem, decisions, migration
  strategy, evidence, and measured simplification.
- Prepare the 0.2.0 release checklist and rollback plan.

### Boundaries

- No feature additions.
- No release publication, tag, push, or version bump without explicit approval.
- No performance optimization without a measured retained-journey bottleneck.

### Focused verification

- Complete checkpoint locally.
- Full supported CI matrix green.
- Fresh 0.1.1 fixture migrates and completes every retained journey.
- Fresh 0.2 workspace completes every retained journey.
- Canonical digests remain unchanged by projection deletion/rebuild.
- Release artifacts import only from their isolated environments.

### Exit condition

The project is ready for a separately authorized 0.2.0 version bump, tag, and
trusted-publishing release.

## Phase sequence and approval points

| Phase | Outcome | Hard stop before next phase |
| --- | --- | --- |
| 0 | Reproducible unchanged baseline | Full suite, artifacts, baseline journeys |
| 1 | Approved public contract | Register/inventory validation and full checkpoint |
| 2 | Enforced architecture ratchet | Negative fixtures, exact baseline, full checkpoint |
| 3 | One composition root | Import-side-effect tests and full checkpoint |
| 4 | Pure Domain/Application contracts | Pure contract tests and full checkpoint |
| 5 | Safe canonical persistence and SQLite projection | Failure injection, rebuild equivalence, full checkpoint |
| 6 | Target issue query path | Query/output contracts and full checkpoint |
| 7 | Target issue mutation path | Lifecycle/recovery journeys and full checkpoint |
| 8 | Target planning path | Aggregate progress journeys and full checkpoint |
| 9 | Versioned migration and configuration | 0.1.1 migration/rollback journey and full checkpoint |
| 10 | Retained operational boundaries | Offline/Git/health/report journeys and full checkpoint |
| 11 | Remote sync absent; local projection retained | Absence policies, projection journeys, full checkpoint |
| 12 | No legacy zones or architecture exceptions | Empty baseline, package audit, full checkpoint |
| 13 | Release candidate proven | Local and remote matrix, migration and artifact evidence |

The hard-stop column is cumulative. Every row also requires production Python
CLOC less than or equal to the preceding accepted row. Tests and documentation
may grow when they add useful evidence; production code cannot grow phase over
phase.

## First execution step

After the maintainer approves this plan, begin only Phase 0. Run the unchanged
baseline checkpoint and return with the evidence. Do not begin requirement
triage or architecture-policy implementation in the same turn.
