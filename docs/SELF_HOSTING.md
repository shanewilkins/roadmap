# Self-Hosting Roadmaps with Vanilla Git

This guide explains how to set up and sync roadmaps using vanilla Git (push/pull) instead of GitHub's API. This approach works with any Git hosting platform: GitHub, GitLab, Gitea, Gitbucket, or vanilla Git over SSH.

## Overview

The roadmap CLI supports two sync backends:

1. **GitHub Backend** - Uses GitHub REST API
   - Requires GitHub personal access token
   - Full feature support (labels, milestones, etc.)
   - Only works with GitHub

2. **Vanilla Git Backend** - Uses git push/pull
   - No API required
   - Works with any Git hosting
   - Minimal setup
   - Perfect for offline-first workflows

## Quick Start: Vanilla Git Backend

### Prerequisites

- Git installed and configured
- A git repository (local or remote)
- Roadmap CLI installed

### 1. Initialize Roadmap with Git Backend

```bash
cd your-project
roadmap init --name=.roadmap --sync-backend=git
```

This creates a `.roadmap/` directory with the roadmap structure, configured to use git push/pull for syncing.

### 2. Create Issues

```bash
roadmap issue create "Build API layer" --milestone=v1.0
roadmap issue create "Write documentation" --milestone=v1.0
```

### 3. Sync to Remote

```bash
# Preview changes
roadmap git sync --dry-run

# Apply sync (push local changes to remote)
roadmap git sync
```

That's it! Your issues are now synced to the remote repository.

## Configuration

### .github/config.json

The sync configuration is stored in `.github/config.json`:

```json
{
  "backend": "git",
  "github": {
    "owner": "optional",
    "repo": "optional"
  }
}
```

### Configuration Options

**backend**: Which sync backend to use
- `"git"` - Vanilla Git push/pull (default for non-GitHub setups)
- `"github"` - GitHub REST API (requires token)

**github** (optional): GitHub repository information
- `owner`: GitHub username or organization
- `repo`: Repository name

## Vanilla Git Backend Details

### How It Works

The vanilla git backend syncs roadmap issues by:

1. **Push**: Stages and commits issue files to git, then pushes to remote
2. **Pull**: Fetches from remote and merges changes locally
3. **Conflict Resolution**: Uses git merge conflict resolution (checkout --ours/theirs)

### Issue Storage

Issues are stored as YAML files in `.roadmap/issues/`:

```
.roadmap/
├── issues/
│   ├── v.1.0.0/
│   │   ├── {issue-id}.md      # Individual issue file
│   │   ├── {issue-id}.md
│   │   └── ...
│   └── archive/
│       └── ...
├── config.yaml
└── ...
```

Each issue is a separate file, making git history clear and diffs readable.

### Git Workflow

```bash
# Check sync status
roadmap git sync --dry-run

# Push local changes
roadmap git sync

# With conflict resolution
roadmap git sync --force-local   # Keep local changes
roadmap git sync --force-remote  # Keep remote changes
```

## Switching Between Backends

### From GitHub to Vanilla Git

If you're currently using GitHub backend and want to switch:

```bash
# Update configuration
# Edit .github/config.json:
# {
#   "backend": "git",
#   ...
# }

# Future syncs will use git
roadmap git sync
```

**Note**: Existing GitHub-linked issues (with `github_issue` IDs) will be skipped. Create new unlinked issues to sync via git.

### From Vanilla Git to GitHub

```bash
# Get/refresh GitHub token from https://github.com/settings/tokens
export GITHUB_TOKEN="ghp_..."

# Update configuration
# Edit .github/config.json:
# {
#   "backend": "github",
#   "github": {
#     "owner": "your-org",
#     "repo": "your-repo"
#   }
# }

# Re-run init to set up GitHub integration
roadmap init --sync-backend=github --github-repo=your-org/your-repo
```

## Common Scenarios

### Scenario 1: Team Collaboration on GitLab

Your team uses GitLab instead of GitHub:

```bash
# Initialize roadmap
roadmap init --name=.roadmap --sync-backend=git

# Configure remote (GitLab)
git remote add origin git@gitlab.com:your-team/your-project.git

# Create and sync issues
roadmap issue create "Feature request"
roadmap git sync

# Others can pull and see issues
git pull origin main
roadmap issue list
```

### Scenario 2: Offline-First Development

Working offline with sync when connection returns:

```bash
# Create issues while offline
roadmap issue create "Build feature X"
roadmap issue create "Test feature X"

# Reconnect to network, sync all changes
roadmap git sync --dry-run    # Preview
roadmap git sync              # Apply
```

### Scenario 3: Self-Hosted Git Server

Using a self-hosted Gitea, Gitbucket, or plain git server:

```bash
# Initialize with git backend (works with any git host)
roadmap init --sync-backend=git

# Set up SSH access
git remote add origin ssh://git.example.com/path/to/repo.git

# Sync normally - no API keys needed
roadmap git sync
```

### Scenario 4: Bridging Teams

Part of your team on GitHub, others on different platforms:

```bash
# Create GitHub-linked issues
roadmap issue create "API endpoint" --github-issue=123

# Create git-only issues for non-GitHub tools
roadmap issue create "Database migration"

# Sync happens automatically to the right places:
# - GitHub issues → GitHub API
# - Git-only issues → Git push/pull
roadmap git sync
```

## Troubleshooting

### "Failed to initialize git backend"

**Cause**: Not in a git repository or git not available

**Solution**:
```bash
# Initialize git repository
git init
git remote add origin <your-remote>

# Then init roadmap
roadmap init --sync-backend=git
```

### "Backend authentication failed"

**Cause**: Git can't access the remote (SSH key missing, wrong credentials)

**Solution**:
```bash
# Test git access
git fetch origin

# If SSH: ensure SSH key is loaded
ssh-add ~/.ssh/id_rsa

# Then retry sync
roadmap git sync
```

### "Conflicts detected"

**Cause**: Local and remote both have changes to same issues

**Solution**:
```bash
# View conflicts
roadmap git sync --dry-run

# Resolve with force options
roadmap git sync --force-local   # Keep your changes
roadmap git sync --force-remote  # Accept remote changes

# Or manually resolve
git status
# ... fix conflicts in .roadmap/issues/ ...
roadmap git sync
```

### "No issues found"

**Cause**: Sync preview shows no changes, but you expect some

**Solution**:
```bash
# Check local issues exist
roadmap issue list

# Check git status
git status

# Make sure you're syncing correct backend
# Edit .github/config.json to verify "backend": "git"

# Try explicit sync
roadmap git sync --verbose
```

## Advanced Usage

### Custom Remote

By default, sync uses the `origin` remote. To use a different remote:

```bash
# Configure custom remote
git remote add production <url>

# Sync to production remote
roadmap git sync --remote=production
```

### Batch Sync Operations

Push multiple issues efficiently:

```bash
# Create multiple issues
roadmap issue create "Fix #1"
roadmap issue create "Fix #2"
roadmap issue create "Fix #3"

# Single sync does batch push (more efficient)
roadmap git sync

# Single commit with all changes
git log --oneline -1  # Shows "Sync 3 issues"
```

### Integration with CI/CD

Automatically sync roadmap updates:

```yaml
# .github/workflows/sync-roadmap.yml
name: Sync Roadmap

on:
  push:
    paths:
      - '.roadmap/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install roadmap-cli
      - run: roadmap git sync
```

### Export to Other Tools

Since issues are plain YAML/Markdown files:

```bash
# Convert to CSV
cd .roadmap/issues/v.1.0.0
for file in *.md; do
  # Parse YAML frontmatter and output CSV
  # ...
done

# Version control
git log -- .roadmap/issues/
```

## Architecture

### SyncBackendInterface Protocol

Both GitHub and vanilla Git backends implement the `SyncBackendInterface`:

```python
class SyncBackendInterface(Protocol):
    def authenticate(self) -> bool:
        """Check authentication and connectivity"""

    def get_issues(self) -> dict:
        """Fetch all remote issues"""

    def push_issue(self, issue: Issue) -> bool:
        """Push single issue to remote"""

    def push_issues(self, issues: List[Issue]) -> SyncReport:
        """Batch push issues"""

    def pull_issues(self) -> SyncReport:
        """Pull remote issues"""

    def resolve_conflict(self, conflict: SyncConflict, strategy: str) -> bool:
        """Resolve sync conflicts"""
```

This ensures consistent behavior across backends while allowing implementation flexibility.

## FAQ

**Q: Can I sync to multiple remotes?**
A: Currently, sync targets a single backend. You can manually push to multiple remotes using git.

**Q: Do I need a GitHub token for vanilla git backend?**
A: No - vanilla git backend requires only git access (SSH or HTTPS credentials).

**Q: Can I have both GitHub-linked and Git-only issues?**
A: Yes - issues with `github_issue` IDs sync via GitHub API; others sync via git.

**Q: Is vanilla git backend offline-capable?**
A: Yes - create/edit issues offline, sync when reconnected.

**Q: Can I switch backends mid-project?**
A: Yes, but old GitHub-linked issues won't sync via git (and vice versa).

## See Also

- [Sync Command Reference](../user-guide/commands/sync.md)
- [Issue Management](../user-guide/issues.md)
- [Architecture Design](../docs/ARCHITECTURE.md)
