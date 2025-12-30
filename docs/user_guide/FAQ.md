# FAQ: Frequently Asked Questions

## Philosophy & Positioning

### Q: Why "project-management-as-code"? Isn't that just storing files in git?

**A:** Yes, but the philosophy is important. Traditional PM tools (Jira, Linear, etc.) lock data in proprietary formats and databases. Project-management-as-code means:

1. **Data is human-readable** - Open a `.md` or `.yaml` file in any editor
2. **Data lives in git** - Track changes, see history, blame who changed what
3. **Portable forever** - If you stop using Roadmap tomorrow, your data is just text files
4. **Automatable** - Script, pipe, integrate with CI/CD, feed to AI tools
5. **Offline-first** - Works completely offline, no cloud dependency

It's the same philosophy that makes Infrastructure-as-Code (Terraform, CloudFormation) valuable.

### Q: Is Roadmap trying to replace Jira?

**A:** For small-to-medium teams, yes. For large enterprises, maybe not.

**Where Roadmap shines:**
- Teams with <50 people
- Developers who want to avoid the Jira overhead
- Teams already using git for everything
- Projects where the PM is technical enough to use CLI

**Where Jira still might win:**
- Enterprise with 500+ people needing complex workflows
- Teams with non-technical PMs who need a GUI
- Organizations with compliance/audit requirements
- Projects needing advanced reporting/dashboards

**Roadmap philosophy:** We're building for developers and small teams, not trying to serve everyone.

### Q: Why CLI-first instead of a web UI?

**A:** Because:

1. **Developers already live in the CLI** - Why learn a new UI when you live in your terminal?
2. **Composability** - CLI tools pipe together beautifully (like Unix philosophy)
3. **Integration** - Easier to integrate with git hooks, CI/CD, scripts, cron jobs
4. **Offline-first** - No internet? Still works.
5. **Accessibility** - Keyboard navigation is better than mouse hunting
6. **Simplicity** - Building a web UI would delay v1.0

A web UI could happen in v2.0+ if there's demand.

---

## Getting Started

### Q: Do I need git knowledge to use Roadmap?

**A:** You need basic git knowledge: `git add`, `git commit`, `git push`. That's it. You don't need to be a git expert.

### Q: Can non-technical PMs use this?

**A:** Probably not in v1.0. Roadmap is CLI-first, which requires comfort with terminal commands. This is intentional—we're optimizing for technical teams.

Future versions could add a web UI for non-technical stakeholders.

### Q: Do I need GitHub integration?

**A:** No, it's optional. You can:
- Use Roadmap standalone (local issues only)
- Sync with GitHub (two-way sync of issues)
- Just use git commits to auto-update status

Choose what fits your workflow.

---

## Data & Architecture

### Q: Where does my data live?

**A:** In the `.roadmap/` folder in your git repo. Example structure:

```
.roadmap/
  config.yaml         # Roadmap configuration
  roadmap.md          # Main roadmap document
  milestones/
    v1-0.md           # v1.0 milestone
    v1-1.md           # v1.1 milestone
  issues/
    issue-abc123.md   # Individual issue file
    issue-def456.md
```

Each file is a standard markdown/YAML file you can edit by hand.

### Q: What format is the data in?

**A:** Each issue is a markdown file with YAML frontmatter:

```markdown
---
id: issue-abc123
title: Implement authentication
status: in-progress
priority: high
assignee: alice
progress: 75
milestone: v1.0
---

# Implementation Details

We need OAuth2 support for GitHub and Google.

## Acceptance Criteria
- [ ] GitHub OAuth works
- [ ] Google OAuth works
- [ ] Session management tested
```

**You can edit these files directly in your editor or via CLI.** Both ways work.

### Q: Can I migrate from Jira to Roadmap?

**A:** In v1.0, you'd need to:
1. Export from Jira as JSON/CSV
2. Write a script to convert to Roadmap format
3. Commit to your repo

We don't have a built-in Jira importer yet, but it's possible (and on the roadmap for v1.1).

### Q: What if multiple people edit the same issue?

**A:** Git handles conflicts like any other file. If Alice and Bob both edit the same issue:

```bash
git pull                    # Get latest
# If there's a conflict:
# Edit the file, resolve manually
git add .roadmap/issues/
git commit -m "Resolved merge conflict"
git push
```

For v1.1+, we're considering:
- Optimistic locking (prevent overwrites)
- Conflict auto-resolution (merge friendly changes)
- Change notifications

### Q: How is this different from just using GitHub issues?

**A:** Good question. GitHub issues are great, but:

| Feature | GitHub Issues | Roadmap |
|---------|---------------|---------|
| **Offline** | No | Yes |
| **In your editor** | No | Yes |
| **Version controlled** | Yes (in GitHub) | Yes (in git) |
| **Programmatic** | GitHub API | CLI + JSON/CSV |
| **Local-first** | No | Yes |
| **Works without GitHub** | No | Yes |
| **Milestones/sprints** | Basic | Rich |
| **Progress tracking** | No | Yes |
| **Cost** | Free (if <3 private repos) | Free |

Use Roadmap locally, sync to GitHub if you want both.

---

## Status & Progress Tracking

### Q: How do issues auto-update when I commit?

**A:** Roadmap watches your commit messages for keywords:

```bash
# Any of these auto-close the issue:
git commit -m "fixes issue-id"
git commit -m "closes issue-id"
git commit -m "resolves issue-id"
git commit -m "[closes roadmap:issue-id]"

# You can also set progress:
git commit -m "Progress on issue-id: 75% complete"
```

### Q: Can I manually update status?

**A:** Yes:

```bash
roadmap issue update issue-id --status done --progress 100
```

But if you also commit with "fixes issue-id", the auto-update will also trigger (that's fine, both set it to done).

### Q: What statuses are available?

**A:** Standard workflow states:

- `todo` - Not started
- `in-progress` - Currently being worked on
- `blocked` - Waiting on something else
- `review` - In code review or QA
- `done` - Completed

Custom statuses coming in v1.1.

---

## Comparison

### Q: How does Roadmap compare to Linear?

**A:**

| Feature | Linear | Roadmap |
|---------|--------|---------|
| **Web UI** | Beautiful | Not yet |
| **Team visibility** | Excellent | Via exports/json |
| **Cost** | $10-20/seat/month | Free |
| **Works offline** | No | Yes |
| **Open source** | No | Yes |
| **GitHub sync** | Limited | Two-way |
| **CLI** | No | Yes |
| **Git-native** | No | Yes |

Linear is better for non-technical PMs. Roadmap is better for developers who want everything in CLI+git.

### Q: How does Roadmap compare to Trello?

**A:** Trello is visual (Kanban board), Roadmap is terminal-based. Different tools for different workflows.

Use Trello if you like dragging cards. Use Roadmap if you like CLIs and git.

### Q: How does Roadmap compare to Asana/Monday.com?

**A:** Those are full-featured project management suites for large teams. Roadmap is intentionally simpler, designed for developers and small technical teams.

---

## Collaboration & Sharing

### Q: How do team members see the roadmap?

**A:** Options:

1. **They have repo access** - They pull `.roadmap/` from git
2. **Export for read-only viewers** - `roadmap data export json` → share HTML/PDF
3. **Daily snapshots to shared folder** - Cron job saves daily status
4. **GitHub sync** - Issues visible in GitHub

### Q: How do I prevent someone from breaking the roadmap?

**A:** Git workflows:

1. **Require code review** - PR reviews before merging to main
2. **Branch protection** - Protect main branch, require reviews
3. **Access control** - GitHub team permissions

For v1.1, we're considering:
- Read-only roles for stakeholders
- Approval workflows for status changes

### Q: Can I generate reports for stakeholders?

**A:** Yes:

```bash
# Export to CSV
roadmap data export csv > status.csv
# Open in Excel

# Export to JSON
roadmap data export json > status.json
# Share as-is or generate HTML report

# Export per-milestone
roadmap milestone list --format json | \
  jq '.[] | {name, status, progress}'
```

For executive reports, you could build a small dashboard that reads these exports.

---

## Integration

### Q: What CLI tools pair well with Roadmap?

**A:** Great question! Roadmap outputs JSON and plain text, so it works with:

- **`jq`** - Query JSON output (`roadmap list --format json | jq '...'`)
- **`fzf`** - Fuzzy search issues (`roadmap issue list | fzf`)
- **`ripgrep` (rg)** - Search `.roadmap/` files quickly
- **`dasel`** - Edit YAML/JSON in pipelines
- **`gron`** - Break down JSON for analysis
- **GNU tools** - `awk`, `sed`, `grep`, `sort`, etc.
- **R / Python** - Load CSV export for analysis
- **Grafana / Datadog** - Ingest status snapshots for dashboards

Roadmap is designed to work **with** Unix tools, not replace them.

### Q: Can I integrate with my CI/CD pipeline?

**A:** Yes:

```yaml
# GitHub Actions example
- name: Check roadmap health
  run: |
    roadmap health check          # Validate format
    roadmap issue list            # See current status
    # Use exit codes for pass/fail
```

Examples coming in documentation.

---

## Troubleshooting

### Q: Issues aren't auto-updating when I commit

**A:** Check:

1. **Commit message format** - Use `fixes issue-id` (with 'fixes', not 'fixed')
2. **Issue ID is correct** - Use exact ID from roadmap
3. **Commit is pushed** - Auto-update happens on local and remote
4. **Syntax is right** - `fixes issue-abc123`, not `fixes issue abc123`

### Q: I accidentally deleted an issue file

**A:** Use git history:

```bash
git log --oneline -- .roadmap/issues/issue-id.md
git checkout <commit>^:.roadmap/issues/issue-id.md
```

Or just restore from backup in `.roadmap/.backups/`.

### Q: Roadmap is slow with 1000+ issues

**A:** In v1.0, performance is acceptable. For v1.1:

- We're optimizing for 10k+ issues
- Consider splitting into multiple milestones
- Archive completed issues to reduce active list

---

## Future (v1.1+)

### Q: What's planned for future releases?

**A:** See [FUTURE_FEATURES.md](../developer_notes/FUTURE_FEATURES.md) for the full roadmap. Highlights:

- **v1.1**: Historical tracking, trends, analytics
- **v1.2**: Enterprise RBAC, team management
- **v2.0**: Web UI, real-time collaboration, mobile

---

## Still Have Questions?

- Check [QUICK_START.md](QUICK_START.md) for getting started
- See [WORKFLOWS.md](WORKFLOWS.md) for real-world patterns
- Read [ARCHITECTURE.md](../developer_notes/ARCHITECTURE.md) for technical details
- File an issue on GitHub
