# Requirement traceability contract for 0.4

Work item: `2237e909-ab42-4095-a1a2-d791676ed9d4`. Extends the
[capture contract](requirements-capture-contract-0.4.md) and
[lifecycle contract](requirements-lifecycle-contract-0.4.md) under ADR-0011.

## Fixed relation vocabulary and ownership

The requirement artifact canonically owns every mutable traceability link.
SQLite contains only rebuildable reverse rows; target artifacts are never edited
to maintain reciprocal data.

| Relation | Source | Target | Cardinality and validation |
| --- | --- | --- | --- |
| `supports` | Technical requirement | User requirement | Many; UUID target; no self-link or duplicate |
| `depends-on` | Requirement | Requirement | Many; UUID target; no self-link, duplicate or directed cycle |
| `implemented-by` | Requirement | Issue | Many; target must exist; closed and archived issues remain valid |
| `project-target` | Requirement | Project | At most one; target must exist and may be archived |
| `milestone-target` | Requirement | Milestone | At most one; target must exist and may be closed or archived |
| `evidence` | Requirement | Evidence record | Derived from immutable evidence history; not directly mutable |
| `report` | Requirement | Repository-qualified URL | Many unique URLs with local actor and timestamp |

Internal targets are stored as stable IDs. Requirement aliases are accepted at
the CLI boundary for requirement-to-requirement links and resolved to UUIDs
under the workspace lock. External report URLs are captured offline; Roadmap
does not authenticate the actor, contact the provider or synchronize remote state.

## Commands and queries

`requirement link SELECTOR --relation TYPE --target TARGET` adds one relation.
`requirement unlink` uses the same arguments and removes only the edge, never
either artifact. Evidence links are created only by `requirement evidence`.
`requirement list --relation TYPE=TARGET` performs deterministic reverse
discovery; requirement aliases resolve before matching.

Link writes validate target type and existence, duplicates, cardinality and the
complete requirement dependency graph before staging a canonical mutation.
Failures write nothing. Unlink accepts a stored missing UUID so a manually broken
edge remains repairable. Relation changes are metadata: they preserve requirement
identity, intent fingerprint, acceptance and evidence while retaining attributed
history.

## Persistence, projection and diagnosis

Canonical frontmatter stores mutable relations and attributed external reports.
Old requirement documents default to empty relations. Reads preserve supported
unknown top-level fields. SQLite schema version 2 projects every relation,
including derived evidence, into a reverse index keyed by relation and target.
Rebuild and incremental refresh must produce the same reverse answers.

Manual edits can introduce targets that no longer exist. Reads remain possible;
`health scan` reports `canonical.broken-reference` without rewriting the file.
Canonical Markdown remains authoritative if projection refresh fails.

Generic graph plugins, provider synchronization, supersession, remote URL
validation and arbitrary evidence deletion remain out of scope.
