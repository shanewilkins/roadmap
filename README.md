# Roadmap CLI

Roadmap is a repository-local project-management CLI for developers who want
their planning data in reviewable Markdown and YAML files rather than a hosted
service. It supports issues, dependencies, comments, projects, milestones,
daily views, health checks, and machine-readable exports.

The current release is 0.2.0. Its deliberately contracted behavior is defined
by an explicit
[public compatibility contract](docs/architecture/public-contract-0.2.md).

## What it does

- Stores canonical project data under `.roadmap/` so it can be reviewed and
  versioned with the repository.
- Works offline after installation; no Roadmap account or server is required.
- Manages issue state, priority, assignment, dependencies, progress, and
  threaded comments.
- Organizes work into projects and milestones and derives planning views.
- Exposes JSON and CSV for scripts alongside human-readable terminal output.
- Uses a local SQLite index as a rebuildable projection of canonical files.
- Leaves network collaboration to ordinary Git.

Roadmap is intentionally repository-scoped and CLI-first. It does not provide
a hosted web UI, cross-repository portfolio planning, or provider-owned remote
issue synchronization.

## Requirements

- Python 3.12, 3.13, or 3.14
- macOS or Linux; CI tests Ubuntu 24.04 x64 and macOS 15 ARM64
- Git when the `.roadmap/` data will be shared with collaborators

## Installation

With `uv`:

```bash
uv tool install roadmap-cli
roadmap --version
```

With `pipx`:

```bash
pipx install roadmap-cli
roadmap --version
```

Or in a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install roadmap-cli
roadmap --version
```

For development:

```bash
git clone https://github.com/shanewilkins/roadmap.git
cd roadmap
uv sync --all-extras --locked
uv run roadmap --help
```

## Quick start

Initialize a repository and create work:

```bash
cd my-project
roadmap init --project-name "My project"
roadmap issue create --title "Fix login timeout" --priority high
roadmap issue list
```

Use the ID printed by `issue create` to inspect and update the issue:

```bash
roadmap issue view <issue-id>
roadmap issue update <issue-id> --status in-progress
roadmap issue progress <issue-id> 50
roadmap issue comment add <issue-id> "Reproduced and isolated the cause."
roadmap issue close <issue-id> --reason "Fixed and verified"
```

Organize delivery:

```bash
roadmap project create --title "Web application"
roadmap milestone create --title "0.2" --due-date 2026-09-30
roadmap milestone assign <issue-id> "0.2"
roadmap milestone view "0.2"
```

Query or export data:

```bash
roadmap today
roadmap status --format json
roadmap issue list --status blocked --format json
roadmap data export --format csv --output roadmap.csv
roadmap health --format json
```

Run `roadmap <command> --help` for the exact options supported by the installed
version.

## Migrating an existing workspace

The 0.2 development line upgrades 0.1.1 workspaces explicitly. Preview the
complete validated write set first, then confirm the migration:

```bash
roadmap migrate --dry-run
roadmap migrate --yes
```

Migration preserves existing IDs and user-authored content, moves canonical
documents to flat stable-ID paths, externalizes user preferences, and rebuilds
SQLite from canonical files. Resolve every reported conflict before retrying;
ordinary reads never migrate files automatically. Follow the complete
[0.2 migration guide](docs/user_guide/MIGRATING_TO_0_2.md) before upgrading.

## Collaborating through Git

Roadmap data is shared the same way as source code:

```bash
git add .roadmap/
git commit -m "Update project roadmap"
git pull --rebase
git push
```

Roadmap 0.2 keeps explicit local Git conveniences such as `roadmap git status`,
`roadmap git branch <issue-id>`, and `roadmap git link <issue-id>`. It does not
install hooks, interpret commit prose to mutate issue state, store provider
credentials, or synchronize directly with GitHub or another issue service.

The 0.2 codebase removes the experimental 0.1.1 remote-sync, provider, and
automatic-hook commands. Use normal Git commands for collaboration. See the
[0.2 removal guide](docs/user_guide/REMOTE_SYNC_REMOVAL_0_2.md) before upgrading
an existing workspace.

## Data ownership and recovery

Canonical Markdown and YAML are the durable data. SQLite is a local search and
validation projection, not a second source of truth and not a remote sync
target. Projection rebuild and canonical-file recovery are explicit and
testable.

Keep `.roadmap/` versioned and make a normal Git commit before running the 0.2
migration. Do not treat the internal SQLite schema as a public API.

## Documentation

- [Quick start](docs/user_guide/QUICK_START.md)
- [Installation](docs/user_guide/INSTALLATION.md)
- [Workflows](docs/user_guide/WORKFLOWS.md)
- [FAQ](docs/user_guide/FAQ.md)
- [0.2 migration guide](docs/user_guide/MIGRATING_TO_0_2.md)
- [Architecture decisions](docs/architecture/README.md)
- [Refactor case study](docs/architecture/portfolio-case-study.md)
- [0.2 release checklist](docs/releases/0.2.0-checklist.md)
- [Requirements register](docs/requirements/README.md)
- [Project governance](docs/governance/README.md)
- [Security policy](SECURITY.md)
- [Contributing guide](CONTRIBUTING.md)

The old GitHub and milestone synchronization guides describe experimental
0.1.1 behavior and are retained only as migration history; they are not the 0.2
product direction.

## Project status

Roadmap 0.2.0 is the result of thirteen independently verified refactor phases.
See the
[execution plan](docs/architecture/refactor-execution-plan.md) and published
[checkpoint reports](docs/architecture/README.md#execution-checkpoints).

## License

[MIT](LICENSE.md)
