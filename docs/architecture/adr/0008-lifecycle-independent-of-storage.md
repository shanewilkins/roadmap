# ADR-0008: Separate entity lifecycle from physical storage

- Status: Accepted
- Date: 2026-08-10
- Scope: Closing, archiving, restoring, purging, paths, and query visibility

## Context

Roadmap currently distinguishes closing from archiving. Closing changes workflow
status while keeping an issue in the active tree. Archiving later moves its file
to a separate archive tree and records archive state.

The physical move was intended to reduce normal scan time by reducing the number
of files in the active directory. It also makes mutable business state part of
the storage address. Lookup must search multiple trees, archive and restore
create Git path churn, partial moves can create duplicates, and archive state
can disagree between metadata and location.

ADR-0003 provides a rebuildable projection for query performance, so lifecycle
state no longer needs to serve as a directory-level indexing strategy.

## Decision

Entity lifecycle is metadata and does not determine canonical physical
location.

### Workflow and retention are separate

Closing is a workflow transition. Archiving is a reversible visibility and
retention transition. They are independent dimensions:

```text
Workflow:  todo -> in-progress -> closed
Lifecycle: visible <-> archived -> purged
```

- Closing does not archive or move an entity.
- Archiving does not replace the entity's workflow status.
- Restoring makes an archived entity visible while preserving its workflow
  status.
- Archive state is represented by lifecycle metadata such as `archived_at` and,
  when useful, an archive reason.
- The target model does not use both an `ARCHIVED` workflow status and an
  `archived` boolean to represent the same lifecycle fact.

### Stable paths

- Closing, reopening, archiving, restoring, renaming, and reassigning an entity
  do not move its canonical document.
- Mutable business fields such as title, status, milestone, assignee, or archive
  state do not determine a canonical path.
- Canonical paths derive from stable Roadmap identity.
- If filesystem scaling requires sharding, the shard derives from stable ID
  data rather than lifecycle or organization.

ADR-0010 selects the exact flat ID-based layout. The stability rule is fixed by
this decision and applies after the versioned migration.

### Query behavior

Application queries state their lifecycle scope explicitly rather than relying
on which directory was scanned.

- Operational views default to visible, non-closed work where appropriate.
- Current-history views may include visible closed work.
- Reporting includes closed entities when completion history requires them.
- Archive views select archived entities.
- Explicit all-state queries include every retained lifecycle state.
- Lookup by stable ID resolves a retained entity regardless of closed or archive
  state.

Derived projections provide efficient lifecycle and status filtering. A full
canonical scan remains the correctness and rebuild fallback.

### Relationships and retention

- Closed and archived entities remain valid relationship targets.
- Archiving a project or milestone does not silently cascade archive operations
  to independently addressable entities. A cascade, if offered, is an explicit
  Application use case with a previewable write set.
- Archived canonical documents are retained indefinitely by default.
- Purge is a separate, explicit destructive operation. It is never an implicit
  consequence of close or archive and must report relationship impact.

Git history is valuable audit evidence but is not a substitute for retained
canonical entities needed by current queries, reporting, restoration, and
reference resolution.

## Consequences

### Positive

- Entity identity and links remain stable throughout the lifecycle.
- Archive and restore stop producing routine Git renames.
- One canonical location eliminates active/archive duplicate states.
- Performance is handled by a replaceable projection rather than leaked into
  domain semantics.
- Workflow completion remains visible even when an entity is archived.

### Costs and constraints

- The working tree retains archived documents unless users explicitly purge
  them.
- Projection rebuild performance must be measured for large histories.
- Existing archive directories and duplicated archive fields require a
  versioned migration.
- Commands and repository interfaces need explicit lifecycle query semantics.

## Alternatives considered

### Continue moving files to an archive tree

Rejected because it couples storage location to mutable lifecycle state and
creates lookup, consistency, restore, and Git-history complexity for a query
optimization.

### Delete entities when they close

Rejected because closing is a workflow event, not a destructive retention
decision, and current reporting and relationships need completed entities.

### Keep all files together and parse all of them for every command

Rejected as the target query strategy. Canonical files stay stable while a
rebuildable projection supplies efficient selection.

## Related decisions

- ADR-0003 defines canonical files and rebuildable projections.
- ADR-0004 defines stable identity and relationship behavior.
- ADR-0005 defines transaction guarantees for lifecycle mutations and migration.
- ADR-0007 defines compatibility obligations for the archive-layout migration.
- ADR-0010 defines the target canonical paths and entity ID format.

## Migration boundary

This ADR does not move current archive files or alter archive commands. A
versioned migration must reconcile active/archive duplicates, preserve IDs and
workflow status, and establish one stable path per retained entity.
