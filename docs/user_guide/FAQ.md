# Frequently asked questions

## What does “project management as code” mean?

Roadmap keeps canonical planning data in human-readable Markdown and YAML under
the repository. It can be reviewed, diffed, backed up, and shared with the same
Git workflow as source code. Roadmap provides the domain operations and queries;
Git provides history and network collaboration.

## Is SQLite the source of truth?

No. SQLite is a local, rebuildable projection used for queries and validation.
Canonical files are durable user data. A missing or corrupt projection must be
recreatable without changing the semantic content of those files.

## Does Roadmap synchronize with GitHub Issues?

No. Experimental 0.1.1 provider-sync commands are absent in 0.2. Store an
external URL or ID as ordinary issue content if useful, and use normal Git
commands to collaborate on Roadmap files.

## Does a commit message close an issue automatically?

That behavior is not part of 0.2. Update planning state explicitly:

```bash
roadmap issue close <issue-id> --reason "Implemented and verified"
```

Reversible hook and commit-reference automation is Deferred to post-0.2 for a
separate product decision.

## Can I work offline?

Yes. Roadmap's local workflows do not require a server or account. Network
access is needed only when you choose to use Git with a remote host.

## How do teammates see changes?

Commit canonical `.roadmap/` changes and use the repository's normal pull
request or branch process. Teammates pull the repository and run Roadmap
locally. Existing Git access controls and review policies govern the data.

## Which issue states are supported?

The current workflow states are `todo`, `in-progress`, `blocked`, `review`, and
`closed`. Use `roadmap issue update <id> --status <state>`, or the explicit
`start`, `block`, `unblock`, and `close` commands where appropriate.

## Can I script Roadmap?

Yes. Prefer JSON or CSV rather than parsing Rich terminal tables:

```bash
roadmap issue list --format json
roadmap status --format json
roadmap data export --format csv --output roadmap.csv
```

The 0.2 contract stabilizes machine schemas, stdout/stderr separation, and exit
categories.

## Can Roadmap manage requirements?

The repository uses CSV requirement registers as governance artifacts today.
Managing requirements as first-class Roadmap entities is Deferred until after
0.2; requirements and implementation issues remain distinct.

## Is Roadmap a Jira replacement?

Roadmap fits developers and small technical teams that prefer repository-local,
CLI-first planning. It does not provide a hosted UI, organization-wide access
control, cross-repository portfolio management, or the workflow breadth of a
large project-management suite.

## Where is the definitive 0.2 scope?

See the [public contract](../architecture/public-contract-0.2.md), its detailed
[compatibility inventory](../architecture/compatibility-inventory-0.2.csv),
and the [requirements registers](../requirements/README.md).
