# Roadmap 0.2 public contract

- Status: Accepted
- Date: 2026-08-16
- Applies to: the 0.2 refactor
- Detailed register: [compatibility-inventory-0.2.csv](compatibility-inventory-0.2.csv)

This document fixes the product boundary before production code is simplified.
The CSV register is authoritative for individual commands, options,
configuration keys, canonical fields, output shapes, exit categories, Git
behavior, and migration obligations.

## Product boundary

Roadmap is a repository-local, file-first planning CLI. Canonical Markdown and
YAML files are durable user data. SQLite is a disposable local projection used
to query and validate those files; rebuilding that projection is not remote
synchronization. Git is the only collaboration and network synchronization
mechanism: users fetch, merge or rebase, and push with ordinary Git.

The 0.2 product supports:

- safe workspace initialization and reopening;
- issue capture, discovery, lifecycle, dependencies, progress, and comments;
- project and milestone planning with derived progress;
- daily, status, critical-path, health, and structured-output workflows;
- explicit local Git inspection, branch creation, and issue-to-branch
  references; and
- diagnosis, previewable repair, canonical-file observation, and rebuilding a
  missing or corrupt SQLite projection.

Managing requirements as first-class application entities is a plausible
future feature, but it is not part of 0.2. The CSV requirement registers remain
governance artifacts under `docs/requirements/`.

## Compatibility vocabulary

Every inventoried surface has one disposition:

- **Preserve** retains its path and documented meaning. Presentation prose,
  colors, spacing, and incidental implementation details are not stable.
- **Replace** retains the user intent but adopts the target contract and
  migration guidance recorded in the inventory.
- **Remove** is absent from the 0.2 public surface and has explicit replacement
  or retirement guidance.
- **Internal** may change without compatibility guarantees because it is
  derived, provider-specific, or an implementation detail.

## Command decisions

The issue, milestone, project, status, today, analysis, health, local Git, and
data-export command families remain. The real issue discussion interface is
`roadmap issue comment add/list`; the separate top-level `roadmap comment`
family is an unfinished duplicate and is removed.

The following behaviors are intentionally replaced:

- initialization loses provider, credential, and sync-backend options;
- configuration converges on one versioned typed schema with declared scopes;
- archive and restore change lifecycle metadata instead of physically moving
  canonical files;
- list commands lose provider-specific columns and legacy export shortcuts;
- broad cleanup becomes diagnosed, scoped health repair; and
- health and export output adopt documented, versioned machine schemas.

The following behaviors are intentionally removed:

- `roadmap sync`, `roadmap git sync`, sync metrics, provider reconciliation,
  provider issue lookup/link/unlink, and provider link validation;
- Roadmap-owned authentication, tokens, and credential setup;
- automatic Git hooks and commit-message-driven mutation;
- the placeholder `data generate-report` command; and
- the nonfunctional top-level comment commands.

Remote provider identifiers may remain as ordinary text or URLs in canonical
content. Roadmap 0.2 does not own, validate, or reconcile them.

## Configuration contract

Configuration has exactly three declared concerns: shared project policy,
personal user preferences, and runtime-only inputs. One bootstrap path parses
and validates configuration, then injects narrow immutable values into the
application. Domain code does not read environment variables, global files, or
process state.

Provider credentials, remote-sync settings, automatic-hook settings, and
machine-specific paths are removed from shared project configuration. The
inventory records the disposition and migration destination of every currently
recognized key.

## Data and identity contract

Canonical files are authoritative. Stable IDs, supported lifecycle values,
meaningful user-authored content, and relations expressed by stable ID are
compatibility obligations. SQLite tables, caches, computed progress, resolved
names, file paths, and provider synchronization metadata are projections or
internal state and may be regenerated or removed.

Canonical paths become stable-ID based. A 0.1.1 workspace is upgraded through
an explicit, versioned, idempotent migration with preview, backup, recovery,
and rejection of unsupported future schemas. Migration must preserve semantic
content and stable identity; it need not preserve obsolete physical layout or
projection bytes.

## Output and failure contract

Human-readable output preserves meaning, not exact Rich styling. JSON and CSV
are public machine contracts. Successful machine output is written only to
stdout; diagnostics go to stderr. JSON list output uses one documented envelope
and version, and CSV preserves its documented header order.

Process status is `0` for success, `1` for an application failure, and `2` for
Click-compatible command-usage errors. Domain, validation, storage, Git, and
configuration failures must map to a stable public category and actionable
message without exposing a traceback during ordinary use.

## Evolution rules

Phases may simplify only according to the inventory. A missing current command,
configuration key, or canonical field fails the policy test. Removing a public
surface requires its recorded guidance, tests for intentional absence, and
release notes. Undocumented internals are not promoted into public promises by
their mere existence in the 0.1.1 implementation.
