# Changelog

All notable changes to Roadmap CLI are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Standardize type checking on ty and remove Pyright and unused pytest plugins;
  consolidate development dependencies into the dev extra.
- Run architecture checks in pre-commit, retain CI coverage evidence, and
  require the full CI workflow before a release can publish.

### Fixed

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
