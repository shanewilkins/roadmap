# GitHub Sync Setup

To sync with GitHub, you need to:

## 1. Create a GitHub Personal Access Token

Visit: https://github.com/settings/tokens/new

Create a token with:
- `repo` scope (full control of private repositories)
- `workflow` scope (if you want to trigger workflows)

## 2. Store the Token

Option A - Environment Variable:
```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Option B - System Keychain (macOS):
Store it securely via the CLI:

```bash
roadmap git setup --auth
```

## 3. Configure GitHub in Roadmap

Set the repository and enable sync:

```bash
roadmap config set github.repository "owner/repo"
roadmap config set github.enabled true
roadmap config set github.sync_enabled true
roadmap config set github.sync_backend github
```

## 4. Sync with GitHub

### Preview Changes (Dry-Run)

```bash
# See what would be synced without making changes
roadmap sync --dry-run
```

### Sync and Apply Changes

```bash
# Sync with GitHub API
# This pulls remote issues and pushes local changes
roadmap sync

# Note: Sync modifies files in .roadmap/issues/ but does NOT commit/push to git
# You must manually manage git:
git add .roadmap/
git commit -m "chore: sync with GitHub"
git push
```

### View Detailed Sync Information

```bash
# See all pulls and pushes during sync
roadmap sync --verbose
```

### Resolve Conflicts

```bash
# Automatically keep local changes when conflicts occur
roadmap sync --force-local

# Automatically keep remote changes when conflicts occur
roadmap sync --force-remote
```

## Understanding the Sync Workflow

The new sync architecture gives you full control:

1. **Sync modifies files**: `roadmap sync` updates `.roadmap/issues/*.md` files
2. **You control git**: You manually run `git add`, `git commit`, `git push`
3. **No confirmation prompts**: Changes are applied immediately (unless `--dry-run`)
4. **Preview before committing**: Use `--dry-run` to preview changes first

### Typical Workflow

```bash
# Step 1: Preview changes
roadmap sync --dry-run

# Step 2: Run sync and apply changes to local files
roadmap sync

# Step 3: Review what changed
git diff .roadmap/

# Step 4: Commit and push
git add .roadmap/
git commit -m "chore: sync with GitHub"
git push
```

## Current Status

- ✅ GitHub config created
- ✅ GitHub token configured
- ✅ Sync command implemented and ready
- ✅ Backend agnostic (GitHub or self-hosted)
