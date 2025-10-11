# Quick Start Guide

Get up and running with Roadmap CLI in just a few minutes.

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install roadmap-cli
```

### Option 2: Install from Source

```bash
git clone https://github.com/roadmap-cli/roadmap.git
cd roadmap
poetry install
```

## Basic Setup

### 1. Initialize Your First Roadmap

```bash
# Create a new roadmap in the current directory
roadmap init

# Or create with a custom name
roadmap init --name my-project-roadmap
```

This creates:
- Project directory structure
- Configuration files  
- Templates for issues and milestones
- Artifacts directory for exports
- Updated .gitignore to exclude generated files

### 2. Create Your First Issue

```bash
roadmap issue create "Setup development environment" \
  --priority high \
  --type feature \
  --estimate 4
```

### 3. Create a Milestone

```bash
roadmap milestone create "v1.0 Beta" \
  --due-date 2025-12-31 \
  --description "First beta release with core features"
```

### 4. Assign Issue to Milestone

```bash
# Find your issue ID
roadmap issue list

# Assign to milestone
roadmap issue update ISSUE_ID --milestone "v1.0 Beta"
```

## Essential Commands

### Issue Management

```bash
# List all issues
roadmap issue list

# Filter issues
roadmap issue list --status in-progress --priority high

# Update issue status
roadmap issue update ISSUE_ID --status in-progress

# Complete an issue
roadmap issue complete ISSUE_ID
```

### Project Status

```bash
# View overall project status
roadmap status

# View your personal dashboard
roadmap dashboard

# View team workload
roadmap team workload
```

### Data Export

```bash
# Export issues to Excel
roadmap export issues --format excel

# Export with filtering
roadmap export issues --format csv --status done --milestone "v1.0"

# Generate analytics report
roadmap export analytics --format excel
```

## GitHub Integration (Optional)

### 1. Setup GitHub Sync

```bash
roadmap sync setup
```

This will:
- Prompt for your GitHub token
- Configure repository connection
- Set up synchronization preferences

### 2. Sync with GitHub

```bash
# Pull issues from GitHub
roadmap sync pull

# Push local changes to GitHub
roadmap sync push

# Two-way sync
roadmap sync
```

## Team Collaboration

### Adding Team Members

```bash
# Assign issues to team members
roadmap issue update ISSUE_ID --assignee alice

# Hand off work between team members
roadmap handoff ISSUE_ID bob --context "Needs frontend integration"

# View team activity
roadmap activity
```

### Workload Management

```bash
# View team workload distribution
roadmap team workload

# Forecast capacity
roadmap capacity-forecast

# Analyze team performance
roadmap analytics team
```

## Advanced Features

### Bulk Operations

```bash
# Validate all issues
roadmap bulk validate

# Generate health report
roadmap bulk health-report

# Backup entire roadmap
roadmap bulk backup
```

### Analytics and Reporting

```bash
# Enhanced analytics dashboard
roadmap analytics enhanced

# Velocity analysis
roadmap analytics velocity

# Quality metrics
roadmap analytics quality
```

### Git Integration

```bash
# Create Git branch for issue
roadmap git-branch ISSUE_ID

# Link issue to current branch
roadmap git-link ISSUE_ID

# Sync issue status from Git activity
roadmap git-sync
```

## File Structure

After initialization, your project will have:

```
your-project/
├── .roadmap/                    # Default roadmap directory
│   ├── artifacts/              # Export files (auto-excluded from git)
│   ├── issues/                 # Individual issue files
│   ├── milestones/            # Milestone definitions
│   ├── templates/             # Issue and milestone templates
│   └── config.yaml            # Project configuration
├── .gitignore                 # Auto-updated to exclude artifacts/
└── (your project files)
```

## Configuration

The `config.yaml` file contains project settings:

```yaml
project_name: "My Project"
github_repo: "username/repo"
default_assignee: "your-username"
sync_enabled: true
backup_enabled: true
```

## Getting Help

### Built-in Help

```bash
# General help
roadmap --help

# Command-specific help
roadmap issue --help
roadmap export issues --help
```

### Common Issues

**Problem**: `roadmap: command not found`
**Solution**: Ensure the package is installed and your PATH includes the installation directory.

**Problem**: GitHub sync fails
**Solution**: Check your GitHub token permissions and repository access.

**Problem**: Export fails
**Solution**: Ensure you have write permissions to the artifacts directory.

## Next Steps

1. **Explore the [User Guide](user-guide/concepts.md)** for detailed feature explanations
2. **Check the [CLI Reference](CLI_REFERENCE.md)** for complete command documentation  
3. **Read [Team Collaboration](user-guide/team.md)** for multi-user workflows
4. **Review [Performance Optimization](PERFORMANCE_OPTIMIZATION.md)** for large projects

## Example Workflow

Here's a complete example workflow:

```bash
# 1. Initialize project
roadmap init --name my-app-roadmap

# 2. Create milestone
roadmap milestone create "MVP Release" --due-date 2025-06-01

# 3. Create issues
roadmap issue create "User authentication" --priority critical --type feature --milestone "MVP Release"
roadmap issue create "Database schema" --priority high --type feature --milestone "MVP Release"
roadmap issue create "API endpoints" --priority medium --type feature --milestone "MVP Release"

# 4. Start working
roadmap issue start ISSUE_ID

# 5. Track progress
roadmap status
roadmap dashboard

# 6. Export progress report
roadmap export analytics --format excel

# 7. Share with team
# The excel file is in .roadmap/artifacts/ ready to share
```

You're now ready to start managing your project roadmap effectively! 🚀