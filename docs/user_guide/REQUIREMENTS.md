# Durable requirement capture

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
or verify a requirement. Lifecycle/evidence and typed relation commands are
separate 0.4 work; relation/roadmap-target filters arrive with that slice.

List supports type, journey, stage, priority, Draft status and owner filters,
case-insensitive search over key/title/statement/rationale, and deterministic
key/title/priority/created/updated sorting with UUID tie-breaks. View accepts an
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

## Recovery

Resolve Git conflicts before retrying. Existing optimistic conflict checks
preserve external edits made during a write. Interrupted transactions use the
normal recovery machinery; retry the same operation. Canonical data remains
primary if SQLite refresh fails, with the usual stale-projection warning. Repair
and rebuild through `roadmap health`, then inspect the same UUID again.

The [capture contract](../planning/requirements-capture-contract-0.4.md) records
worked examples and the selected fingerprint/alias rules under
[ADR-0011](../architecture/adr/0011-optional-requirements-and-governance.md).
