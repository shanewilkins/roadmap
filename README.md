# Roadmap CLI

> **Project Management as Code** — Manage your project in git, not in a tool.

Roadmap is a CLI-first project management tool designed for developers who want to keep their project data in git, not locked away in another SaaS tool. If you use git, shell scripts, and plain text files, Roadmap feels like home.

## The Problem

Modern project management tools solve a problem developers don't have:

- **You already track work in git.** Commit messages, PRs, issues in GitHub/GitLab... it's all there.
- **You duplicate effort.** Update status in Jira, then mention it in Slack, then close the GitHub issue. Same information, three places.
- **You can't script your workflow.** Want to auto-assign issues based on a commit? Good luck with most tools.
- **Your data lives elsewhere.** Offline? Can't access your roadmap. Switching tools? Export is painful.

## The Solution

Roadmap stores your project data in **plain YAML + Markdown files tracked in git**. This simple approach gives you:

| Problem | Solution |
| --- | --- |
| **Duplicated data entry** | Single source of truth: your git repo |
| **Manual status updates** | Auto-sync on commits (`fixes issue-123`) |
| **No offline access** | Clone the repo, work offline, push changes |
| **Vendor lock-in** | Files stay plain text forever |
| **Non-scriptable workflow** | Composable with `jq`, `fzf`, `ripgrep`, shell scripts |
| **Missing context** | Full git history + blame for every change |
| **Team bloat for small teams** | Start solo, scale to teams without learning new tool |

Project management as a durable, automatable, self-owned system — not a product you rent.

## Why It Works for Small Teams

### For Solo Developers

```bash
roadmap today                    # What am I working on?
roadmap issue update 42 done     # Mark issue done
git log --oneline                # See what I shipped
```

No UI to load. No notifications to ignore. Just you, your terminal, and your git history.

### For Small Teams (3-8 people)

```bash
roadmap issue list --filter assignee=alice
roadmap milestone list --project web-app
git push && roadmap sync github   # Two-way sync with GitHub
```

Everyone sees the same data (it's in git). Changes are trackable (git blame). Decisions are documented (commits). No meetings about "where is the roadmap file?"

### For Distributed Teams

```bash
roadmap issue create "API pagination" --assignee bob --milestone sprint-2
# Bob works offline, commits changes locally
# Roadmap auto-updates via commit message: git commit -m "fixes API pagination"
git pull                         # Everyone syncs to latest
roadmap sync github              # GitHub issues stay in sync
```

Git is the synchronization layer. No merge conflicts on simple status changes. No "who has the lock?"

## Key Features

### 📋 Issue Management

- Create, list, update, delete issues
- Status tracking (todo, in-progress, blocked, review, done)
- Priority levels (low, medium, high, critical)
- Team assignment and filtering
- Advanced search and sorting

### 📅 Milestone Planning

- Create sprints/releases as milestones
- Track progress (how many issues done?)
- Due dates and scope management
- Link issues to milestones

### 🚀 Roadmap Planning

- High-level quarterly/annual plans
- Organize milestones by roadmap
- Strategic tracking

### 🔗 Git Integration

- **Auto-sync on commit:** `git commit -m "fixes issue-42"` → issue status updates
- **Two-way GitHub sync:** Pull requests → issues, status changes → PR labels
- **Commit blame:** See who changed what and when

### 📊 Output Formats

```bash
roadmap today                    # Rich (interactive)
roadmap today --format json      # JSON (for scripting)
roadmap today --format csv       # CSV (for spreadsheets)
roadmap today --format plain     # Plain text (for pipes)
```

**Composable with Unix tools:**

```bash
roadmap issue list --format json | jq '.[] | select(.priority == "critical")'
roadmap today --format csv | fzf --preview 'cat {}'
roadmap issue list --format plain | grep -i "performance"
```

### 🔐 Secure by Default

- Data stored locally (or in git)
- No cloud account required
- Git history = audit trail
- Credentials managed via system keyring
- Open source (audit the code)

## Requirements

- **Python 3.12 or later** (3.12, 3.13)
- Git (for repository tracking and sync)
- System keyring (for secure credential storage)

## Installation

### Recommended: Poetry or uv

**Poetry** (recommended for projects):

```bash
poetry add roadmap-cli
```

**uv** (fast, lightweight):

```bash
uv tool install roadmap-cli
```

### Pip (simple)

```bash
pip install roadmap-cli
```

### From Source

```bash
git clone https://github.com/shanemiller/roadmap.git
cd roadmap
poetry install
poetry run roadmap --help
```

## Quick Start (5 minutes)

### 1. Initialize your project

```bash
cd my-project
roadmap init
```

This creates `.roadmap/` directory with configuration.

### 2. Create an issue

```bash
roadmap issue create "Fix login timeout issue"
roadmap issue list
```

### 3. Start tracking work

```bash
roadmap issue update 1 in-progress
roadmap issue assign 1 alice
```

### 4. Auto-sync with git

```bash
git commit -m "fixes issue 1: login timeout resolved"
roadmap issue list              # Status auto-updated to 'done'
```

### 5. View your priorities

```bash
roadmap today                   # Your task list
roadmap today --filter priority=critical
```

**→ Next steps:** Read [Quick Start Guide](docs/user_guide/QUICK_START.md) for more examples.

## Documentation

| Guide | For | Time |
| --- | --- | --- |
| **[Quick Start](docs/user_guide/QUICK_START.md)** | New users | 5 min |
| **[Workflows](docs/user_guide/WORKFLOWS.md)** | Real-world patterns | 10 min |
| **[GitHub Sync Setup](docs/user_guide/GITHUB_SYNC_SETUP.md)** | GitHub integration | 10 min |
| **[Milestone Syncing](docs/user_guide/MILESTONE_SYNC.md)** | Milestone dependencies & sync | 15 min |
| **[FAQ](docs/user_guide/FAQ.md)** | Questions & comparisons | 15 min |
| **[Architecture](docs/developer_notes/ARCHITECTURE.md)** | Technical details | 20 min |
| **[Installation](docs/user_guide/INSTALLATION.md)** | Setup & troubleshooting | varies |
| **[Security](docs/developer_notes/SECURITY.md)** | Privacy & safety | 10 min |
| **[Future Features](docs/developer_notes/FUTURE_FEATURES.md)** | Roadmap (v1.1+) | 5 min |

## Compare to Other Tools

| Tool | Model | Data | Good For | Bad For |
| --- | --- | --- | --- | --- |
| **Jira** | SaaS/On-prem | Proprietary DB | Large enterprises | Small teams, CLI, offline work |
| **Linear** | SaaS | Cloud | Growing startups | No offline, no git-native |
| **Trello** | SaaS | Cloud | Visual boards | Serious PM, git-less |
| **GitHub Issues** | SaaS | GitHub | Open source | Cross-repo, multiple teams |
| **Notion** | SaaS | Cloud | Note-taking | Structured workflows |
| **Roadmap** | CLI | Git + YAML | Small teams, developers | Enterprise RBAC, Web UI |

See [FAQ.md](docs/user_guide/FAQ.md) for deeper comparisons.

## Scope & Limitations

### What Roadmap Does Well

**Single Repository:**

- Track issues, milestones, and roadmaps within one repo
- Organize work by priority, assignment, and status
- Integrate with git commits via auto-sync
- Export to multiple formats for reporting
- Work offline, sync when ready

**Small Teams (1-8 people):**

- Everyone has read/write access to the repo
- Git-based synchronization (no merge conflicts on simple status changes)
- All changes are tracked and auditable via git history
- CLI-first workflow matches developer preferences

### What Roadmap Doesn't Do

**Multiple Repositories:**

- This tool is repo-scoped by design (each repo gets its own `.roadmap` directory)
- If you manage multiple related projects across repos, use:
  - GitHub Projects (free, integrated with repos)
  - Jira or Linear (enterprise, for complex coordination)
  - Your own meta-layer (if you need something custom)
- Each repo runs independently; there's no built-in cross-repo aggregation

**Enterprise Features:**

- Complex RBAC (role-based access control)
- Multiple teams with separate permissions
- Audit logging and compliance reporting
- Web UI and mobile access
- SaaS infrastructure

For these, use Jira, Linear, or GitHub Enterprise.

**Why This Scope?**

Roadmap intentionally stays small because:

1. **It solves the actual problem** for solo devs and small teams (duplicate data entry)
2. **Larger teams benefit from better tools** (Jira, Linear) that solve different problems
3. **Git as the sync layer** works at scale up to ~5 projects per person
4. **Simplicity is a feature** — less code = fewer bugs = easier to fork/modify

### Future-Proofing

The schema includes optional `repo_url` (on projects) and `project_id` (on milestones) fields for future tooling that might aggregate across repos. These fields are unused today but allow extensions without breaking existing data.

## Real-World Example

### Solo Developer

```bash
# Monday: Plan sprint
roadmap milestone create sprint-12 --due 2025-02-14
roadmap issue create "Refactor auth module" --milestone sprint-12 --priority high

# Wednesday: Work offline
git clone . ~/offline
cd ~/offline
# ... code ...
git commit -m "refactors auth module, fixes security issue"
roadmap issue status 42 done   # Mark done

# Friday: Sync and review
git push
roadmap today --done            # See what shipped
roadmap sync github             # Update GitHub labels
```

### Small Team (PM + 3 devs)

```bash
# Monday standup (async in Slack)
roadmap today --format json | jq '.[] | .title' | sort
# → Shows everyone's tasks

# Devs work independently
git commit -m "implements new API endpoint [closes roadmap:issue-58]"
roadmap sync github             # PR gets linked to issue

# Friday metrics
roadmap analysis velocity sprint-12    # How many issues completed?
```

See [Workflows.md](docs/user_guide/WORKFLOWS.md) for more patterns.

## Integrations

### Works Well With

**CLI Tools:**

- [`jq`](https://stedolan.github.io/jq/) — Query issues as JSON
- [`fzf`](https://github.com/junegunn/fzf) — Fuzzy find issues
- [`ripgrep`](https://github.com/BurntSushi/ripgrep) — Search issue descriptions
- Standard Unix: `grep`, `awk`, `sed`, `sort`, `uniq`

**Development:**

- Git hooks (auto-sync on commit)
- GitHub/GitLab (two-way sync)
- CI/CD (create issues on test failures)
- Cron jobs (daily snapshots, reminders)

**Data:**

- Spreadsheets (export to CSV)
- Grafana (stream metrics)
- Slack (notify on updates)

See [Workflows.md](docs/user_guide/WORKFLOWS.md#Automating) for integration examples.

## Philosophy

- **Plain text first.** Data lives in YAML + Markdown, tracked in git.
- **CLI-native.** Full power from your terminal. No bloated UI.
- **Offline by default.** Clone repo, work anywhere, push changes.
- **Git is your database.** History, blame, and rollback come free.
- **Composable.** Works with `jq`, shell scripts, and Unix tools.
- **Developer-friendly.** Made by developers, for developers.

## Getting Help

- **Questions?** See [FAQ.md](docs/user_guide/FAQ.md)
- **Getting started?** See [Quick Start](docs/user_guide/QUICK_START.md)
- **Ideas?** See [Future Features](docs/developer_notes/FUTURE_FEATURES.md)
- **Bugs?** [Report on GitHub](https://github.com/shanemiller/roadmap/issues)
- **Contributing?** [Join us!](CONTRIBUTING.md) (coming soon)

## License

[License.md](LICENSE.md) — MIT

---

**Ready to stop duplicating your work?** [Get started in 5 minutes →](docs/user_guide/QUICK_START.md)
