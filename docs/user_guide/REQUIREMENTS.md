# Durable requirements and verification

Requirements are optional. An issue-only workspace keeps working without an
upgrade or new canonical files on requirement reads. CSV remains the project's
requirements authority until the separately verified register cutover.

## Explicit adoption

```sh
roadmap requirement enable
roadmap requirement enable --apply
```

The first command previews. Apply atomically upgrades project configuration and
workspace versions to 2 through the existing transaction/recovery machinery.
Released 0.3.1 refuses that configuration instead of silently ignoring requirements.
Retain a pre-upgrade backup if you need the old version; downgrade is unsupported.
A legacy workspace must first complete its existing version-1 migration.
Issue documents are not rewritten by enabling requirements. Config set/reset
preserve the adopted version. Repeating enable does not write again.

## Create, inspect and edit

```sh
roadmap requirement create --type user --title 'Keep intent durable' \
  --statement 'Retain the full Markdown statement.' \
  --criterion 'C1=Preserve UUID across edits' --owner Alice
roadmap requirement view UR-001
roadmap requirement list --type user --owner Alice --sort key
roadmap requirement update UR-001 --title 'Keep revised intent durable'
```

Capture commands return readable, versioned JSON. Use `--statement-file` instead
of `--statement` for a UTF-8 Markdown file. Repeat `--criterion ID=TEXT` for named
criteria; on update it replaces the entire criterion set. User requirements have
acceptance criteria; technical requirements have verification criteria. Criteria
IDs must be non-empty, unique and start with a letter.

Creation defaults to Draft, medium priority and no owner. It requires title,
statement and criteria; rationale, explicit scope, journey, stage, priority and
owner can be supplied. Reads expose UUID, readable key, current intent fingerprint,
prior captured definitions and attributed history. Capture alone cannot accept
or verify a requirement. Use the explicit lifecycle and evidence operations below.

List supports type, journey, stage, priority, lifecycle status and owner filters,
case-insensitive search over key/title/statement/rationale, and deterministic
key/title/priority/created/updated sorting with UUID tie-breaks. It also supports
reverse relation filtering described below. View accepts an
exact full UUID or unambiguous alias. No title matching or short-UUID guessing.

## Identity and edits

UUID4 is identity; files live at `.roadmap/requirements/<uuid>.md`. Readable
`UR-NNN` and `TR-NNN` keys are type-matching aliases. Automatic allocation runs
under the existing workspace lock. Separate Git branches can allocate the same
alias; a merge must not silently rebind either record.

```sh
roadmap requirement view FULL_UUID
roadmap requirement rekey FULL_UUID --key UR-012
```

An alias collision refuses ordinary alias lookup/list/edit/create. Exact UUID
inspection and rekey remain available. The destination must be free; rekey
retains UUID, file, definitions and history. Rekeying by alias is refused.

Statement, title, scope and criterion text/IDs affect the intent fingerprint.
Line ending normalization and criterion reordering do not. Other Markdown edits
are conservatively treated as changed intent. Owner, priority, rationale,
journey/stage and alias changes do not alter intent. `--clear-owner` explicitly
unsets owner. `--expected-revision DIGEST` refuses an edit if intent changed
since it was reviewed. Identity, creation time and history cannot be supplied as
editable fields through Application or CLI.

Manual edits are read without rewriting the document. Current intent is
recomputed from actual fields; an old stored digest cannot certify new content.
`uncaptured_intent` reports a definition that has not yet been captured. The next
CLI update retains that manual definition before capturing its own edit.
Unknown supported frontmatter, prior definitions and history survive updates.
An unchanged edit or rekey writes nothing, making a persisted retry safe.

## Accept and verify intent

Inspect the current requirement and copy its `current_revision` digest. Every
governance operation requires that reviewed digest; changed intent refuses.

```sh
roadmap requirement transition UR-001 --status accepted \
  --expected-revision DIGEST --reason 'Reviewed statement and criteria'
roadmap requirement transition UR-001 --status in-progress \
  --expected-revision DIGEST --reason 'Implementation started'
roadmap requirement evidence UR-001 --criterion C1 --result pass \
  --reference 'commit:FULL_COMMIT_SHA' --expected-revision DIGEST \
  --acceptance-id ACCEPTANCE_UUID \
  --note 'Identity retained through rename and rebuild'
roadmap requirement transition UR-001 --status verified \
  --expected-revision DIGEST --reason 'All criteria have passing evidence'
```

Copy `ACCEPTANCE_UUID` from `active_acceptance_id` after acceptance. Both UUID and
digest are checked under the write lock; reacceptance of unchanged intent also
requires inspecting the new cycle before submitting results.

Acceptance records the actor, date, reviewed digest and reason in a new acceptance
cycle. Evidence records its own UUID, acceptance UUID, digest, criterion, result,
commit/artifact reference, actor and date. References are captured offline; the
CLI does not authenticate actors or check remote artifacts. Repeat evidence for
every named criterion. The latest result per criterion in the active acceptance
cycle must be `pass` before an explicit transition to Verified succeeds.
`fail`, `incomplete` and missing results block verification. A failure or incomplete
result against Verified returns it to In Progress; a later pass still needs an
explicit verification transition. Closing an issue never verifies a requirement.

Draft can become Accepted, Deferred or Rejected. Accepted, In Progress and Verified
can return to Draft, defer or reject; Accepted can start work or verify, In Progress
can accept again or verify, and Verified can accept again or resume work. Deferred
and Rejected must return to Draft before acceptance. Every transition needs a reason;
same-state transitions refuse. Reaccepting starts a new cycle even at the same
digest and needs new evidence.

Semantic edits withdraw acceptance and return intent to Draft. Earlier definitions,
acceptances and results remain available as history. Metadata edits and rekeys
preserve acceptance. Manual intent edits also show effective Draft on reads, with
`acceptance_current: false`; `recorded_status` preserves the on-disk status for
diagnosis. The next write records withdrawal. `verification` exposes each current
criterion's latest result or `missing`; it excludes previous acceptance cycles.
List filters and rebuilt projection status agree with effective state. Reads
never rewrite canonical records. Byte-for-byte reversion of unobserved manual
edits cannot be detected; canonical history is not tamper-proof authentication.

## Link intent to work and delivery

Requirements canonically own typed links. Target artifacts are not rewritten;
SQLite derives reverse lookup rows and can be rebuilt from canonical Markdown.

```sh
roadmap requirement link TR-001 --relation supports --target UR-001
roadmap requirement link UR-001 --relation implemented-by --target ISSUE_UUID
roadmap requirement link UR-001 --relation project-target --target PROJECT_UUID
roadmap requirement link UR-001 --relation milestone-target --target MILESTONE_UUID
roadmap requirement link UR-001 --relation report \
  --target https://github.com/OWNER/REPOSITORY/issues/123
roadmap requirement list --relation implemented-by=ISSUE_UUID
roadmap requirement unlink UR-001 --relation implemented-by --target ISSUE_UUID
```

`supports` permits only a technical source and user target. `depends-on` links
requirements and refuses directed cycles. `implemented-by` targets issues.
Project and milestone targets are each optional and singular. Internal writes
require an existing correctly typed target, but closed and archived targets remain
valid. Duplicate and self links refuse without mutation.

Evidence relations are derived from immutable criterion evidence and cannot be
added or removed through link commands. External reports require an absolute
repository-qualified HTTP(S) URL and record the local actor and time; Roadmap does
not contact the provider. Relation changes do not alter the intent fingerprint or
withdraw acceptance. Unlink removes only the relation. A manually introduced
missing target remains readable and removable, and `health scan` reports it as a
broken canonical reference without rewriting the requirement.

## Recovery

Resolve Git conflicts before retrying. Existing optimistic conflict checks
preserve external edits made during a write. Interrupted transactions use the
normal recovery machinery. After a governance write reports interruption, inspect
the requirement before retrying: the write may already be durable. Evidence is
append-only, so a deliberate repeat creates another attributed result. Canonical data remains
primary if SQLite refresh fails, with the usual stale-projection warning. Repair
and rebuild through `roadmap health`, then inspect the same UUID again.

The [capture contract](../planning/requirements-capture-contract-0.4.md) records
worked examples and the selected fingerprint/alias rules under
[ADR-0011](../architecture/adr/0011-optional-requirements-and-governance.md).
The [lifecycle contract](../planning/requirements-lifecycle-contract-0.4.md) records
the transition table and revision-bound evidence rules.
The [traceability contract](../planning/requirements-traceability-contract-0.4.md)
records relation ownership, cardinality, validation and reverse-query rules.
