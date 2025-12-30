# Quick Start: 5 Minutes to Your First Roadmap

Get up and running with Roadmap CLI in 5 minutes.

## Installation

### Using Poetry (Recommended)

```bash
poetry add roadmap
poetry run roadmap --version
```

### Using uv (Fast alternative)

```bash
uv pip install roadmap
roadmap --version
```

### Using pip

```bash
pip install roadmap
roadmap --version
```

## Initialize Your Project

```bash
# Create a new roadmap in your repo
roadmap init

# This creates:
# .roadmap/                 - Your project management data
# .roadmap/roadmap.md       - Main roadmap file
# .roadmap/config.yaml      - Configuration
```

## Your First Issue (1 minute)

```bash
# Create an issue
roadmap issue create "Implement user authentication" \
  --priority high \
  --status todo \
  --assignee your-username

# View all issues
roadmap issue list

# View your assigned issues
roadmap issue list --filter assignee=your-username

# View today's work
roadmap today
```

## Create a Milestone (1 minute)

```bash
# Create a milestone
roadmap milestone create "v1.0 Release" \
  --due-date 2025-03-31 \
  --description "First production release"

# View milestones
roadmap milestone list

# Add issue to milestone (using issue ID from create output)
roadmap issue update issue-id --milestone "v1.0 Release"
```

## Update Issue Status (1 minute)

```bash
# Mark issue as in-progress
roadmap issue update issue-id --status in-progress

# Mark issue as done
roadmap issue update issue-id --status done

# View progress
roadmap milestone list
```

## Different Output Formats (1 minute)

```bash
# Rich (colorful, interactive) - default
roadmap issue list

# Plain text (POSIX-friendly, for piping)
roadmap issue list --format plain

# JSON (machine-readable)
roadmap issue list --format json

# CSV (for spreadsheets)
roadmap issue list --format csv
```

## Commit and Track Status

Once you've created issues, **status updates happen automatically when you commit:**

```bash
# Make your changes
git add .
git commit -m "fixes issue-abc123"  # Issue auto-marks as done

# Or use the roadmap syntax
git commit -m "[closes roadmap:issue-id] Implement auth"
```

## GitHub Integration (Optional)

```bash
# Setup one-time
roadmap sync setup \
  --token "your-github-token" \
  --repo "username/repo"

# Pull existing issues from GitHub
roadmap sync pull

# Create a new issue locally and push to GitHub
roadmap issue create "New feature"
roadmap sync push --issues
```

## Next Steps

- **[Full Workflows Guide](WORKFLOWS.md)** - Team collaboration patterns
- **[Architecture Guide](ARCHITECTURE.md)** - Understanding the file structure
- **[FAQ](FAQ.md)** - Common questions
- **[Installation Guide](INSTALLATION.md)** - Advanced setup options

## Common Commands Reference

```bash
# Issues
roadmap issue list              # View all issues
roadmap issue create "Title"    # Create issue
roadmap issue update id --status done  # Update status
roadmap issue show id           # View issue details

# Milestones
roadmap milestone list          # View all milestones
roadmap milestone create "v1.0" # Create milestone

# Your daily work
roadmap today                   # Your assigned for upcoming milestone
roadmap status                  # Overall project status

# Data export
roadmap data export csv         # Export to CSV
roadmap data export json        # Export to JSON
```

## Getting Help

```bash
roadmap --help                  # Overall help
roadmap issue --help            # Issue commands help
roadmap milestone --help        # Milestone commands help
roadmap [command] --help        # Any command's help
```

That's it! You're ready to manage your project from the command line. 🎉
