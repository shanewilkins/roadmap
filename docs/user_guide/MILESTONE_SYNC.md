# Milestone Syncing Guide

This guide explains how milestone syncing works in Roadmap CLI, including dependency resolution, error handling, and best practices.

## Overview

Milestone syncing ensures that milestones and their dependencies are properly synchronized between your local Roadmap database and GitHub. The sync process:

1. **Fetches milestones** from GitHub with dependency metadata
2. **Resolves dependencies** using topological sorting
3. **Syncs in correct order** to avoid constraint violations
4. **Handles errors** with detailed categorization and recommendations

## Key Features

### 🔗 Dependency Resolution

Milestones can depend on other milestones, creating dependency chains. The sync system automatically:

- Detects milestone-to-milestone dependencies
- Orders syncing using topological sort
- Ensures parent milestones sync before dependent milestones
- Prevents circular dependency issues

**Example Dependency Chain:**
```
Project 1.0
├── Milestone: Foundation (no dependencies)
├── Milestone: Core Features (depends on: Foundation)
└── Milestone: Polish (depends on: Core Features)
```

The sync will automatically process in order: Foundation → Core Features → Polish

### 🔄 Circular Dependency Detection

The system detects and reports circular dependencies:

**Example Circular Chain:**
```
M1 depends on M2
M2 depends on M3
M3 depends on M1  ← Circular!
```

**Result:**
```
⚠️  Circular dependency detected: M1 → M2 → M3 → M1
```

### 📊 Error Classification

Sync errors are categorized into 7 groups with specific recommendations:

| Category | Icon | Description | Common Causes |
|----------|------|-------------|---------------|
| **Dependency Errors** | 🔗 | Missing milestones or projects | Out-of-order sync, deleted resources |
| **API Errors** | 🌐 | GitHub API issues | Rate limits, timeouts, service unavailable |
| **Authentication Errors** | 🔒 | Token or permission issues | Expired token, insufficient scopes |
| **Data Errors** | 💾 | Database or validation issues | Constraint violations, schema mismatches |
| **Resource Errors** | 📦 | Deleted or missing resources | Cleanup, renamed items |
| **File System Errors** | 📁 | File access issues | Permissions, disk space |
| **Unknown Errors** | ❓ | Unclassified errors | Various causes |

## Usage

### Basic Sync

```bash
# Sync milestones and issues with GitHub
roadmap sync
```

### Verbose Mode

Show detailed information including dependency resolution and error details:

```bash
# Detailed sync output with error examples
roadmap sync --verbose
```

**Verbose output includes:**
- Milestone dependency chains
- First 5 affected issue IDs per error category
- Truncated error messages (80 chars)
- Detailed recommendations

### Preview Changes

```bash
# See what would be synced without applying
roadmap sync --dry-run
```

### Targeted Sync Operations

```bash
# Pull remote changes only (no push)
roadmap sync --pull

# Push local changes only (no pull)
roadmap sync --push

# Show detailed conflict information
roadmap sync --conflicts
```

## Dependency Resolution Process

### 1. Fetch Phase

```
📥 Fetching milestones from GitHub...
   ├── Milestone 1: Foundation
   ├── Milestone 2: Core Features (depends on: Foundation)
   └── Milestone 3: Polish (depends on: Core Features)
```

### 2. Resolution Phase

```
🔄 Resolving milestone dependencies...
   ├── Building dependency graph
   ├── Detecting circular dependencies
   ├── Topological sorting
   └── Order established: Foundation → Core → Polish
```

### 3. Sync Phase

```
⬆️  Syncing milestones in dependency order...
   ✓ Foundation (no dependencies)
   ✓ Core Features (depends on: Foundation)
   ✓ Polish (depends on: Core Features)
```

## Error Handling

### Missing Dependencies

When a milestone depends on a non-existent milestone:

```bash
⚠️  Sync Errors
Total errors: 1 across 1 issues

🔗 Dependency Errors (1)
  Fix: Ensure all dependencies (milestones, projects) are synced first.
       Run 'roadmap sync' again.
```

**Solution:**
1. Verify the dependency exists in GitHub
2. Run `roadmap sync` again to pull the missing milestone
3. If persistent, check for typos in milestone dependencies

### Circular Dependencies

When milestones have circular dependencies:

```bash
⚠️  Sync Errors
Total errors: 3 issues

🔗 Dependency Errors (3)
  Fix: Circular dependency chain detected.
       Break the cycle by removing one dependency.

Circular chain: M1 → M2 → M3 → M1
```

**Solution:**
1. Identify the dependency chain in GitHub
2. Remove one dependency to break the cycle
3. Re-run sync after fixing

### API Rate Limits

```bash
⚠️  Sync Errors
Total errors: 5 across 5 issues

🌐 API Errors (5)
  Fix: Check GitHub service status at https://githubstatus.com.
       Retry after a short wait.
```

**Solution:**
1. Wait for rate limit to reset (usually 1 hour)
2. Use `roadmap sync --verbose` to see retry attempts
3. The system auto-retries with exponential backoff

### Authentication Issues

```bash
⚠️  Sync Errors
Total errors: 1 across 1 issues

🔒 Authentication Errors (1)
  Fix: Verify GitHub token with 'roadmap config github'.
       Ensure token has required permissions (repo, read:org).
```

**Solution:**
1. Generate new token: https://github.com/settings/tokens
2. Ensure token has `repo` and `read:org` scopes
3. Update with `roadmap config github`

## Best Practices

### 1. Regular Syncs

Sync frequently to minimize conflicts:
```bash
# Add to your workflow
git pull
roadmap sync
# ... make changes ...
git commit -m "Update roadmap"
roadmap sync
git push
```

### 2. Use Dry-Run First

Preview changes before applying:
```bash
# Check what will change
roadmap sync --dry-run

# Apply if acceptable
roadmap sync
```

### 3. Handle Dependencies Carefully

When creating milestone dependencies:
- Ensure parent milestones exist first
- Avoid circular dependencies
- Document dependency rationale in milestone descriptions

### 4. Monitor Sync History

Check sync status periodically:
```bash
# View sync history for an issue
roadmap issue sync-status <issue-id>

# Show recent sync history
roadmap issue sync-status <issue-id> --history
```

### 5. Use Verbose for Troubleshooting

When errors occur:
```bash
# Get detailed error information
roadmap sync --verbose

# Review which issues are affected
# Check recommendations for each error category
```

## Advanced Topics

### Conflict Resolution

When local and remote changes conflict:

```bash
# Always prefer local changes
roadmap sync --force-local

# Always prefer remote changes
roadmap sync --force-remote

# Interactive resolution (default)
roadmap sync
```

### Manual Linking

Link issues manually when needed:
```bash
# Link local issue to GitHub issue #123
roadmap sync --link 123 --issue-id <local-uuid>

# Unlink an issue from GitHub
roadmap sync --unlink --issue-id <local-uuid>
```

### Baseline Management

The sync system maintains a baseline for three-way merging:

```bash
# Show current baseline
roadmap sync --base

# Reset baseline (clears sync history)
roadmap sync --reset-baseline

# Clear baseline entirely
roadmap sync --clear-baseline
```

## Troubleshooting

### Problem: "Milestone not found" errors

**Symptoms:**
```
📦 Resource Errors (3)
  Affected: issue-123, issue-456, issue-789
```

**Solution:**
```bash
# Sync milestones first
roadmap sync --pull

# Verify milestones exist
roadmap milestone list

# Re-sync if needed
roadmap sync
```

### Problem: Circular dependency detected

**Symptoms:**
```
Circular dependency chain: M1 → M2 → M1
```

**Solution:**
1. Visit GitHub repository settings
2. Navigate to Milestones
3. Edit milestone dependencies to break cycle
4. Re-run sync

### Problem: Rate limit exceeded

**Symptoms:**
```
🌐 API Errors (10)
  Fix: Check GitHub service status...
```

**Solution:**
```bash
# Wait 1 hour for rate limit reset
# Or use authenticated requests (should be automatic)

# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

### Problem: Permission denied

**Symptoms:**
```
🔒 Authentication Errors (1)
  Fix: Verify GitHub token...
```

**Solution:**
```bash
# Generate new token with correct scopes
# Required: repo, read:org

# Update configuration
roadmap config github

# Verify connection
roadmap sync --dry-run
```

## Integration with Workflow

### Git Hooks

Automatically sync after git operations:

```bash
# .git/hooks/post-commit
#!/bin/bash
roadmap sync --verbose
```

### CI/CD Integration

Sync in CI pipelines:
```yaml
# .github/workflows/sync-roadmap.yml
name: Sync Roadmap
on: [push]
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Sync Roadmap
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          roadmap sync --verbose
```

## Performance Considerations

- **Large repos**: Sync may take 30-60 seconds for 100+ milestones
- **Rate limits**: GitHub API allows 5000 requests/hour (authenticated)
- **Parallel processing**: The system uses parallel API calls for efficiency
- **Caching**: Baselines are cached to minimize redundant fetches

## Related Commands

- `roadmap milestone list` - View all milestones
- `roadmap milestone view <id>` - View milestone details
- `roadmap issue sync-status <id>` - Check sync history
- `roadmap sync --conflicts` - Analyze conflicts
- `roadmap config github` - Update GitHub configuration

## Further Reading

- [GitHub Sync Setup](./GITHUB_SYNC_SETUP.md) - Initial configuration
- [Workflows](./WORKFLOWS.md) - Common workflow patterns
- [FAQ](./FAQ.md) - Frequently asked questions
