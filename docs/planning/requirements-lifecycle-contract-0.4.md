# Requirement lifecycle and evidence contract for 0.4

Work item: `4c04e9cb-2b7d-4732-a09b-f6a5974a5138`. Extends the
[capture contract](requirements-capture-contract-0.4.md) under ADR-0011.

## Transition examples and rules

| Current state | Allowed destination |
| --- | --- |
| Draft | Accepted, Deferred, Rejected |
| Accepted | Draft, In Progress, Verified, Deferred, Rejected |
| In Progress | Draft, Accepted, Verified, Deferred, Rejected |
| Verified | Draft, Accepted, In Progress, Deferred, Rejected |
| Deferred | Draft |
| Rejected | Draft |

`requirement transition SELECTOR --status STATE --expected-revision DIGEST
--reason TEXT` requires the current recomputed intent digest and a nonempty reason.
Acceptance creates an immutable UUID acceptance record naming digest, actor, time
and reason. Reaccepting from In Progress or Verified starts a fresh acceptance
cycle; earlier evidence cannot satisfy it. Returning to Draft, deferring or
rejecting withdraws current acceptance. Same-state transitions refuse.

Verification is explicit and only succeeds with an active acceptance for current
intent and a latest passing result for every current named criterion in that
acceptance cycle. Closing an issue has no effect. In Progress requires acceptance.
Deferred and Rejected return through Draft before renewed acceptance.

## Evidence examples and rules

`requirement evidence SELECTOR --criterion ID --result pass|fail|incomplete
--reference COMMIT_OR_ARTIFACT --expected-revision DIGEST --acceptance-id UUID
--note TEXT` appends
an immutable UUID evidence entry. It names acceptance UUID, intent digest,
criterion ID, result, reference, actor and timestamp. Note is optional. The
acceptance UUID is checked under the same write lock as the digest, so concurrent
reacceptance of unchanged intent cannot receive a result from an old cycle. The
reference is a nonempty caller-supplied commit or artifact locator; offline
capture does not assert that the locator resolves or authenticate the actor.

Evidence is allowed only with active current acceptance in Accepted, In Progress
or Verified. Unknown criteria, stale digests, blank references and invalid results
refuse without mutation. For each criterion, append order determines the latest
result within the active acceptance cycle, independent of timestamps. Missing,
failed and incomplete results block verification. A failure or incomplete result
against Verified explicitly demotes it to In Progress. A later pass never silently
verifies it again. Earlier results remain available in history.

Examples: two criteria with only one pass cannot verify; pass then fail blocks;
fail then pass can verify after explicit transition; reacceptance requires fresh
results even at the same intent digest. Metadata/rekey edits preserve acceptance.
Intent edits reset to Draft, withdraw acceptance and preserve prior evidence.
Manual intent edits are compared with the active acceptance on every read:
effective state becomes Draft and evidence becomes stale without canonical writes.
A subsequent mutation records the manual intent and withdrawal before acting.
Reverting unobserved manual edits byte-for-byte cannot be detected by an offline
file reader; stored history is attribution, not a tamper-proof audit service.

## Persistence and outputs

Canonical frontmatter retains acceptance/evidence arrays plus the active
acceptance UUID. Old Draft capture documents default to empty arrays and no active
acceptance. Validate record references, digests, criterion membership in accepted
definitions, unique IDs and governance prerequisites when parsing; do not trust a
manually changed status or stored current digest. Malformed governance refuses.
Current content may differ from an accepted definition: that is stale intent,
not malformed historical evidence.

Versioned CLI JSON exposes effective `status`, stored `recorded_status`, active
acceptance, full acceptance/evidence history, `acceptance_current` and per-criterion
latest results through `verification`. List status filters and rebuildable SQLite
status use the same effective state. Reads never persist state changes.
All writes use the existing workspace lock, optimistic document validation and
recoverable unit of work. No new runtime dependency or architecture zone.
CSV authority, typed links, gap reports and project cutover remain separate work.
