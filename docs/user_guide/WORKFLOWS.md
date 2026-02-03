# Workflows: How Teams Use Roadmap

Real-world patterns for different team structures.

## Solo Developer Workflow

**Goal:** Manage personal projects with minimal overhead.

### Daily Routine

```bash
# Morning: Check what you should work on today
roadmap today

# During work: Update status as you go
roadmap issue update issue-id --status in-progress
roadmap issue update issue-id --progress 50

# Before committing: Reference the issue
git commit -m "fixes issue-id: implement feature"
# Status auto-updates to done on commit

# Evening: See what you accomplished
roadmap today  # Shows completed items
```

### Weekly Planning

```bash
# Review upcoming milestone
roadmap milestone list

# See what's still pending
roadmap issue list --filter status=todo --filter milestone="v1.0"

# Plan for next week
roadmap issue create "Refactor database layer"
roadmap issue update issue-id --milestone "v1.0"
```

### Integration with Git

Roadmap watches your commits:

```bash
# Option 1: Use standard git syntax
git commit -m "fixes #issue-id: implement auth"

# Option 2: Use roadmap syntax
git commit -m "[closes roadmap:issue-id] auth complete"

# Either way: Issue auto-marks as done and progress → 100%
```

---

## GitHub Sync Workflow

**Goal:** Keep roadmap synchronized with GitHub issues.

### Understanding the Sync Architecture

The sync process is designed to give you full control over git operations:

1. **Sync modifies files**: `roadmap sync` updates `.roadmap/issues/*.md` with remote data
2. **You control git**: You manually `git add`, `git commit`, `git push`
3. **No prompts**: Changes apply immediately (use `--dry-run` to preview)
4. **Smart conflict resolution**: Automatic merge with configurable strategies

### Typical Sync Workflow

```bash
# Step 1: Preview what would be synced
roadmap sync --dry-run

# Step 2: Run sync (applies changes to local files)
roadmap sync

# Step 3: Review what changed
git diff .roadmap/

# Step 4: Commit and push the changes
git add .roadmap/
git commit -m "chore: sync issues from GitHub"
git push

# Step 5: Continue with your work
roadmap today
```

### Advanced Sync Options

```bash
# Sync with verbose output (see all pulls/pushes)
roadmap sync --verbose

# Resolve conflicts by keeping local changes
roadmap sync --force-local

# Resolve conflicts by keeping remote changes
roadmap sync --force-remote

# Dry-run with verbose output (safe preview)
roadmap sync --dry-run --verbose
```

### Integration with Team Workflow

For teams, sync typically happens:

1. **Morning**: `roadmap sync` to get latest GitHub issues
2. **During work**: Update issues locally with `roadmap issue update`
3. **Before standup**: `roadmap sync --dry-run --verbose` to see what changed
4. **Before merging**: `roadmap sync` to pull any GitHub activity, then commit/push
5. **End of day**: Push sync changes to git

Example:

```bash
# Morning sync
roadmap sync
git add .roadmap/ && git commit -m "chore: morning sync" && git push

# Work during the day (on feature branch)
git checkout -b feat/feature-name
roadmap issue update issue-id --status in-progress
# ... make code changes ...
git commit -m "fixes issue-id: implement feature"

# Before creating PR, get latest from main
git checkout main && git pull
roadmap sync --dry-run --verbose  # Safe preview
roadmap sync  # Apply latest changes
git add .roadmap/ && git commit -m "chore: pre-pr sync" && git push

# Create PR
git checkout feat/feature-name
git rebase main
git push
# ... create and merge PR ...
```

---

## Small Team Workflow (3-8 people)

**Goal:** Coordinate work across developers with PM visibility.

### PM Assigns Work (Morning)

```bash
# Create milestone
roadmap milestone create "Sprint 1" --due-date 2025-01-31

# Create issues for the sprint
roadmap issue create "API endpoint: /users" --priority high
roadmap issue create "Database schema" --priority high
roadmap issue create "Frontend list view" --priority medium

# Assign to team members
roadmap issue update issue-1 --assignee alice
roadmap issue update issue-2 --assignee bob
roadmap issue update issue-3 --assignee alice

# Assign all to milestone
roadmap issue update issue-1 --milestone "Sprint 1"
roadmap issue update issue-2 --milestone "Sprint 1"
roadmap issue update issue-3 --milestone "Sprint 1"

# Commit assignments to git
git add .roadmap/
git commit -m "chore: sprint 1 assignments"
```

### Developers Work (During Sprint)

```bash
# Alice: Start her work
roadmap today  # Shows her 2 assigned items

roadmap issue update issue-1 --status in-progress
git checkout -b feat/users-api

# ... code and commit ...

git commit -m "fixes issue-1: implement user endpoint"
# Issue auto-marks as done!

# Bob: Check progress
roadmap issue list --filter milestone="Sprint 1"
# Shows: issue-1 (done), issue-2 (todo), issue-3 (in-progress)
```

### Team Discussion & Feedback (Async)

```bash
# Alice leaves feedback on Bob's work
roadmap issue comment add issue-2 "Great implementation! One question: did you consider the edge case for null names?"

# Bob replies to specific comment
roadmap issue comment list issue-2  # View the comment first to get ID
roadmap issue comment add issue-2 "Good catch! I'll handle that in a follow-up." --reply-to 101

# PM asks for status update
roadmap issue comment add issue-1 "Is this blocking the frontend work? Let me know if you need help!"

# View all discussion on an issue
roadmap issue comment list issue-2 --format json  # For automation

# Comments persist in git, full history is visible
git log -p .roadmap/issues/  # See every comment added
```

This keeps discussions in context without switching to Slack, email, or GitHub.

### PM Tracks Progress (Midweek)

```bash
# See sprint status
roadmap milestone list

# Output shows:
# Sprint 1: 1 done, 2 in-progress, 0 todo (50% complete)

# Identify blockers
roadmap issue list --filter status=blocked

# See team workload
roadmap issue list --format json | jq '.[] | {assignee, status}'
```

### End-of-Sprint Review (Friday)

```bash
# Export final status for stakeholders
roadmap data export csv --format sprint-1-final
# Or pipe to another tool for analysis

# Archive completed issues
roadmap issue archive --filter milestone="Sprint 1" --filter status=done

# Plan next sprint
# Repeat the PM workflow from Monday
```

---

## Distributed Team Workflow (8+ people, multiple repos)

**Goal:** Manage work across multiple repos with centralized visibility.

### Team Setup

```bash
# Each repo has its own .roadmap/ folder
repo-1/.roadmap/              # Frontend
repo-2/.roadmap/              # Backend API
repo-3/.roadmap/              # Mobile

# Shared roadmap repo or document for cross-repo milestones
shared-roadmap/
  .roadmap/
    roadmap.md                # High-level quarterly roadmap
    milestones/
      q1-2025.md             # Quarterly planning
```

### Cross-Repo Synchronization

```bash
# Sync all repos to central dashboard
for repo in frontend backend mobile; do
  cd $repo
  roadmap data export json > ../status/$repo-status.json
  cd ..
done

# Git stores these snapshots for history
git add status/
git commit -m "chore: status snapshot $(date +%Y-%m-%d)"
```

### PM Visibility

```bash
# Example: Aggregate status across repos
jq '.[] | {repo: "frontend", assignee, status}' status/frontend-status.json
jq '.[] | {repo: "backend", assignee, status}' status/backend-status.json

# Or use roadmap in shared repo for milestones
roadmap milestone list  # Shows high-level roadmap
```

---

## Use Cases & Integration

### Scripting with Roadmap

Because roadmap outputs JSON and plain text, you can pipe to other tools:

```bash
# Export issues assigned to you
roadmap issue list --format json --filter assignee=you | \
  jq '.[] | select(.status != "done") | {id, title, priority}'

# Find all high-priority blockers
roadmap issue list --format json | \
  jq '.[] | select(.priority == "high" and .status == "blocked")'

# Count issues by assignee
roadmap issue list --format json | \
  jq 'group_by(.assignee) | map({assignee: .[0].assignee, count: length})'

# Export to CSV for reporting (Excel-compatible)
roadmap data export csv --format detailed > roadmap.csv
```

### Automation with Cron

```bash
# Crontab: Daily status snapshot at 5pm
0 17 * * * cd /path/to/repo && \
  roadmap data export json > snapshots/$(date +\%Y-\%m-\%d).json && \
  git add snapshots && \
  git commit -m "chore: status snapshot" || true

# Now you have daily history of project status
git log snapshots/     # See when statuses changed
git show snapshots/2025-01-15.json  # See status on that date
```

### CI/CD Integration

```yaml
# Example: GitHub Actions checking roadmap health
name: Roadmap Health Check
on: [push]
jobs:
  roadmap-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install roadmap
        run: pip install roadmap
      - name: Validate roadmap
        run: roadmap health check
      - name: Check for blockers
        run: |
          BLOCKERS=$(roadmap issue list --format json | \
            jq '[.[] | select(.status == "blocked")] | length')
          if [ $BLOCKERS -gt 0 ]; then
            echo "⚠️  $BLOCKERS issues are blocked!"
            exit 1
          fi
```

---

## Tips for Success

### ✅ Do This

- **Update status regularly** - Stale data is worse than no data
- **Use commits to track work** - `fixes issue-id` auto-updates the roadmap
- **Assign to milestones** - Helps PM see sprint progress at a glance
- **Export for stakeholders** - JSON/CSV for non-technical PM/exec views
- **Archive completed work** - Keep `.roadmap/` focused on active items

### ❌ Avoid This

- **Manually updating status after commit** - Status auto-updates, don't duplicate effort
- **Over-prioritizing everything** - "high" priority should mean "actually urgent"
- **Creating 100 issues at once** - Start with next 2 weeks of work
- **Forgetting to commit** - Changes in `.roadmap/` don't matter if not in git

---

## Next Steps

- **[Architecture Guide](../developer_notes/ARCHITECTURE.md)** - Understand the file structure
- **[FAQ](FAQ.md)** - Common questions about workflows
- **[Quick Start](QUICK_START.md)** - Get running in 5 minutes
