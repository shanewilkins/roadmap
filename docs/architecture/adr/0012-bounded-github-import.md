# ADR-0012: Import GitHub records through bounded explicit ingestion

- Status: Accepted
- Date: 2026-10-08
- Scope: 0.4 import and collaboration; 0.5 external-closure correctness boundary

## Context

Dogfooding required a manual complete-record import after initial triage summaries
omitted source descriptions. The maintainer accepted bounded import and the
completion-after-pull collaboration guarantee for 0.4, while scheduling
GitHub-only closure propagation as a 0.5 correctness issue.

## Decision

Implement explicit selected-record GitHub import using `gh` for extraction and
an Application-owned ingestion use case for validation and local transactions.
Keep source records attributed and distinguish them from local planning fields.
Preserve complete agreed source content, existing local identity and history.
Preview the write plan, match repository-qualified external identity, deduplicate
unchanged imports and retain visible revisions for changed source records.
Do not silently apply source state changes to locally governed workflow fields.
Partial extraction, invalid input, conflicts and interrupted writes must support
clear failure and safe retry through existing persistence guarantees.

Provider-specific extraction belongs in a narrow outbound adapter; Domain and
Application do not construct provider clients or shell commands. Bootstrap wires
the adapter; CLI invokes Application. GitHub authentication stays with `gh`.
Ordinary core reads/writes remain offline. No credential store, generic provider
backend, reconciliation engine or background convergence protocol is introduced.
Exact command flags, source envelope/field mapping, selection, pagination and
changed-source presentation require an implementation contract before coding.

For 0.4 collaboration, closing in Roadmap and committing that canonical record
with a merged branch must produce correct completion views after another clone
pulls. Verify projection freshness and conflicts in an installed two-clone journey.

GitHub-only closure propagation is accepted for 0.5 under UR-069/TR-057. Its
acquisition/commit timing and conflicting/reopened-state ownership remain design
gates. Capturing external source state in 0.4 does not itself promise automatic
local completion. A separate reviewed policy must define how remote completion
becomes canonical repository data available through the promised pull workflow.

## Consequences

[ADR-0013](0013-publish-committed-github-closures.md) adds the accepted 0.4 outbound
publication path from committed Roadmap closures to GitHub. It does not change
this import contract or move GitHub-only closure acquisition out of 0.5.

ADR-0002 remains in force: this is the concrete bounded integration product
decision it permits. ADRs 0003–0011 retain canonical identity, file authority,
transaction, architectural and requirement-verification boundaries. Source
provenance and deduplication are import guarantees, not competing writable
sources or automatic status reconciliation.

Use the importer during 0.4 GitHub closeout and release dogfooding. Scope is
selected issues, full descriptions, paginated comments, agreed metadata/timeline
and original attribution; attachment URLs are retained without promising binary
capture. Repeat safely, preserve local work and expose changed source material.

## References

- [Collaboration/import release decision](../../requirements/proposals/collaboration-completion-after-pull.md)
- [Accepted 0.4 plan](../../planning/0.4.0-plan.md)
- [Manual source-record capture evidence](../../planning/github-record-capture-2026-10-08.md)
