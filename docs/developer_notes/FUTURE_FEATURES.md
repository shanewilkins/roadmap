# Product direction

This file no longer maintains a speculative version-by-version feature list.
The authoritative planning inputs are:

- the [requirements registers](../requirements/README.md);
- the [0.2 public contract](../architecture/public-contract-0.2.md);
- the [0.2 architecture plan](../architecture/roadmap-0.2.md); and
- the [phased execution plan](../architecture/refactor-execution-plan.md).

## 0.2 focus

Roadmap 0.2 makes the existing local, file-first product smaller and reliable:
stable identity, canonical files, rebuildable SQLite projections, explicit
lifecycle semantics, typed configuration, predictable errors and structured
output, safe migration, and a disciplined dependency structure.

Provider synchronization, Roadmap-managed credentials, automatic Git hooks,
and commit-message mutation are outside the 0.2 product boundary.

## Post-0.2 candidates

The registers deliberately defer two directions for later product decisions:

- reversible Git-hook and explicit commit-reference automation; and
- requirements as first-class repository-native application entities.

Deferred means uncommitted. A candidate becomes planned only through the
governed requirement lifecycle and a compatible architecture decision.
