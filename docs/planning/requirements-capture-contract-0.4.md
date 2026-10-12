# Durable requirements capture contract for 0.4

Work item: `13a711b6-ae83-4d7d-a78f-8126339756bc`.
This implements the identity/capture foundation under ADR-0011. Lifecycle,
evidence, typed links and gap reports remain separately tracked work. CSV stays
authoritative until the verified cutover; development fixtures do not replace it.

## Record and identity

Use UUID4 identity and `.roadmap/requirements/<uuid>.md`, with user and technical
requirements in the same collection. Readable aliases are `UR-NNN` or `TR-NNN`
(minimum three digits, no upper numerical bound). Alias prefix must match type.
Titles and aliases never determine identity or filenames.

Create requires a title, Markdown statement and at least one named criterion.
The same criterion envelope serves acceptance criteria for user requirements and
verification criteria for technical requirements; IDs are stable user-supplied
keys, unique within a requirement. Preserve rationale, priority, owner, journey,
stage and explicit scope alongside the statement. Defaults are Draft, medium
priority and no owner. New history entries identify the actor and timestamp.

Allocate the next alias (maximum existing number for that prefix plus one) under
the existing workspace lock. No central sequence file, server or reservation
service. Explicit aliases are validated under the same lock. Two separate Git
branches can still allocate the same alias; UUIDs remain distinct.

Ordinary alias lookup and mutations fail closed on collision. Repair uses an
explicit rekey by full UUID, checks that the destination alias is free, preserves
the file path and records old/new aliases in history. Never silently renumber a
branch or pick a title match. Exact UUID lookup remains available for diagnosis
and repair even when aliases collide. No alias reuse changes another record's ID.

## Acceptance-bearing revision

Versioned SHA-256 fingerprint over a deterministic UTF-8 JSON envelope containing
requirement type, title, Markdown statement, explicit scope, and criterion IDs and
text. Sort criteria by their IDs, so presentation order does not change intent.
Normalize CRLF/CR to LF; retain other whitespace and Markdown exactly. JSON keys
are sorted and separators fixed. No Markdown heuristic claims that different
prose means the same thing. Formatting changes outside that narrow normalization
are conservatively treated as intent changes.

Alias, rationale, priority, owner, journey/stage, timestamps and history do not
change this fingerprint. Scope does. Persist the fingerprint with each capture
revision; compute the current fingerprint from the actual fields during reads,
so manual edits cannot reuse an old stored digest as proof of current intent.
Keep previous revision definitions and attributed events. Lifecycle/evidence work
will bind acceptance and criterion coverage to these fingerprints; capture alone
cannot mark a requirement Accepted or Verified.

## Worked examples reviewed before implementation

| Change | Identity | Intent revision | Expected result |
| --- | --- | --- | --- |
| Create first user requirement | New UUID4 | New digest | `UR-001`, Draft, one captured definition |
| Rename its title | Same UUID/file | Changes | Preserve earlier definition and history |
| Rekey `UR-001` to `UR-012` | Same UUID/file | Unchanged | Alias event; no title matching |
| Change owner or priority | Same UUID/file | Unchanged | Metadata event |
| Convert CRLF to LF | Same UUID/file | Unchanged | Exact body still preserved by persistence |
| Reverse criterion display order | Same UUID/file | Unchanged | IDs define criterion identity |
| Change criterion text or scope | Same UUID/file | Changes | Preserve previous definition |
| Edit statement manually | Same UUID/file | Recomputed on read | Report changed current revision without rewriting on read |
| Merge two `UR-002` aliases | Two UUIDs/files | Neither rebound | Alias reads refuse; exact-UUID diagnosis/rekey |
| External edit during a CLI write | Same UUID | No lost edit | Existing optimistic conflict refuses transaction |

## Boundary and CLI plan

Domain owns the record, criterion invariants and pure fingerprint calculation.
Application owns allocation, selection, edit/rekey decisions and transaction
boundaries. The existing persistence adapter owns frontmatter, Markdown,
unknown-field preservation, locking/recovery and SQLite projection. Bootstrap
injects ports; CLI parses commands and renders terminal/versioned JSON.
No new architecture zone, generic graph package or provider dependency.

The capture slice exposes `requirement create`, `view`, `list`, `update` and
`rekey`. Search/filter/sort use deterministic Application results and UUID
tie-breaks. Type, journey, stage, priority, Draft status and owner are capture
filters; relation/target filters will be added with the separately owned typed
relation work. Missing/ambiguous lookup fails explicitly. Reads create no
canonical requirement files.

The maintainer selected explicit adoption and older-version refusal on
2026-10-10. The boundary is `requirement enable` preview followed by explicit
`--apply`, upgrading the project configuration to schema/workspace version 2
through the existing recoverable transaction. Released 0.3.1 rejects configuration
schema 2 before constructing workspace services. Existing
issue-only workspaces retain their version and behavior. Do not silently adopt
requirements while listing or viewing existing work.

## Verification gates

Pure identity/fingerprint tests first, then real-storage CLI, concurrent alias
allocation, branch-collision/rekey, manual edits, unknown-frontmatter, Git conflict,
optimistic write conflict, interrupted transaction/retry and projection rebuild.
Use installed before/after issue-only fixtures and a requirements-enabled journey.
Run the unchanged architecture and quality gates. Close the work item only when
its scoped implementation and preservation evidence pass; do not infer completion
of later lifecycle, relations or adoption-release work.
