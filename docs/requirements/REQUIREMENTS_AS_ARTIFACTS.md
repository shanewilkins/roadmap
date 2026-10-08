# Requirements as First-Class Artifacts

**Decision status:** Minimal optional scope accepted for 0.4 on 2026-10-08;
broader interchange, supersession and scope-selection remain Deferred.

The [accepted 0.4 plan](../planning/0.4.0-plan.md) maps the nine outcomes to
requirements, implementation recommendations, work and evidence. It supersedes
the earlier broad draft (retained in Git history).
[ADR-0011](../architecture/adr/0011-optional-requirements-and-governance.md)
records the accepted architecture direction; unresolved interfaces are design
gates rather than implicit decisions.

## Recommendation

Use small repository-native requirements to connect intent, implementation and
verification. Preserve the existing hexagonal boundaries, transactions and
recovery. Requirements are optional; existing issue-only workspaces remain usable.

## Product boundary

| Artifact | Purpose |
| --- | --- |
| Requirement | Governed outcome or constraint, rationale, criteria and acceptance evidence. |
| Issue | Executable work, linked to intent or explicit maintenance rationale. |
| Milestone | Delivery grouping and progress. |
| Project | Strategic grouping. |

## Canonical storage

One Markdown file per requirement: `.roadmap/requirements/<uuid>.md`, following
ADR-0010. UUID4 identity is separate from workspace-unique readable UR/TR aliases.
Type is metadata, not a directory. Define the versioned envelope and alias
collision/rekey behavior before implementation. Preserve unknown fields, Markdown,
history and optimistic conflict protection through the existing unit of work.
SQLite provides rebuildable queries, never a second canonical store.

CSV remains authoritative for the project's requirements until a verified
one-time cutover. Thereafter CSV may be a generated view. General CSV import/export
is Deferred; cutover does not silently accept that broader feature.

## Lifecycle

Support Draft, Accepted, In Progress, Verified, Deferred and Rejected through
explicit, validated, attributed transitions. Review the transition table before
coding. Linked task state may inform progress but cannot govern requirement
status automatically. Verification records identify criteria, acceptance revision,
result, actor, date and commit/artifact. Semantic changes preserve prior evidence
but make it stale, requiring reacceptance and verification. Define and test
acceptance-bearing fields and canonicalization, including manual edits.

Supersession and requirement archive commands remain Deferred. Closed/archived
issue targets remain addressable for traceability.

## Typed relationships

Use a fixed set for intent support/dependencies, implementation, delivery targets,
evidence and external reports. Settle exact vocabulary and canonical owning
sides before implementation. Store UUID targets; derive reverse relations in
SQLite. Validate types, missing targets, duplicates and prohibited cycles.
Do not add a generic graph framework or duplicate manually maintained edges.
External reports use repository-qualified URLs and explicit local attribution.

## Minimum CLI journey

Implement create/view/list/update, explicit lifecycle transitions, typed link
management, verification evidence and gap/recommendation queries through
Application-owned use cases. Command names and flags require a reviewed contract.
Prove create, accept, plan, implement, verify, revise, reaccept and reverify in an
installed package, including conflict and invalid-transition recovery.

## Traceability views

Expose accepted intent without work, unjustified work, implementation awaiting
verification, stale/failed evidence, broken links and blockers. Justified
maintenance is legitimate work. Terminal and versioned JSON reconcile against
explicit populations. Recommendations are deterministic read-only queries with
reviewed eligibility/order, injected time, stable ties and explanations.

## Delivery sequence

Follow the [accepted delivery gates](../planning/0.4.0-plan.md#delivery-order-and-gates):
self-host governance first, identity/persistence, lifecycle/relations, decision
support, schedule/hosting URL, then optional adoption and release proof. Migration
preview/recovery and future-version/downgrade boundaries are required when the
schema changes. Broader CSV interchange and supersession migrations remain
separate Deferred requirements.

## Risks and controls

Fail closed on alias collisions or write conflicts. Retain stale evidence without
claiming current verification. Keep one authority through cutover. Treat local
work and GitHub disposition as separate auditable operations. Test candidates in
workspace copies and use the published CLI for daily governance now.

## Decision criteria

Accepted scope is complete only with scoped evidence and a self-hosted release
journey, including friction disposition and an audited GitHub baseline. No status,
coverage percentage or local issue closure is a substitute for that proof.
