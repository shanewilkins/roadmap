# Canonical persistence and projection contract for 0.2

- Status: Phase 5 implemented boundary
- Date: 2026-08-17
- Decisions: ADR-0003, ADR-0005, ADR-0007
- Requirements: TR-002, TR-007, TR-008, TR-029, TR-034

## Authority and direction

Markdown documents with YAML frontmatter under `.roadmap/` are authoritative.
The outbound document repository maps those documents to the Phase 4 Domain
aggregates without allowing paths, YAML values, or SQLite rows into Domain or
Application. A boundary-owned envelope retains supported unknown frontmatter
and user-authored Markdown. A supported read never rewrites its source.

SQLite is a one-way, disposable projection. Its adapter can scan canonical
documents, refresh affected identities, rebuild the complete index, and return
candidate rows. It has no operation that can create or update a canonical
document. Missing, stale, corrupt, truncated, or schema-incompatible projection
state is replaced from canonical documents. Canonical bytes are compared in the
contract suite before and after rebuild.

## Document compatibility

The Phase 5 mapping supports the retained 0.1.1 issue, milestone, project, and
archive directories. Missing legacy schema versions are read as version zero;
new writes declare canonical schema version one. Unsupported future or invalid
versions fail without mutation. Stable IDs, typed owned fields, Unicode,
deferred known fields, and supported unknown fields round-trip. Duplicate IDs,
malformed YAML, invalid required fields, and invalid timestamps fail at the
document boundary.

Phase 5 does not move retained documents into ADR-0010's final flat ID layout.
That explicit migration remains Phase 9 work. New target-adapter documents use
an ID filename while existing documents retain their current path.

## Mutation protocol

Every target mutation enters a canonical unit of work and acquires one
workspace advisory lock. The unit of work reads and records the content digest
of each document in its write set. Commit rejects a digest mismatch as external
concurrency rather than overwriting a manual or Git-authored edit.

Before canonical replacement, the adapter serializes the whole write set and
records durable before/after transaction intent under `.roadmap/db/transactions`.
Each target replacement uses a temporary file on the same filesystem, flushes
its content, atomically replaces the target, and flushes the containing
directory. An ordinary failure restores the complete old write set. A process
interruption leaves durable intent; the next locked mutation deterministically
rolls the complete new write set forward. Transaction paths are resolved and
required to remain inside the workspace, including through symlinks.

Canonical commit precedes projection refresh. Projection failure marks the
projection stale and cannot roll back canonical success. A later maintenance
operation rebuilds the projection.

## SQLite connection ownership

The retained database manager owns every connection it creates, including
connections created in worker threads. Explicit `close()` closes the complete
registry and is idempotent. A weak finalizer closes the same registry when an
embedding host abandons an owner, including through reference cycles. A
connection that fails during configuration is closed before its error escapes.
Direct SQLite call sites use closing contexts, and the new projection opens a
scoped connection for each operation.

The Phase 5 full-suite gate promotes both `ResourceWarning` and Pytest's
unraisable-exception wrapper to errors. Zero unclosed SQLite warnings is a
release condition, not a filtered warning exemption.

## Deferred route migration

The target adapters are not yet the command query path. Phases 6 through 8 move
issue, milestone, and project slices through the new ports. The retained local
file-to-SQLite refresh remains available during that migration; provider and
remote synchronization removal remains Phase 11 work.
