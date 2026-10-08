# ADR-0013: Publish committed Roadmap closures to GitHub

- Status: Accepted
- Date: 2026-10-08
- Scope: 0.4, UR-070/TR-058

## Decision

Roadmap owns the closure decision; Git carries it; GitHub receives it after
merge. A narrow Application use case plans all eligible canonical closures from
a pinned Git HEAD. A persistence adapter maps committed blobs through the same
canonical document parser. A separate outbound adapter uses `gh api` to publish.
Bootstrap wires these independent adapters. Ordinary core operations stay offline.

The additive `roadmap github publish-closures --repo OWNER/REPO` command previews
offline JSON by default; `--apply` explicitly enables network writes. Eligibility
requires closed status, a recorded closure reason, exactly one qualified target
label `github-publish:OWNER/REPO#NUMBER`, and exactly one disposition label
`github-close:completed` or `github-close:not-planned`. These labels are an explicit
publication contract, not inferred from legacy `github:NUMBER` labels or imported
source snapshots. Existing issue-update commands manage them without a schema
migration. The importer can later propose these labels for review, not opt in
imported records silently. No local issue closes remotely just because its
unqualified number happens to match.

Reject malformed/conflicting opted-in records and duplicate local identities or
remote targets before any writes. Records for another explicitly selected
repository are excluded. Read only committed regular Markdown files, including
archived issues. Ignore working-tree edits and untracked records. All evidence
links identify the pinned commit, retained local ID, closure rationale and history.

For each target, verify the current remote record is an issue with the exact
requested number and repository URL. Skip already-closed issues without changing
their existing disposition or comments. Otherwise, post evidence, then close
with GitHub's `completed` or `not_planned` state reason. A stable comment marker
identifies the local closure event, qualified target and disposition independently
of unrelated later commits. Paginate all comments before deciding to post. Retry
after a failed close reuses existing evidence; retry after a successful close
skips it. Network failures stop the batch with a nonzero exit and an endpoint;
previous successes remain remote and safe to retry. No local receipt commits,
credential store, provider reconciliation or reopening are introduced.

## Automation and limits

The repository workflow runs on pushes to `master` and manual dispatch from that
branch, checking out the current `master` tip. It installs the locked runtime,
previews, then applies with `contents: read` and `issues: write`. A shared
concurrency group serializes workflow publications without canceling an active
batch. Every push retries all eligible closures; manual dispatch retries without
a new commit. Branch pushes and PR events do not publish. Tests use isolated
repositories and simulated GitHub transport; live workflow verification follows
merge, so implementation evidence does not yet prove a live GitHub round trip.

Use one publisher per repository. GitHub offers no atomic comment-and-close
transaction or comment idempotency key; independent concurrent manual publishers
can race to post duplicate evidence. A current-HEAD snapshot governs a run;
later canonical reopening does not reopen GitHub or undo an already issued close.
Removing publication labels before merge withdraws an unpublished decision.
Manual `--apply` is explicit publication and should run from an already-published
commit. This GitHub.com-only capability does not claim enterprise-host support.

This implements the bounded outward path permitted by ADR-0002. ADR-0012 remains
the import decision; GitHub-only closure acquisition stays in 0.5 (UR-069/TR-057).

## References

- [Operator guide](../../user_guide/GITHUB_CLOSURES.md)
- [GitHub issue update API](https://docs.github.com/en/rest/issues/issues#update-an-issue)
- [gh API pagination and JSON input](https://cli.github.com/manual/gh_api)
