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
The roadmap CLI will automatically store it securely after first use with `--github-token`

## 3. Configure GitHub in Roadmap

Create `.github/config.json`:
```json
{
  "github": {
    "owner": "shanewilkins",
    "repo": "roadmap"
  }
}
```

## 4. Run Sync

```bash
# Preview changes
roadmap git sync --dry-run

# Sync with confirmation
roadmap git sync

# Force conflict resolution
roadmap git sync --force-local   # Keep local changes
roadmap git sync --force-github  # Keep GitHub changes
```

## Current Status

- ✅ GitHub config created: `.github/config.json`
- ❌ GitHub token not set (needed for actual sync)
- ✅ Sync command implemented and ready
