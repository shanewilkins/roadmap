# ADR-0010: Use stable ID-based canonical paths

- Status: Accepted
- Date: 2026-08-10
- Scope: Canonical directory layout, filenames, entity IDs, and layout migration

## Context

ADRs 0003, 0004, and 0008 establish one canonical document per entity, stable
Roadmap identity, and lifecycle-independent storage. The current layout still
uses mutable information such as milestone assignment, title, and archive state
in directory or filename choices.

Before persistence refactoring begins, the target layout and ID contract must be
fixed. Otherwise adapters, links, migrations, projections, and enforcement could
be built around another temporary organization.

## Decision

The canonical entity layout is flat by entity type and keyed only by the complete
stable Roadmap ID:

```text
.roadmap/
  config.yaml
  issues/
    <stable-roadmap-id>.md
  milestones/
    <stable-roadmap-id>.md
  projects/
    <stable-roadmap-id>.md
```

Additional independently addressable entity types follow the same
`<collection>/<stable-roadmap-id>.md` rule unless an accepted ADR defines a
different canonical representation.

### Paths and filenames

- A canonical filename contains the complete Roadmap ID and the `.md` suffix.
- Titles, slugs, milestones, status, assignee, workflow state, and lifecycle
  state do not appear in the canonical path.
- Backlog, milestone membership, and project membership are document metadata and
  relationships, not directories.
- Closing, reopening, renaming, reassigning, archiving, and restoring do not move
  a canonical document.
- Entity collections remain flat. Filesystem sharding is deferred and would
  require a new accepted decision and versioned layout migration.
- Paths and IDs use a case-stable representation suitable for every supported
  filesystem.

### ID contract

- Existing Roadmap IDs are preserved exactly. Migration never expands, replaces,
  or regenerates an existing ID.
- New entities use a complete lowercase, hyphenated UUID4 string.
- A persisted relationship contains the target's complete canonical ID. For a
  legacy entity, its existing stored ID is its complete canonical ID.
- An inbound CLI adapter may accept an unambiguous prefix as user convenience,
  but it resolves that prefix before invoking Application. Prefixes are never
  persisted as substitutes for a known complete ID.
- Ambiguous prefixes fail without mutation and list enough non-sensitive context
  for the user to choose a complete ID.
- External identifiers never become filenames or Roadmap identity.

UUID4 is selected because it is supported across the declared Python runtime
range without an additional dependency and does not encode a provider, path, or
business ordering assumption.

### Migration

The layout transition is a versioned explicit migration under ADR-0007.

- Preflight enumerates every retained entity and proposed target path.
- Active and archive trees are reconciled by stable ID before any move.
- An ID collision or non-identical duplicate is an explicit conflict that stops
  migration; content is not selected heuristically.
- User-authored Markdown, supported unknown fields, timestamps, workflow state,
  archive metadata, and relationships are preserved.
- Migration stages the complete write set and uses ADR-0005 transaction and
  recovery guarantees.
- A dry run reports moves, conflicts, skipped files, and projection rebuilds.
- Derived projections are discarded and rebuilt after canonical migration.
- The workspace schema version changes only after the canonical layout commits
  successfully.

After this migration, ordinary entity operations do not move canonical files.

## Consequences

### Positive

- Identity-to-path mapping is deterministic and independent of mutable state.
- Git diffs show content changes instead of routine organizational renames.
- Lookup and duplicate detection search one canonical location per entity type.
- Adapter logic no longer needs active/archive or milestone directory traversal.
- New IDs have substantially more collision resistance than shortened UUIDs.

### Costs and constraints

- Existing workspaces need a one-time versioned migration.
- Filenames are less descriptive when viewed without document content.
- Legacy and UUID4 IDs coexist, so parsers and lookup must treat IDs as opaque
  strings rather than assuming one length.
- Flat directories retain all visible and archived entities.

## Alternatives considered

### Keep title slugs in filenames

Rejected because title edits would continue to create Git renames and stale
references.

### Organize issue files by milestone or lifecycle

Rejected because both values are mutable business state and projections provide
efficient filtering.

### Rewrite legacy IDs as UUID4

Rejected because identity stability is more important than making historical and
new IDs visually uniform.

### Introduce ID-prefix sharding now

Rejected because the stated small-team scope does not justify the added path
complexity without measurement.

## Related decisions

- ADR-0003 defines canonical files and rebuildable projections.
- ADR-0004 defines aggregate identity and relationships.
- ADR-0005 defines migration transaction guarantees.
- ADR-0007 defines compatibility and schema evolution.
- ADR-0008 separates lifecycle from storage location.

## Migration boundary

This ADR fixes the destination but does not move current files or issue new IDs.
The migration is a separately tested refactor stage described in the approved
implementation specification.
