# ADR-0003: Use canonical files with rebuildable projections

- Status: Accepted
- Date: 2026-08-10
- Scope: Persistence authority, document storage, indexing, and schema evolution

## Context

Roadmap is a file-first application, but the current implementation also uses
SQLite state and filesystem location to answer some questions about an entity.
Without an explicit authority rule, canonical documents, database records,
caches, and directory placement can disagree and behave as competing sources of
truth.

The persistence boundary must preserve Roadmap's Git-native properties while
supporting fast queries, safe schema evolution, and recovery from stale derived
state.

## Decision

Human-readable documents under the repository-local `.roadmap/` directory are
the sole canonical representation of Roadmap entities and project
configuration. Entity documents use Markdown with YAML frontmatter unless a
separate accepted decision selects another human-readable format for a specific
artifact.

Canonical persistence follows these rules:

- Each independently addressable entity has one canonical document.
- Every entity has a stable opaque ID represented in its document and stable
  physical location.
- Canonical documents contain the data required to reconstruct application
  state without SQLite, a cache, or a network service.
- Reads never rewrite documents merely because an older supported form was
  encountered.
- Writes preserve user-authored content and unknown fields when doing so is
  compatible with a valid schema.
- Canonical schemas declare a version. Unsupported future versions fail with an
  actionable error rather than being guessed at or rewritten.
- Schema upgrades are explicit, reviewable migrations with preflight and
  recovery behavior. They are not side effects of normal reads.

SQLite databases, search indexes, analytics tables, caches, and materialized
views are projections. They may improve query speed but are never authoritative.

- A projection can be deleted and rebuilt entirely from canonical documents.
- A missing, stale, incompatible, or corrupt projection triggers a rebuild or a
  clear degraded-mode path.
- When a projection disagrees with a canonical document, the document wins.
- Projection schemas are internal implementation details unless explicitly
  declared public.
- A successful canonical write is not rolled back merely because projection
  refresh failed; the projection is marked stale and rebuilt.

Application owns persistence ports expressed in domain terms. Outbound
persistence adapters implement document storage and projections. Application
and Domain do not depend on paths, parsers, SQLite schemas, or filesystem
libraries.

## Query model

Normal list, search, reporting, and filtering operations may use a projection to
identify matching entity IDs and then load only the canonical documents needed
by the use case. A full document scan remains the correctness fallback and the
source for rebuilding projections.

The projection must record enough schema and content identity to detect that it
is stale. Its invalidation strategy is an adapter concern, but false freshness
is not acceptable.

## Consequences

### Positive

- Users retain portable, diffable, inspectable project state.
- Git history remains meaningful and sufficient to exchange canonical state.
- Database corruption cannot destroy the source of truth.
- Performance optimizations can evolve without changing the domain or file
  contract.
- Tests can establish correctness from canonical fixtures without hidden
  database setup.

### Costs and constraints

- Projection rebuilding must be reliable and tested at realistic data sizes.
- Document migrations require explicit compatibility policy and tooling.
- Persistence adapters must preserve content they do not own where the schema
  permits it.
- Features cannot write only to SQLite or another cache.

## Alternatives considered

### Make SQLite canonical

Rejected because it would weaken human readability, direct editing, Git diffs,
and repository portability.

### Treat files and SQLite as co-equal

Rejected because two authorities require reconciliation and create ambiguous
failure recovery.

### Parse every document for every query

Rejected as the only query strategy because predictable interactive performance
should not depend on repeatedly parsing the entire working set.

## Related decisions

- ADR-0002 makes Git responsible for exchanging canonical repository state.
- ADR-0005 defines atomic writes and projection refresh ordering.
- ADR-0007 defines schema compatibility and migration obligations.
- ADR-0008 prevents lifecycle state from changing canonical file location.

## Migration boundary

This ADR does not select the final projection implementation or change current
files. The target file schema, migration tooling, and projection rebuild path
require separately scoped implementation work.

