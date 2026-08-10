# ADR-0005: Make writes consistent under concurrency and failure

- Status: Accepted
- Date: 2026-08-10
- Scope: Mutation boundaries, locking, atomic replacement, and crash recovery

## Context

Roadmap mutations may touch one or more canonical documents and a rebuildable
projection. Direct file writes, file moves, and best-effort cleanup can leave
partial state when a process crashes or when two commands modify the same
workspace concurrently.

A single filesystem does not provide an atomic transaction across several
files. The architecture therefore needs an explicit consistency protocol rather
than assuming a sequence of renames is one transaction.

## Decision

Application owns a Unit of Work boundary for every mutating use case. The
outbound persistence adapter implements that boundary for canonical files.

### Concurrency

- Mutating operations acquire one exclusive workspace-scoped lock before
  reading the state they intend to change.
- Reads that must observe a multi-document invariant use the corresponding
  shared lock or an equivalent consistent snapshot supplied by the adapter.
- Lock metadata supports diagnosis and safe stale-lock recovery; a process does
  not silently steal a lock that may still be active.
- Before commit, the adapter verifies that canonical documents in the write set
  have not changed since they were read. Unexpected changes abort with a
  conflict instead of overwriting another writer.
- Git working-tree changes made outside Roadmap are external concurrency. They
  are detected through content identity, not resolved by the application.

### Single-document writes

- Validate and serialize the complete new document before replacing the old
  document.
- Write temporary content on the same filesystem as the target.
- Flush required content before an atomic replacement.
- Preserve or restore the prior canonical document if commit cannot complete.

### Multi-document writes

- Determine and validate the complete read and write set before mutation.
- Stage all replacement documents before changing canonical paths.
- Record sufficient durable transaction intent to detect an interrupted commit.
- Apply individual canonical replacements atomically.
- On startup or before another mutation, detect incomplete transactions and
  deterministically roll them forward or restore the prior complete state.
- Report recovery rather than silently ignoring an incomplete transaction.

The exact journal representation is an adapter implementation detail. Its
observable guarantee is that a supported use case resolves to the complete old
state or complete new state after recovery, never a permanently accepted
partial state.

### Projection ordering

Canonical documents commit first. Derived projections update only after the
canonical commit succeeds. Projection failure marks the projection stale and
does not invalidate a successful canonical transaction; rebuilding restores
consistency.

Backups and transaction journals are recovery mechanisms, not additional
sources of truth.

## Consequences

### Positive

- Concurrent commands do not silently overwrite one another.
- Interrupted multi-file operations have a deterministic recovery path.
- Canonical state remains authoritative even when projection refresh fails.
- Application use cases express transactional intent without depending on
  filesystem mechanisms.

### Costs and constraints

- Multi-document writes require staging and recovery metadata.
- Lock behavior and crash recovery need cross-platform tests.
- Mutating use cases must identify their complete consistency boundary.
- The implementation must distinguish a stale lock from a live slow operation.

## Alternatives considered

### Best-effort sequential writes

Rejected because failures can leave permanent partial state with no reliable
way to determine the intended result.

### Make SQLite the transaction coordinator and authority

Rejected by ADR-0003 because canonical project state must remain reconstructable
from human-readable files.

### Rely on Git to repair local concurrent writes

Rejected because Git records repository history and exchanges commits; it does
not serialize concurrent Roadmap processes inside one working tree.

## Related decisions

- ADR-0003 defines canonical documents and rebuildable projections.
- ADR-0008 removes routine archive and restore file moves from lifecycle changes.

## Migration boundary

This ADR defines guarantees, not a specific lock or journal implementation.
Implementation must begin with failure-injection and concurrency contract tests.

