# Durable requirement capture verification — 2026-10-12

Scope: work item `13a711b6-ae83-4d7d-a78f-8126339756bc`, the capture/identity
foundation for 0.4. Lifecycle/evidence, typed relations and their filters,
reverse queries, gap reports and the project register cutover remain separate
work. Closing this issue must not mark those outcomes or CSV rows verified.

## Delivered contract

`requirement enable` previews explicit adoption; `--apply` upgrades project
configuration and workspace versions to 2 through the existing transaction.
Published 0.3.1 rejects the upgraded workspace. Issue-only workspaces retain
version 1; enabling does not rewrite issue documents. Config set/reset preserve
adoption, and retries do not downgrade the workspace.

Create/view/list/update/rekey capture Draft user/technical requirements with
UUID4 identities, separate type-matching UR/TR aliases, Markdown statements,
named criteria, rationale and planning metadata. Local alias allocation uses
the existing lock. Branch collisions identify aliases and affected UUIDs;
explicit full-UUID rekey retains files, intent and history.

Versioned fingerprints cover type/title/statement/scope/criteria. Named criteria
are sorted and line endings normalized; other Markdown changes conservatively
change intent. Metadata and alias edits retain intent. Reads recompute intent
without rewriting files; the next edit retains a manual definition before its
own revision. Immutable identity/history fields cannot be supplied as updates.

## Evidence

Pure worked-example tests preceded persistence implementation. Real-storage tests
cover user/technical creation, discovery, metadata/intent edits, exact lookup,
concurrent allocation, branch-collision rekey, manual edits, unknown frontmatter,
Git conflicts, optimistic document and adoption conflicts, interrupted adoption
and capture recovery, idempotent retries and projection rebuild.

The installed candidate journey started with a workspace created by actual
published 0.3.1, previewed and applied adoption, confirmed that 0.3.1 then refused
it, and checked the original issue byte-for-byte. The new requirement retained
its UUID/path through edits and rekey, retained two intent definitions, and
survived projection rebuild. Read-only operations wrote zero canonical files.
The fixture workspace was temporary; this project was not upgraded and its CSV
registers remain authoritative.

Architecture review: Domain owns pure invariants/fingerprints; Application owns
selection, allocation, edits and transaction decisions; persistence maps files
and reuses the existing writer/recovery/projection; CLI renders JSON; bootstrap
wires the narrow ports. No new zone, exception, generic provider framework or
runtime dependency. All four import contracts pass (152 files, 599 dependencies).
Typing, lint, complexity, dead-code and high-severity security gates pass without
relaxing enforcement. Public command/parameter contracts and operator docs are
recorded in the existing inventory and behavior matrix.

Final local validation passed all **1,328 tests** with 96.91% statement coverage
(6,644 statements, 205 uncovered), using one worker. An intermediate full run
passed 1,324 tests. Two later parallel runs exceeded different existing
performance limits: projection rebuild at 8.913 seconds against 8 seconds, then
daily/board at 10.336 seconds against 8 seconds while rebuild passed. The
unchanged benchmark passed in isolation and in the final complete serial run.
This is evidence of load sensitivity, not a proved root-cause diagnosis. No limit
was raised, test skipped or assertion weakened. Normal parallel CI remains the
remote verification gate; its outcome is recorded in the work item's comments.

The [installed result](requirement-capture-verification-2026-10-12.json) records
actual published-version refusal and the preservation/rebuild checks.

Permanent installed-candidate capture/adoption journeys run in the six supported
Ubuntu/macOS and Python package-matrix jobs. That matrix checks the candidate;
the local journey additionally exercises actual published 0.3.1 refusal.
Candidate metadata still says 0.3.1; this is unreleased 0.4 work, not a PyPI release.

See [operator guide](../user_guide/REQUIREMENTS.md) and
[capture contract](requirements-capture-contract-0.4.md).

## Remote completion proof

Implementation `662c2a891575bc7aab83ef35299f001333d868b9` is pushed.
[CI 38279490416](https://github.com/shanewilkins/roadmap/actions/runs/38279490416)
succeeded. The normal parallel suite passed all 1,328 tests on each of Python
3.12, 3.13 and 3.14 (31.65s, 32.08s and 34.40s respectively). Quality and build
jobs passed. Each of the six Ubuntu/macOS package jobs successfully ran the new
installed requirements capture journey, alongside retained wheel/sdist smoke,
cumulative and collaboration/import journeys. CodeQL also succeeded.

This completes the capture slice's remote verification gate without relaxing
performance limits or changing the parallel CI configuration. Project adoption,
CSV cutover and later requirement lifecycle/relations are still separate work.
