# Accepted scope: Collaboration after pull and bounded GitHub import

- Status: Accepted by maintainer on 2026-10-08; delivery not yet verified.
- Owner: Maintainer.
- 0.4: UR-067/TR-055 collaboration correctness; UR-068/TR-056 bounded import.
- 0.5: UR-069/TR-057 GitHub-only closure propagation correctness.

## Decision

The maintainer accepted the recommended boundary: get basic Git collaboration
and explicit import working for 0.4 dogfooding; handle GitHub-only closure as a
0.5 correctness issue. This resolves the initial unscheduled draft proposal.
The CSV registers hold the formal requirement statements and criteria.

## 0.4 collaboration requirement

After a contributor closes an issue in Roadmap, commits the canonical completion
record with the implementation changes and merges the branch, another
collaborator shall see the issue complete on their first relevant Roadmap read
after pulling. Preserve issue identity, completion history and context.

## Observable acceptance criteria

1. In two independent clones, Bob closes a shared issue in Roadmap, commits its
   canonical record with the implementation changes, and merges the branch.
2. The other collaborator pulls the merged branch. The next issue view/list and
   milestone or project progress query agree that the same issue is complete.
3. A preexisting stale local SQLite projection does not hide the received
   completion or require the user to import the issue again, run a separate
   status-update command or manually repair otherwise valid received data.
4. Bob's issue ID, closure reason/history and retained implementation context
   survive the exchange. Local machine settings and credentials are not exchanged.
5. Concurrent edits use ordinary Git conflict handling. Unresolved conflict
   markers are diagnosed rather than interpreted as a valid completed record;
   resolved canonical records determine the subsequent view.
6. Completion of implementation work does not automatically mark a linked
   requirement Verified; acceptance evidence has its own lifecycle.

## 0.4 bounded import requirement

Explicitly import selected GitHub issue records completely and safely. Preview
selection/identity matching and local changes. Preserve original descriptions,
all paginated comments, agreed metadata/timeline and attribution. Retain
attachment URLs without promising binary attachment capture. Reuse existing
local IDs; preserve local planning, content and history. Repeated identical
imports must not duplicate records; changed remote records retain source
revisions and expose differences without silently overwriting local status.
Validate input, handle conflicts and recover/retry interrupted writes safely.

Use `gh` for extraction and Application-owned ingestion through existing
transaction boundaries. Keep core workflows offline. Review exact command,
source envelope/mapping and change presentation before coding. This is a bounded
integration, not a second reconciliation protocol.

## 0.5 correctness requirement

When Bob closes only the GitHub issue and implementation is merged, a defined
external-disposition path must record the completion in canonical repository
data so another collaborator sees it through the promised next-pull workflow.
Settle capture/commit timing, exact source identity, local-field ownership and
conflicting/reopened-state rules before implementation. Test failed/repeated
delivery and retain attribution/history. Issue closure does not verify intent.
This capability is accepted for 0.5 and is outside the 0.4 release gate.

## Delivery order

Verify the existing two-clone Git journey early; fix actual gaps rather than
assuming a new synchronization layer is needed. Implement the bounded importer
before substantial remaining GitHub closeout and use it during 0.4 dogfooding.
At release review: import, plan, implement, close locally, commit, merge, pull in
another clone and verify completion. The separate 0.5 item carries external-only
closure correctness, not an implicit 0.4 promise.

## Canonical work items

- [0.4 two-clone collaboration](../../../.roadmap/issues/355390b8-7f70-4f89-8042-34252d6d4981.md).
- [0.4 bounded GitHub import](../../../.roadmap/issues/ff21f48a-d2bc-4bc1-bce3-90468079190d.md).
- [0.5 GitHub-only closure correctness](../../../.roadmap/issues/884d27e2-6fda-434b-a506-fac9b8c1128f.md).

## Architecture references

- [ADR-0002: Git-owned synchronization](../../architecture/adr/0002-git-owned-synchronization.md)
- [ADR-0003: Canonical files and projections](../../architecture/adr/0003-canonical-files-and-rebuildable-projections.md)
- [ADR-0012: Bounded GitHub import](../../architecture/adr/0012-bounded-github-import.md)
- [Accepted 0.4 plan](../../planning/0.4.0-plan.md)
