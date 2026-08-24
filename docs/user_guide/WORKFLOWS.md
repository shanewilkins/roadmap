# Supported workflows

These workflows use explicit Roadmap commands and ordinary Git. Roadmap 0.2
does not install automatic mutation hooks or synchronize with hosted issue
providers.

## Solo daily loop

```bash
roadmap today
roadmap issue update <issue-id> --status in-progress
roadmap issue progress <issue-id> 50

# Work and commit source changes normally.
git add src/ tests/
git commit -m "Implement the selected work"

# Change planning state explicitly.
roadmap issue close <issue-id> --reason "Implemented and verified"
git add .roadmap/
git commit -m "Close roadmap issue"
```

Explicit state changes keep ordinary commit prose from unexpectedly mutating
planning data.

## Small-team planning loop

Create the delivery structure and assign work:

```bash
roadmap project create --title "Web application"
roadmap milestone create --title "Sprint 1" --due-date 2026-08-28
roadmap issue create --title "Create users endpoint" --priority high
roadmap milestone assign <issue-id> "Sprint 1"
roadmap issue update <issue-id> --assignee alice
```

Review the shared state:

```bash
roadmap milestone view "Sprint 1" --only-open
roadmap issue list --milestone "Sprint 1" --format json
roadmap issue list --status blocked
```

Discuss decisions next to the work:

```bash
roadmap issue comment add <issue-id> "Please cover the null-name case."
roadmap issue comment list <issue-id>
```

## Git collaboration loop

Each collaborator updates canonical Roadmap files and uses the repository's
normal review process:

```bash
git pull --rebase
roadmap issue update <issue-id> --status review
git add .roadmap/
git commit -m "Move issue to review"
git push
```

Resolve a canonical-file conflict as a normal text conflict, review the merged
meaning, then run `roadmap health`. The local SQLite projection is not shared
state and must not win over canonical Markdown or YAML.

Retained local conveniences include:

```bash
roadmap git status
roadmap git branch <issue-id>
roadmap git link <issue-id>
```

These commands inspect or create explicit local Git context. They do not fetch,
push, reconcile provider issues, or infer state transitions from commit text.

## Dependency and blocker loop

```bash
roadmap issue deps add <blocked-id> <dependency-id>
roadmap issue block <blocked-id> --reason "Waiting for dependency"
roadmap analysis critical-path

# When the dependency is resolved:
roadmap issue deps remove <blocked-id> <dependency-id>
roadmap issue unblock <blocked-id> --reason "Dependency resolved"
```

## Reporting and automation

Prefer documented structured output over parsing terminal tables:

```bash
roadmap issue list --format json
roadmap milestone list --format csv
roadmap status --format json --output status.json
roadmap data export --format csv --output roadmap.csv
```

Treat stderr as diagnostics and check the process status: `0` is success, `1`
is an application failure, and `2` is invalid command usage.

## Diagnosis and recovery

```bash
roadmap health --details
roadmap health scan --details --group-by severity
roadmap health fix --dry-run
```

Make a Git commit or backup before applying repair. The 0.2 repair contract is
diagnosis-first and scoped; canonical files remain authoritative, and a damaged
SQLite projection must be rebuildable without changing their semantic content.

## Removed 0.1.1 workflows

These experimental surfaces are absent in 0.2:

- `roadmap sync` or `roadmap git sync`;
- GitHub link, lookup, unlink, or link-validation commands;
- Roadmap-managed authentication or provider credentials;
- Roadmap-installed Git hooks; or
- commit-message-driven issue mutation.

Use Git directly for network collaboration and explicit Roadmap commands for
planning state. See the
[0.2 public contract](../architecture/public-contract-0.2.md) for migration
guidance, the [removal guide](REMOTE_SYNC_REMOVAL_0_2.md), and the complete
compatibility inventory.
