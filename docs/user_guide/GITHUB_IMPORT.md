# Import selected GitHub issue records

Run from an initialized Roadmap workspace with `gh` installed and authenticated:

```sh
roadmap github import --repo OWNER/REPO 123 456
roadmap github import --repo OWNER/REPO 123 456 --apply
```

The first command fetches and previews; it makes no canonical writes. The second
fetches again, validates the whole selection, rechecks local ownership under the
workspace lock and commits the local captures together. Neither command writes
to GitHub. Select 1–25 distinct positive issue numbers. Each API invocation has a
60-second timeout; each normalized issue envelope is limited to 20 MB.

## Identity and duplicate policy

Identity is repository-qualified `OWNER/REPO#NUMBER`, independent of the title.
The importer recognizes previous importer snapshots, qualified
`github-source:OWNER/REPO#NUMBER` and `github-publish:OWNER/REPO#NUMBER` labels,
and the existing anchored `# GitHub source record:` or `Baseline GitHub report:`
source URL headers. Repository names are compared without case sensitivity.
Closed and archived issues participate in matching.

One matching record retains its local ID. No match previews creation with a new
ID allocated only on apply. Multiple matches refuse the entire batch. An
unqualified legacy `github:NUMBER` label also refuses import until its repository
is established through `roadmap issue update --add-label`. Titles, arbitrary
links and similar descriptions are never identity evidence. Recorded GitHub node
IDs also guard against mistaken reuse and transferred or renamed targets;
those cases require explicit reconciliation.

If a historical triage copy has already been resolved as a duplicate, retain its
history and explicitly designate its original local owner:

```sh
roadmap issue update DUPLICATE_ID --add-label github-source-owner:ORIGINAL_ID
```

Use the owner's exact local ID. The redirect is accepted only if the copy is
closed, carries `resolution:duplicate`, both records have the same qualified
GitHub identity, and the owner exists and has no redirect. Chains, missing owners,
self references and inconsistent identities refuse the batch. Ordinary closed
records are never silently ignored.

## Captured data and local authority

Each immutable source revision is one attributed local comment containing a
reserved `roadmap-github-source:v1` marker and a JSON envelope. It retains the full
issue response (including Markdown description and metadata), all paginated
comments, and all API-visible timeline events. Original authors, timestamps,
links and IDs remain inside that envelope; the enclosing comment records the
local capture time and identifies the GitHub importer. Source comments are not
flattened into local discussion. Attachment links remain in source text; binary
attachments and private edit history are outside this contract.

The adapter fetches the issue before and after pagination and refuses a changed
response or an incomplete comment count. Every selected record must validate
before any local write. Existing local title, description, status, assignee,
labels, relations and history remain intact. A newly created local issue starts
in the ordinary TODO state, unassigned, even if GitHub reports it closed. GitHub
state is source evidence, not an instruction to close or reopen local work.

An unchanged repeat returns `unchanged` and writes nothing. Changed source data
adds a `capture-revision` comment. A return to an already captured version returns
`reuse-revision` without another copy; comment order remains capture history,
not a claim that the last comment is the current remote state. Keep reserved
markers and their JSON intact: malformed or edited provenance refuses import.

## Recovery and scope

Apply uses the existing canonical transaction and recovery machinery. Retry an
interrupted operation with the same command; successfully captured revisions are
reused. Resolve Git conflicts before retrying. Source revisions travel with
ordinary committed issue files and remain readable after a pull and projection
rebuild.

This command imports selected issues. It does not import GitHub projects or
milestones, pull requests or code, and it does not run in the background.
Automatic acquisition of GitHub-only closure remains the 0.5 correctness work.
The separate `github publish-closures` command publishes committed opted-in local
closures, under its own contract.

See [ADR-0012](../architecture/adr/0012-bounded-github-import.md) and the
[accepted 0.4 plan](../planning/0.4.0-plan.md).
