# Changelog

All notable changes to Roadmap CLI are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Reject unresolved Git conflict hunks in canonical Markdown bodies on ordinary
  reads, using the same diagnosis as health. Verify installed two-clone
  close/merge/pull and resolved retry with stale or missing SQLite projections.
- Derive the default project name from the selected workspace's parent directory
  when initializing with `--workspace`, including dry runs from another directory.
- Use the nearest initialized default workspace for commands run in subdirectories
  instead of treating each current directory as a separate uninitialized root.
- Normalize configured identity and Git-name fallback consistently with explicit
  assignees. Daily and assignee-filtered views include legacy padded assignments
  without rewriting their canonical records. Missing-identity diagnostics now
  give executable setup commands; document the offline onboarding path.

### Added

- Add selected complete GitHub issue import with online preview and explicit
  atomic apply. Reuse repository-qualified local identities across closed and
  archived records, capture immutable attributed source revisions, and leave
  local planning untouched. Repeat imports do not duplicate records or revisions.
- Verify SQLite projection connections close on successful operations and on
  schema, insert, commit, refresh and query failures. Treat resource leaks and
  unraisable exceptions as test failures across supported Python versions.
- Add explicit outbound GitHub closure publication from canonical Git HEAD:
  offline JSON preview, repository-qualified opt-in, completed/not-planned
  dispositions, committed evidence links, and safe retry after partial failures.
- Add a serialized default-branch Action to publish opted-in closures after push
  or merge, without local receipt commits or inbound reconciliation.
- Add bounded real-process regression coverage for block-with-reason hangs
  reported in GitHub #3756; current 0.3.1 reproduction cases complete successfully.

## [0.3.1] - 2026-10-08

### Added

- Add CI gates for high-confidence dead code and active documentation links,
  with negative fixtures proving rejected inputs.

- Add branch-outcome regressions for migration refusals, canonical transaction
  failure/retry, planning idempotency, aggregate invariants and scoped issue-list
  workload output.

- Add scoped requirement verification records, fail-closed evidence policy and
  an executable maintainer handover runbook with a current release checklist.

- Add explicit workspace selection, JSON entity inspection with issue history,
  project/milestone ID-only creation, nullable-field clearing, issue due dates and
  label edits, project owner/priority controls, and stderr-only operational verbosity.
- Add a reviewed command/option evidence matrix and a guard against CLI drift.

- Add global `--debug` tracebacks for unexpected CLI failures. Configuration
  access errors no longer silently use defaults; command import failures remain
  errors. Log projection refresh exceptions with Python logging and send repair
  warnings to stderr.
- Show candidate IDs and labels for ambiguous issue/project/milestone lookups.
- Explain effective configuration values, owning scope, and default/configured
  source with `config explain KEY [--format json]`.
- Print only the created issue ID with `issue create --print-id`, keeping
  warnings and branch notifications on stderr.
- Show repair-preview commands in plain health output and document built-in
  shell completion.

### Changed

- Replace deprecated Click filesystem isolation in tests with pytest-managed
  temporary workspaces, remove retired coverage exclusions, and enable Bandit's
  try/except/pass rule instead of suppressing it globally.

- Raise the statement-coverage floor to 90% after real-storage CLI safety journeys.

- Replace the hand-written import graph checker with Import Linter contracts
  and narrow namespace/core dependency guards; raise the coverage floor to 87%.

- Standardize type checking on ty and remove Pyright and unused pytest plugins;
  consolidate development dependencies into the dev extra.
- Run architecture checks in pre-commit, retain CI coverage evidence, and
  require the full CI workflow before a release can publish.

### Fixed

- Correct the empty issue-list creation hint to include the required `--title`
  option, with a CLI regression proving the suggested command works.

- Refuse migration when canonical directories cannot be enumerated or a personal
  configuration schema version is boolean; protect changed migration previews
  and prove projection failure rollback/retry with regression tests.
- Distinguish unpublished master behavior from PyPI 0.3.0 and correct the package
  documentation URL to the actual default branch.

- Refuse dry-run recovery writes and parent-close guard bypasses; reject explicit
  branch options without branch action before canonical writes.
- Preserve literal machine output, independent sort directions and empty CSV
  headers; validate output options and export enums even when results are empty.
- Honor empty-analysis destinations and health summary-only across formats.
- Require explicit bounded health repair targets. Prefer `--format`, `--yes` and
  `milestone progress`; warn on deprecated spellings through 0.3, retire in 0.4.
  Archive keeps a lifecycle override; its legacy force-as-consent shortcut is
  explicitly deprecated, as is project close's shortcut. Init force is deprecated
  because initialization is idempotent and never overwrites canonical data.

- Keep broken-reference health findings visible when filtering by entity, with
  workspace-relative scopes and an accurate unhealthy exit code.
- Validate manually edited configuration values using the same type rules as
  scoped writes; reject boolean schema versions without rewriting input.
- Treat duplicate project/milestone names as ambiguous and list candidates.

- Preserve successful canonical mutation results when post-commit cleanup or
  projection stale-marker persistence fails; retry journals on reopen.
- Reject symlinked backup directories/files and anchor cleanup deletion to a
  directory descriptor, including revalidation after confirmation.
- Fail canonical scans on unreadable directories instead of treating them as
  empty, and block projection repair when enumeration fails.

- Refuse recovery preview and projection repair when transaction journals
  cannot be inspected, instead of silently treating them as absent.
- Validate complete recovery journals and snapshot integrity before replay;
  preserve post-interruption manual edits and reject unsafe snapshot paths.
- Release workspace locks when recovery or lock-metadata persistence fails.
- Persist transaction snapshots and preparation/cleanup boundaries; preserve
  rollback intent when an ordinary write failure cannot finish restoration.
- Rebuild missing projections when retrying a migration interrupted after
  canonical commit.
- Explicitly select locked development dependencies for CI and pre-commit
  checks and the documented contributor commands.

### Added

- Reliability coverage for deletion guards, reciprocal dependency edits,
  populated backup cleanup, malformed canonical input, and repair refusal.
- A maintainer continuity/inactivity policy and a review closeout record that
  distinguishes local verification from remote CI and independent review.
- A required CI audit of locked runtime/development dependencies using pinned
  pip-audit, in addition to GitHub's Dependabot monitoring.
- Reliability tests covering actual process termination, separate writers,
  filesystem replacement failures, recovery conflicts, and installed CLI
  repair, plus a recovery guide and guarantee-to-test evidence map.

## [0.3.0] - 2026-09-02

### Changed

- Migrated static type checking from Pyright-only to `ty` running alongside
  Pyright, both enforced in CI and pre-commit; aligned their configured
  Python-version floor with the declared `>=3.12` support range.
- Reduced cyclomatic complexity across the codebase and enforced a
  xenon B-or-better gate (absolute, per-module, and average) in CI and
  pre-commit.
- Raised the enforced test coverage floor from 78% to 85%, backed by a
  targeted test-coverage sweep (CLI output formatting and issue query
  presentation) that reached 85.70%.
- Reduced DRY violations identified during the complexity-reduction pass.
- Enabled GitHub's native Dependabot vulnerability alerts for the repository.

### Fixed

- Removed the stale, inaccurate `.env.production` file (unverifiable "0 known
  CVEs" claim, an obsolete `poetry install` reference, and unused
  environment variables that nothing in the codebase reads).
- Removed the stale, tracked `output.txt` pytest-output artifact from version
  control.
- Fixed a broken `SECURITY.md` reference to a nonexistent developer-notes
  file; it now points to the ADR that documents credential handling.

### Removed

- Removed `.env.production` and `output.txt` from version control (see
  Fixed, above).

## [0.2.0] - 2026-08-27


### Added

- Added explicit `roadmap migrate` preflight, dry-run, confirmed execution,
  structured output, recovery, and idempotent rerun for supported 0.1.1
  workspaces.
- Added versioned workspace/document schemas, stable entity IDs, scoped
  configuration, deterministic JSON/CSV output, read-only health diagnosis,
  previewable repair, and explicit local Git status/branch/reference commands.
- Added architecture, test-quality, package-installation, compatibility,
  failure-injection, concurrency, corruption, migration, offline, and measured
  performance gates.

### Changed

- Canonical Markdown/YAML documents are now the sole data authority. SQLite is
  a disposable query projection refreshed or rebuilt only from those files.
- Projects, milestones, and issues use flat stable-ID paths. Lifecycle state is
  metadata rather than a physical archive-directory contract.
- New IDs use complete UUID4 values; migration preserves existing IDs and
  user-authored content.
- The package now has one Domain/Application/Adapters/Bootstrap architecture,
  one configuration path, one persistence path, and one implementation for
  each retained CLI journey.
- Supported runtimes now include Python 3.12 through 3.14 on macOS and Linux;
  CI verifies the full Python range and installed artifacts on Ubuntu x64 and
  macOS ARM64.
- Machine-readable stdout is isolated from diagnostics and confirmations on
  stderr.

### Removed

- Removed provider-backed synchronization, GitHub entity replication,
  Roadmap-owned credentials, connectivity/setup handlers, provider baselines,
  reconciliation databases, and sync metrics. Ordinary Git transport remains
  outside Roadmap and local file-to-SQLite projection maintenance remains.
- Removed the legacy `core`, `common`, `infrastructure`, `presentation`, and
  superseded adapter ownership zones, along with duplicate configuration,
  health, export, persistence, and compatibility implementations.
- Removed claimed features that did not belong to the retained product,
  including hosted dashboards, predictive analytics, OAuth, and generated API
  documentation stacks.

### Migration

- Existing 0.1.1 workspaces must run `roadmap migrate --dry-run` and review the
  report before `roadmap migrate --yes`.
- Migration rewrites canonical entities to stable paths, externalizes user
  preferences, removes legacy credential fields, and rebuilds SQLite without
  treating it as authority. See `docs/user_guide/MIGRATING_TO_0_2.md`.

## [0.1.1] - 2026-08-09

### Fixed

- Removed the unrelated `roadmap` PyPI distribution from runtime dependencies;
  it shadowed this project's package and broke the console command.
- Moved development and documentation tooling out of runtime dependencies.
- Read the installed version from distribution metadata and added clean wheel
  and source-distribution smoke tests.
- Corrected supported Python/platform declarations, repository URLs, and
  installation guidance.

## [0.1.0] - 2026-05-18

### Changed

- Reset the public version from premature 1.x tags to 0.1.0 so package versions
  accurately communicate pre-1.0 compatibility and maturity.

## Pre-reset 1.x tags

Tags numbered 1.0.0 through 1.0.2 predated the maturity reset. Their release
notes contained aspirational and unverified feature, compatibility, coverage,
security, and performance claims, so they are not a description of the current
product contract. Git history remains available for provenance; supported
behavior begins with the honest 0.1.x line above.
