# GitHub Integration Guide

This guide walks you through setting up and using GitHub integration with the Roadmap CLI tool.

## Overview

The Roadmap CLI provides seamless bidirectional synchronization with GitHub repositories, allowing you to:

- Sync local roadmap issues with GitHub issues
- Keep issue status, labels, and assignments in sync
- Work with your roadmap both locally and on GitHub
- Maintain a single source of truth across platforms

## Quick Setup

### 1. Create a GitHub Personal Access Token

1. Go to [GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give your token a descriptive name (e.g., "Roadmap CLI Sync")
4. Select the following scopes:
   - `public_repo` (for public repositories)
   - `repo` (for private repositories, if needed)
5. Click "Generate token"
6. **Important**: Copy the token immediately - you won't see it again!

### 2. Configure Repository Settings

Set up your GitHub repository information:

```bash
roadmap config set github.owner YOUR_GITHUB_USERNAME
roadmap config set github.repo YOUR_REPOSITORY_NAME

```text

### 3. Store Your Credentials

#### Option A: Secure Keychain Storage (Recommended)

```bash
roadmap credentials set-github-token

# You'll be prompted to enter your token securely

```text

#### Option B: Environment Variable

```bash
export GITHUB_TOKEN="your_token_here"

```text

#### Option C: Configuration File

```bash
roadmap config set github.token "your_token_here"

```text

**Security Note**: The keychain storage is the most secure option as it encrypts your token.

### 4. Test the Connection

Verify your setup works:

```bash
roadmap sync test-connection

```text

If successful, you should see a confirmation message.

## Usage

### Initial Sync

To perform your first sync and pull existing GitHub issues:

```bash
roadmap sync from-github

```text

This will:

- Create local issue files for all GitHub issues
- Maintain GitHub issue IDs for future syncing
- Set up the bidirectional sync relationship

### Pushing Local Issues to GitHub

To create GitHub issues from your local roadmap:

```bash
roadmap sync to-github

```text

### Bidirectional Sync

For ongoing synchronization in both directions:

```bash
roadmap sync bidirectional

```text

This command:

- Pushes new local issues to GitHub
- Pulls new GitHub issues to local files
- Updates existing issues in both directions
- Resolves simple conflicts automatically

### Automated Sync

You can set up automatic syncing:

```bash

# Enable automatic sync on issue creation/updates

roadmap config set sync.auto_push true
roadmap config set sync.auto_pull true

# Set sync interval (in minutes)

roadmap config set sync.interval 15

```text

## Configuration Options

### Repository Settings

```bash

# Basic repository configuration

roadmap config set github.owner "your-username"
roadmap config set github.repo "your-repository"

# Optional: Use different GitHub API endpoint (for GitHub Enterprise)

roadmap config set github.api_base_url "https://api.github.com"

```text

### Sync Behavior

```bash

# Automatic sync settings

roadmap config set sync.auto_push true          # Auto-push local changes

roadmap config set sync.auto_pull false         # Manual pull only

roadmap config set sync.interval 30             # Sync every 30 minutes

# Conflict resolution

roadmap config set sync.conflict_resolution "manual"    # or "github_wins", "local_wins"

# Issue filtering

roadmap config set sync.labels_filter "roadmap"        # Only sync issues with this label

roadmap config set sync.exclude_labels "wontfix,duplicate"  # Exclude these labels

```text

### Label Mapping

Map roadmap priorities and types to GitHub labels:

```bash

# Priority mapping

roadmap config set sync.label_map.priority.critical "critical"
roadmap config set sync.label_map.priority.high "high-priority"
roadmap config set sync.label_map.priority.medium "medium-priority"
roadmap config set sync.label_map.priority.low "low-priority"

# Type mapping

roadmap config set sync.label_map.type.feature "enhancement"
roadmap config set sync.label_map.type.bug "bug"
roadmap config set sync.label_map.type.task "task"

```text

## Advanced Features

### Selective Sync

Sync only specific issues or milestones:

```bash

# Sync specific issues

roadmap sync issue ISSUE_ID_1 ISSUE_ID_2

# Sync by milestone

roadmap sync milestone "v1.0"

# Sync by assignee

roadmap sync assignee "username"

```text

### Branch-Based Workflows

Integrate with Git workflows:

```bash

# Sync issues related to current branch

roadmap sync branch

# Sync issues with specific branch patterns

roadmap sync branch --pattern "feature/*"

```text

### Batch Operations

Perform bulk operations:

```bash

# Bulk update issue status

roadmap sync bulk-update --status "in-progress" --assignee "new-assignee"

# Bulk label management

roadmap sync bulk-label --add "sprint-2" --remove "sprint-1"

```text

## Troubleshooting

### Authentication Issues

If you're getting authentication errors:

1. **Verify your token has the right scopes**:
   ```bash
   roadmap sync test-connection --verbose
   ```

2. **Check token storage**:
   ```bash
   roadmap credentials list
   ```

3. **Re-authenticate**:
   ```bash
   roadmap credentials clear
   roadmap credentials set-github-token
   ```

### Sync Conflicts

When issues conflict between local and GitHub:

1. **View conflicts**:
   ```bash
   roadmap sync status --show-conflicts
   ```

2. **Resolve manually**:
   ```bash
   roadmap sync resolve ISSUE_ID --keep-local
   # or

   roadmap sync resolve ISSUE_ID --keep-github
   ```

3. **Set default resolution**:
   ```bash
   roadmap config set sync.conflict_resolution "github_wins"
   ```

### Sync Strategy Configuration

The `sync bidirectional` command supports different conflict resolution strategies:

```bash

# Use local_wins strategy (default - recommended)

roadmap sync bidirectional --strategy local_wins

# Use remote_wins strategy (prefer GitHub)

roadmap sync bidirectional --strategy remote_wins

# Use newer_wins strategy (timestamp-based)

roadmap sync bidirectional --strategy newer_wins

```text

#### Important: GitHub Timestamp Race Condition

**Default Strategy**: The default sync strategy is `local_wins` to prevent a common race condition with GitHub timestamps.

**The Problem**: When using the `newer_wins` strategy with bidirectional sync, a race condition occurs:

1. You mark a local issue as "done"
2. `roadmap sync bidirectional` pushes this change to GitHub (closes the issue)
3. GitHub updates its `updated_at` timestamp when the issue is closed
4. The same sync command then pulls from GitHub and sees GitHub's timestamp is newer
5. This can cause the sync to prefer GitHub's state and potentially override your local changes

**The Solution**: The `local_wins` strategy ensures that local changes take precedence and avoid this timestamp race condition. This is particularly important for workflows where you primarily work locally and sync to GitHub periodically.

**When to Use Other Strategies**:

- `remote_wins`: When GitHub is your primary workspace and local is just a backup
- `newer_wins`: When you have multiple team members making changes both locally and on GitHub, and you want true timestamp-based resolution (understanding the race condition risk)

### Rate Limiting

If you hit GitHub API rate limits:

1. **Check your rate limit status**:
   ```bash
   roadmap sync rate-limit
   ```

2. **Optimize sync frequency**:
   ```bash
   roadmap config set sync.interval 60  # Sync every hour instead

   ```

3. **Use conditional requests** (enabled by default):
   ```bash
   roadmap config set sync.use_etags true
   ```

### Connection Issues

For network or API issues:

1. **Test basic connectivity**:
   ```bash
   roadmap sync test-connection --verbose
   ```

2. **Check proxy settings** (if behind corporate firewall):
   ```bash
   roadmap config set github.proxy_url "http://proxy.company.com:8080"
   ```

3. **Verify GitHub status**:
   Visit [GitHub Status Page](https://www.githubstatus.com/)

## Security Best Practices

### Token Management

1. **Use the minimum required scopes**:
   - `public_repo` for public repositories
   - Add `repo` only if you need private repository access

2. **Regularly rotate tokens**:
   - Set up a calendar reminder to rotate tokens every 6-12 months
   - Use descriptive names to track token usage

3. **Secure storage**:
   - Always use keychain storage when possible
   - Never commit tokens to version control
   - Use environment variables for CI/CD environments

### Network Security

1. **Use HTTPS only**:
   - The tool enforces HTTPS for all GitHub API calls
   - Verify your `github.api_base_url` uses HTTPS

2. **Corporate environments**:
   - Configure proxy settings if required
   - Work with your IT team for firewall rules

### Access Control

1. **Repository permissions**:
   - Ensure your token has appropriate access to the repository
   - Use organization tokens for team repositories

2. **Audit access**:
   - Regularly review who has access to your repositories
   - Monitor GitHub's access logs

## Integration Examples

### CI/CD Pipeline

Add roadmap sync to your GitHub Actions:

```yaml
name: Sync Roadmap
on:
  issues:
    types: [opened, edited, closed]
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install roadmap CLI
        run: pip install roadmap-cli
      - name: Sync with roadmap
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          roadmap config set github.owner ${{ github.repository_owner }}
          roadmap config set github.repo ${{ github.event.repository.name }}
          roadmap sync bidirectional

```text

### Team Workflows

Set up different sync configurations for team members:

```bash

# Product manager - full sync

roadmap config set sync.auto_push true
roadmap config set sync.auto_pull true
roadmap config set sync.labels_filter ""

# Developer - selective sync

roadmap config set sync.auto_push false
roadmap config set sync.auto_pull true
roadmap config set sync.labels_filter "assigned-to-me"

# QA team - status-focused sync

roadmap config set sync.auto_push true
roadmap config set sync.auto_pull false
roadmap config set sync.status_sync_only true

```text

## Getting Help

If you encounter issues not covered in this guide:

1. **Check the CLI reference**: [CLI Reference](../CLI_REFERENCE.md)
2. **View troubleshooting guide**: [Troubleshooting](../TROUBLESHOOTING.md)
3. **Report issues**: [GitHub Issues](https://github.com/shanewilkins/roadmap/issues)
4. **Join discussions**: [GitHub Discussions](https://github.com/shanewilkins/roadmap/discussions)

## Related Documentation

- [CLI Reference](../CLI_REFERENCE.md) - Complete command documentation
- [Security Guide](../SECURITY.md) - Security best practices
- [Troubleshooting](../TROUBLESHOOTING.md) - Common issues and solutions
- [Configuration](../configuration.md) - All configuration options
