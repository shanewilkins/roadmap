# Changelog

All notable changes to Roadmap CLI are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
