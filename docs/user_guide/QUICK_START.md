# Quick start

This guide describes the supported local workflow. Provider synchronization
and automatic Git mutation exposed experimentally in 0.1.1 are absent in 0.2.

## Install

```bash
uv tool install roadmap-cli
roadmap --version
```

`pipx install roadmap-cli` is also supported. Roadmap requires Python 3.12,
3.13, or 3.14.

## Initialize a repository

```bash
cd my-project
roadmap init --project-name "My project"
roadmap status
```

Roadmap stores repository-local data under `.roadmap/`. Commit the canonical
Markdown and YAML files so collaborators receive them through ordinary Git.

## Capture and update an issue

```bash
roadmap issue create \
  --title "Implement authentication" \
  --priority high \
  --assignee your-name

roadmap issue list
roadmap issue view <issue-id>
roadmap issue update <issue-id> --status in-progress
roadmap issue progress <issue-id> 50
roadmap issue close <issue-id> --reason "Implemented and verified"
```

Use the stable ID printed by `issue create`. Valid issue states include `todo`,
`in-progress`, `blocked`, `review`, and `closed`.

## Add dependencies and discussion

```bash
roadmap issue deps add <issue-id> <dependency-id>
roadmap issue block <issue-id> --reason "Waiting for the dependency"
roadmap issue unblock <issue-id> --reason "Dependency completed"

roadmap issue comment add <issue-id> "Review notes"
roadmap issue comment list <issue-id>
roadmap issue comment list <issue-id> --format json
```

The supported discussion interface is `roadmap issue comment`. The separate
top-level `roadmap comment` commands in 0.1.1 are unfinished duplicates and are
not part of the 0.2 contract.

## Plan a milestone

```bash
roadmap project create --title "Web application"
roadmap milestone create \
  --title "0.2" \
  --due-date 2026-09-30 \
  --project "Web application"

roadmap milestone assign <issue-id> "0.2"
roadmap milestone view "0.2"
roadmap milestone list
```

## Query and export

```bash
roadmap today
roadmap status --format json
roadmap issue list --status blocked --format json
roadmap issue list --priority critical --format csv
roadmap data export --format markdown --output roadmap-report.md
```

The exact options are available from `roadmap <command> --help`. Structured
output is intended for scripts; human-readable styling is not a stable machine
interface.

## Collaborate

```bash
git add .roadmap/
git commit -m "Update roadmap"
git pull --rebase
git push
```

Git is the collaboration layer. SQLite remains a rebuildable local projection
of canonical files; refreshing or rebuilding it is local maintenance, not
remote synchronization. The experimental 0.1.1 `roadmap sync` and
`roadmap git sync` commands are absent in 0.2.

## Recover safely

```bash
roadmap health
roadmap health scan --details
roadmap health fix --dry-run
```

Preview repair before applying it, and commit or back up `.roadmap/` first. The
0.2 repair surface is limited to interrupted canonical transactions and
rebuilding the disposable SQLite projection; unsafe heuristic rewrites require
explicit canonical-file edits.

## Next steps

- [Workflows](WORKFLOWS.md)
- [Installation](INSTALLATION.md)
- [FAQ](FAQ.md)
- [0.2 remote-sync removal](REMOTE_SYNC_REMOVAL_0_2.md)
- [Roadmap 0.2 public contract](../architecture/public-contract-0.2.md)
