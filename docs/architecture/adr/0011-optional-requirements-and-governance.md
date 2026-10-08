# ADR-0011: Add optional requirements with revision-bound governance

- Status: Accepted
- Date: 2026-10-08
- Scope: 0.4 requirements identity, lifecycle, evidence, traceability and adoption

## Context

The maintainer accepted nine observable 0.4 outcomes, including using Roadmap to
develop itself and to govern disposition of its GitHub backlog. Requirements
represent intent; issues represent executable work. They need distinct identities
and lifecycles while sharing existing persistence and architectural guarantees.

## Decision

Add an optional requirements aggregate within the existing hexagonal boundaries.
Use complete UUID4 identity and flat `requirements/<uuid>.md` canonical paths
under ADR-0010. Readable UR/TR keys are workspace-unique aliases, not filenames or
identity. Ambiguous or colliding keys fail closed; explicit rekeying preserves
UUID identity, history and links. Use the existing unit of work, conflict checks,
recovery and rebuildable SQLite projection. Preserve Markdown and unknown fields.

Support explicit Draft, Accepted, In Progress, Verified, Deferred and Rejected
states. Verification is criterion-specific and applies to an acceptance-bearing
revision, with actor/date/result/commit or artifact attribution. Semantic edits
preserve prior evidence but make it stale for the current revision and require
renewed acceptance and verification. Issue closure cannot imply verification.

Use a fixed typed relation set with one canonical owning side; reverse relations
are derived. Validate types, targets, duplicates and prohibited cycles. Archived
and closed entities remain addressable. Gap reports and recommendations are
read-only Application queries with shared terminal/JSON results. Recommendations
use an explicit deterministic policy, not an AI service or automatic approvals.

Keep adoption additive and optional. Use an explicit versioned migration for
schema changes, preserving supported issue-only workflows and documenting
unsupported downgrade. Keep the CSV registers authoritative during development;
cut over once to requirement artifacts after preservation/verification proof.
Thereafter CSV is a generated view, not a second manual authority.

Use installed Roadmap to govern its release work and capture observations. Map
external GitHub reports by repository-qualified URL and preserve existing local
IDs. Local work and remote disposition are separate auditable operations; the
latter uses explicit `gh` actions. Do not introduce automatic provider sync.

## Consequences

No new architecture zone, graph framework or authentication service is needed.
The project must test identity preservation, revision staleness, invalid
transitions, projection reconstruction and optional adoption. Alias allocation,
fingerprint canonicalization, transition prerequisites, relation vocabulary and
recommendation ordering remain implementation design gates, with worked examples
required before coding. This decision accepts principles, not those unresolved
interfaces or a claim of delivered behavior.

## Related decisions

ADRs 0001, 0003–0010 remain in force. The
[accepted delivery plan](../../planning/0.4.0-plan.md) maps the nine outcomes to
requirements, implementation recommendations, evidence and delivery gates.
