# Publish a Roadmap closure after merge

Roadmap 0.4 development adds explicit outbound publication of committed closure
decisions. This command is not in published 0.3.1; use the development checkout
until the next release. Normal Roadmap commands stay offline.

## Record the decision locally

Use the normal issue commands to record the evidence, opt in the exact GitHub
target, and choose its remote disposition. For the #3756 investigation:

```sh
roadmap issue update 9928b489 \
  --add-label 'github-publish:shanewilkins/roadmap#3756' \
  --add-label 'github-close:not-planned'
```

That local issue is already closed with a recorded reason. For a newly resolved
issue, also run `roadmap issue close ID --reason 'Evidence-backed disposition'`.
Use `github-close:completed` for implemented/verified fixes; use
`github-close:not-planned` for declined, superseded, duplicate or currently
unreproducible reports. Keep the actual rationale in the closure reason and
supporting comments. Do not call an unreproduced report a verified fix.

`github:3756` and legacy provider metadata alone do not authorize publication.
Each opted-in closed record needs one qualified target, one disposition, and a
recorded closure reason. Ambiguous/invalid batches fail before remote writes.

## Commit, preview and push

Commit the canonical issue record with its evidence. Then preview the committed
plan from the development checkout:

```sh
uv run --locked roadmap github publish-closures --repo shanewilkins/roadmap
```

Preview emits JSON and makes no network calls. It reads Git HEAD, not uncommitted
changes; a newly closed but uncommitted issue is absent. A committed closure still
appears if you have only reopened it in the working tree. Review the commit before
pushing it to `master`, or merge it through a PR.

The **Publish Roadmap closures** Action checks out current `master`, posts a link
to the committed closure evidence, and closes the matching GitHub issue with the
chosen reason. Pushing another branch does not publish. The workflow uses its
built-in token with `issues: write`; no personal token is stored in Roadmap.

## Retry and inspect failures

Inspect the Action's preview and publication output. A failure returns nonzero
and names the failed endpoint; earlier items may already be published. Retry
using the workflow's manual dispatch on `master`, or by a subsequent push.

For deliberate manual publication from an already-pushed commit, authenticate
`gh` with issue write access and run:

```sh
uv run --locked roadmap github publish-closures \
  --repo shanewilkins/roadmap --apply
```

An already-closed issue is skipped, preserving its existing remote disposition.
If the evidence comment succeeded but the close failed, retry finds the stable
marker through paginated comments and does not post it again. No local receipt
files or follow-up commits are generated. Use a single publisher per repository;
the Action serializes its own runs. Independent manual publishers can race.

Publication does not import remote-only closures, mirror subsequent remote edits,
or reopen remote issues. GitHub-originated completion remains planned for 0.5.

See [ADR-0013](../architecture/adr/0013-publish-committed-github-closures.md).
