# Roadmap CLI Command Reference

Complete reference for all Roadmap CLI commands with examples, options, and usage patterns.

## 📋 Command Overview

| Command Group | Commands | Description |
|---------------|----------|-------------|
| **Core** | `init`, `status` | Project initialization and status |
| **Projects** | `project create/overview` | Project-level management and analysis |
| **Issues** | `issue create/list/update/close/delete` | Issue management |
| **Comments** | `comment list/create/edit/delete` | Issue comment management |
| **Milestones** | `milestone create/list/assign/delete` | Milestone management |
| **Team** | `team members/assignments/workload` | Team collaboration and workload |
| **Sync** | `sync setup/pull/push/test/status` | GitHub synchronization |
| **Bulk** | `bulk validate/health-report/backup` | Bulk operations |

## 🚀 Core Commands

### `roadmap init`

Initialize a new roadmap in the current directory.

```bash
# Basic initialization
roadmap init

# Initialize with verbose output
roadmap init --verbose
```

**Creates:**

- `.roadmap/` directory structure
- `config.yaml` configuration file
- `issues/` and `milestones/` subdirectories
- Template files for future use

**Example Output:**

```
🗺️  Initializing new roadmap...
✅ Roadmap initialized successfully!

Created the following structure:
  .roadmap/
  ├── issues/
  ├── milestones/
  ├── templates/
  └── config.yaml

Try: roadmap issue create 'My first issue'
```

### `roadmap status`

Display current roadmap status and project overview.

```bash
# Show status overview
roadmap status

# Detailed status with verbose output
roadmap status --verbose
```

**Example Output:**

```
📊 Roadmap Status
─────────────────

Project: My Project
Issues: 15 total (3 todo, 8 in-progress, 4 done)
Milestones: 3 total (2 open, 1 closed)
Last Sync: 2024-10-10 14:30:22
GitHub: ✅ Connected (username/repository)
```

## 🏗️ Project Management

### `roadmap project create`

Create a new project with comprehensive metadata and timeline tracking.

```bash
# Basic project creation
roadmap project create "My Project"

# Full project with all options
roadmap project create "Advanced Project" \
  --description "Complex project with milestones" \
  --owner "johnsmith" \
  --priority "high" \
  --start-date "2025-01-01" \
  --target-end-date "2025-03-31" \
  --estimated-hours 120.0 \
  --milestones "Phase 1" \
  --milestones "Phase 2" \
  --milestones "Launch"

# Quick project with minimal options
roadmap project create "Bug Fix Sprint" \
  --description "Critical bug fixes for Q1" \
  --owner "devteam" \
  --priority "critical" \
  --estimated-hours 40.0
```

**Options:**

- `--description, -d TEXT`: Project description
- `--owner, -o TEXT`: Project owner/lead
- `--priority, -p [critical|high|medium|low]`: Project priority (default: medium)
- `--start-date, -s TEXT`: Start date in YYYY-MM-DD format
- `--target-end-date, -e TEXT`: Target completion date in YYYY-MM-DD format
- `--estimated-hours, -h FLOAT`: Estimated hours to complete
- `--milestones, -m TEXT`: Milestone names (can be specified multiple times)

**Creates:**

- Project file in `.roadmap/projects/` with pattern `{id}-{name}.md`
- Unique 8-character project ID
- YAML frontmatter with all metadata
- Template content with sections for objectives, timeline, and notes

**Example Output:**

```
✅ Created project:
   ID: a1b2c3d4
   Name: Advanced Project
   Priority: high
   Owner: johnsmith
   Estimated: 120.0h
   File: .roadmap/projects/a1b2c3d4-advanced-project.md
```

### `roadmap project overview`

Generate comprehensive project-level analysis and reporting.

```bash
# Rich terminal output (default)
roadmap project overview

# JSON format for automation
roadmap project overview --format json

# CSV export for spreadsheets
roadmap project overview --format csv

# Custom output directory
roadmap project overview --output ./reports

# Skip chart generation
roadmap project overview --no-include-charts
```

**Options:**

- `--output, -o PATH`: Custom output directory for analysis artifacts
- `--format, -f [rich|json|csv]`: Output format (default: rich)
- `--include-charts/--no-include-charts`: Generate visualization charts (default: true)

**Analysis Includes:**

- **Overall Statistics**: Total issues, completion rates, open bugs
- **Milestone Progression**: Progress tracking per milestone
- **Team Workload**: Issue distribution across team members
- **Issue Type Distribution**: Breakdown by bug/feature/task
- **Technical Debt Indicators**: Bug ratios and quality metrics
- **Timeline Analysis**: Project health and delivery projections

## 📝 Issue Management

### `roadmap issue create`

Create a new issue with optional metadata.

```bash
# Basic issue creation
roadmap issue create "Implement user authentication"

# Issue with full metadata
roadmap issue create "Fix login validation bug" \
  --priority high \
  --status todo \
  --milestone "v1.0" \
  --assignee "developer1" \
  --labels bug,security,backend \
  --estimate 4.5
```

**Options:**

- `--priority`: `critical`, `high`, `medium`, `low` (default: `medium`)
- `--status`: `todo`, `in-progress`, `review`, `done` (default: `todo`)
- `--milestone`: Name of existing milestone
- `--assignee`: Username or team name
- `--labels`: Comma-separated list of labels
- `--estimate`: Estimated time to complete in hours (e.g., `2.5`, `8`, `16`)
- `--git-branch`: Create a git branch for this issue (if in a git repository)
- `--branch-name`: Override the suggested branch name (e.g. `feature/1234-custom-name`)
- `--force`: Force branch creation even if the working tree has tracked modifications

**Time Estimation Examples:**

```bash
# Quick task (30 minutes)
roadmap issue create "Update documentation" --estimate 0.5


## Configuration: Branch name template

You can customize the suggested branch name format via the configuration file `.roadmap/config.yaml`.

Key: `defaults.branch_name_template`

Supported placeholders:
- `{id}` - the 8-character issue id
- `{slug}` - a slugified version of the issue title
- `{prefix}` - a prefix chosen from the issue type (e.g. `feature`, `bugfix`)

Example:

```yaml
defaults:
  branch_name_template: "feat/{id}/{slug}"
```

If the template is not set, roadmap falls back to `feature/{id}-{slug}`.

# Standard task (4 hours)
roadmap issue create "Implement login form" --estimate 4

# Large feature (2 days = 16 hours)
roadmap issue create "User dashboard redesign" --estimate 16

# Sprint epic (5 days = 40 hours)
roadmap issue create "Complete payment integration" --estimate 40
```

**Example with all options:**

```bash
roadmap issue create "Add email verification" \
  --priority medium \
  --milestone "Security Features" \
  --assignee "security-team" \
  --labels email,verification,security \
  --estimate 6.5
```

### `roadmap issue list`

List issues with optional filtering.

```bash
# List all issues
roadmap issue list

# Filter by status
roadmap issue list --status todo
roadmap issue list --status in-progress,review

# Filter by priority
roadmap issue list --priority high
roadmap issue list --priority critical,high

# Filter by milestone
roadmap issue list --milestone "v1.0"

# Filter by assignee
roadmap issue list --assignee "developer1"

# Show my issues
roadmap issue list --my-issues

# Combine filters
roadmap issue list \
  --status todo,in-progress \
  --priority high \
  --milestone "v1.0"

# Show only specific fields
roadmap issue list --fields title,status,priority
```

**Assignee Time Aggregation:**

When filtering by assignee (`--assignee` or `--my-issues`), the command displays additional time summaries:

```bash
# Example assignee output with time aggregation
roadmap issue list --assignee "backend-team"
```

```
📋 3 assigned to backend-team issues

┌──────────┬─────────────────────┬──────────┬─────────────┬──────────┬───────────┐
│ ID       │ Title               │ Priority │ Status      │ Estimate │ Milestone │
├──────────┼─────────────────────┼──────────┼─────────────┼──────────┼───────────┤
│ abc123   │ Authentication API  │ high     │ in-progress │ 2.0d     │ v1.0      │
│ def456   │ Database migration  │ high     │ done        │ 1.0d     │ v1.0      │
│ ghi789   │ Unit tests         │ medium   │ review      │ 4.0h     │ v1.0      │
└──────────┴─────────────────────┴──────────┴─────────────┴──────────┴───────────┘

⏱️  Total estimated time for backend-team: 28.0h
⏳ Remaining work (excluding done): 20.0h
📊 Workload breakdown:
   in-progress: 1 issues (16.0h)
   done: 1 issues (8.0h)
   review: 1 issues (4.0h)
```

**Output Format:**

```
📋 Issues (3 found)
┌─────────────────────────┬──────────┬──────────┬───────────┬──────────┐
│ Title                   │ Status   │ Priority │ Milestone │ Estimate │
├─────────────────────────┼──────────┼──────────┼───────────┼──────────┤
│ Implement user auth     │ todo     │ high     │ v1.0      │ 12.0h    │
│ Fix validation bug      │ review   │ critical │ v1.0      │ 2.5h     │
│ Add email verification  │ todo     │ medium   │ v1.0      │ 8.0h     │
└─────────────────────────┴──────────┴──────────┴───────────┴──────────┘
```

The output includes estimated time for each issue when available, displayed in a human-readable format (hours, minutes, or days as appropriate).

### `roadmap issue update`

Update an existing issue's metadata.

```bash
# Update issue status
roadmap issue update abc123 --status in-progress

# Update multiple fields
roadmap issue update def456 \
  --status done \
  --priority low \
  --assignee "qa-team"

# Update estimated time
roadmap issue update ghi789 --estimate 8.5

# Comprehensive update
roadmap issue update abc123 \
  --status in-progress \
  --priority high \
  --assignee "dev-team" \
  --milestone "v1.0" \
  --estimate 12.0
```

**Updatable Fields:**

- `--status`: Change issue status
- `--priority`: Change priority level
- `--milestone`: Assign to different milestone
- `--assignee`: Change assignee
- `--labels`: Replace all labels
- `--estimate`: Update estimated time in hours

**Estimate Update Examples:**

```bash
# Increase estimate after scope analysis
roadmap issue update abc123 --estimate 16

# Decrease estimate after simplification
roadmap issue update def456 --estimate 2.5

# Remove estimate (set to no estimate)
roadmap issue update ghi789 --estimate 0
```

### `roadmap issue start`

Start work on an issue by recording the actual start date and optionally creating a Git branch.

```bash
# Start work on an issue (records current time as start date)
roadmap issue start abc123

# Start with specific date
roadmap issue start abc123 --date "2025-01-15 09:00"

# Start and create a Git branch
roadmap issue start abc123 --git-branch

# Start with custom branch name
roadmap issue start abc123 --git-branch --branch-name "feat/custom-auth"

# Start with branch creation, even if working tree has changes
roadmap issue start abc123 --git-branch --force
```

**Options:**

- `--date`: Start date (YYYY-MM-DD HH:MM, defaults to now)
- `--git-branch/--no-git-branch`: Create a Git branch for this issue when starting
- `--checkout/--no-checkout`: Checkout the created branch (default: True when --git-branch is used)
- `--branch-name`: Override suggested branch name
- `--force`: Force branch creation even if working tree has tracked modifications

**Behavior:**

- Sets issue status to `in-progress`
- Records `actual_start_date` for time tracking
- Optionally creates and checks out a Git branch
- Respects `defaults.auto_branch` configuration (can be overridden with `--no-git-branch`)
- Safe by default: won't create branch if working tree has tracked changes (unless `--force` is used)
- Untracked files don't block branch creation

**Example Workflow:**

```bash
# Create an issue
roadmap issue create "Implement authentication" --estimate 8

# Start working on it with automatic branch creation
roadmap issue start abc123 --git-branch

# Output:
# 🚀 Started work on: Implement authentication
#    Started: 2025-01-15 14:30
#    Status: In Progress
# 🌿 Created Git branch: feature/abc123-implement-authentication
# ✅ Checked out branch: feature/abc123-implement-authentication
```

### `roadmap issue done`

Mark an issue as done (convenient alias for `roadmap issue update --status done`).

```bash
# Mark issue as done
roadmap issue done issue-abc123

# Mark as done with reason
roadmap issue done issue-abc123 --reason "Fixed in version 2.1"
```

### `roadmap issue update` (Enhanced)

Update issue fields including status with optional reason tracking.

```bash
# Update status with reason
roadmap issue update issue-abc123 --status done --reason "Feature complete"

# Update multiple fields
roadmap issue update issue-abc123 --status in-progress --priority high --assignee john
```

**New `--reason` Feature:**

- Appends reason to issue content for audit trail
- Especially useful when changing status
- Uses "**Completed:**" prefix for status changes to "done"
- Uses "**Update:**" prefix for other status changes

### `roadmap issue delete`

Delete an issue permanently.

```bash
# Delete an issue (requires confirmation)
roadmap issue delete issue-abc123
```

**⚠️  WARNING:** This permanently deletes the issue. Consider using `roadmap issue done` or `roadmap issue update --status done` instead.

**Safety Features:**

- Requires confirmation by default
- Shows issue details before deletion
- Suggests using `roadmap issue done` as alternative
- Creates backup before deletion
- Cannot be undone without backup restoration

**When to use deletion:**

- Duplicate issues
- Issues created by mistake
- Issues that are no longer relevant

## 💬 Comment Management

### `roadmap comment list`

List all comments for a specific issue.

```bash
# List comments for a local issue
roadmap comment list issue-abc123

# List comments for a GitHub issue number
roadmap comment list 42
```

**Features:**

- Works with both local issue IDs and GitHub issue numbers
- Shows comment author, timestamps, and content
- Displays creation and update dates for each comment
- Rich formatted output with color-coded panels

### `roadmap comment create`

Create a new comment on an issue.

```bash
# Create comment on local issue
roadmap comment create issue-abc123 "This looks good to me!"

# Create comment with markdown formatting
roadmap comment create 42 "**Status Update:** Fixed the authentication bug. 
Ready for testing in staging environment."

# Multi-line comment
roadmap comment create issue-abc123 "Great work on this feature!

Here are some suggestions:
- [ ] Add unit tests
- [ ] Update documentation
- [ ] Consider edge cases"
```

**Features:**

- Supports markdown formatting in comments
- Works with both local issue IDs and GitHub issue numbers
- Immediately posts to GitHub when issue is synced
- Returns comment ID for future reference

### `roadmap comment edit`

Update an existing comment.

```bash
# Edit a comment by its GitHub comment ID
roadmap comment edit 1234567 "Updated comment with new information"

# Edit with markdown formatting
roadmap comment edit 1234567 "**Updated:** The issue has been resolved.
Thanks to @developer for the quick fix!"
```

**Features:**

- Requires GitHub comment ID (shown when listing comments)
- Supports full markdown formatting
- Updates timestamp automatically
- Preserves comment history on GitHub

### `roadmap comment delete`

Delete a comment.

```bash
# Delete comment with confirmation prompt
roadmap comment delete 1234567

# Delete without confirmation (use with caution)
roadmap comment delete 1234567 --confirm
```

**Safety Features:**

- Requires confirmation by default
- Use `--confirm` flag to skip confirmation prompt
- Permanent deletion - cannot be undone
- Only works on comments you have permission to delete

**Prerequisites for Comment Commands:**

- Repository must be configured with `roadmap sync setup`
- Issue must be synced with GitHub (have a GitHub issue number)
- Valid GitHub authentication required
- Appropriate repository permissions for comment operations

## 🎯 Milestone Management

### `roadmap milestone create`

Create a new milestone.

```bash
# Basic milestone
roadmap milestone create "v1.0"

# Milestone with full details
roadmap milestone create "Security Audit" \
  --description "Complete security review and fixes" \
  --due-date "2024-12-31" \
  --status open
```

**Options:**

- `--description`: Detailed milestone description
- `--due-date`: Target completion date (YYYY-MM-DD)
- `--status`: `open`, `closed` (default: `open`)

### `roadmap milestone list`

List milestones with optional filtering.

```bash
# List all milestones
roadmap milestone list

# Filter by status
roadmap milestone list --status open
roadmap milestone list --status closed

# Show progress information
roadmap milestone list --with-progress
```

**Output Format:**

```
🎯 Milestones (2 found)
┌─────────────────┬──────────┬────────────┬──────────┬──────────┐
│ Name            │ Status   │ Due Date   │ Progress │ Estimate │
├─────────────────┼──────────┼────────────┼──────────┼──────────┤
│ v1.0            │ open     │ 2024-12-31 │ 60%(6/10)│ 32.5h    │
│ Security Audit  │ open     │ 2024-11-15 │ 25%(1/4) │ 16.0h    │
└─────────────────┴──────────┴────────────┴──────────┴──────────┘
```

The milestone list includes total estimated time for all issues in each milestone, calculated from individual issue estimates.

### `roadmap milestone update`

Update milestone details.

```bash
# Update milestone status
roadmap milestone update "v1.0" --status closed

# Update due date
roadmap milestone update "Security Audit" --due-date "2025-01-15"

# Update description
roadmap milestone update "v1.0" \
  --description "First stable release with core features"
```

### `roadmap milestone delete`

Delete a milestone.

```bash
# Delete milestone (issues will become unassigned)
roadmap milestone delete "Old milestone"

# Delete with confirmation
roadmap milestone delete "Important milestone" --confirm
```

**Behavior:**

- Issues assigned to deleted milestone become unassigned
- Creates backup before deletion
- Requires confirmation for safety

### `roadmap milestone delete`

Delete a milestone permanently and unassign all issues from it.

```bash
# Delete a milestone (requires confirmation)
roadmap milestone delete "Sprint 1"
```

**⚠️  WARNING:** This permanently deletes the milestone and unassigns all issues.

**What happens:**

- Permanently deletes the milestone
- Unassigns all issues from this milestone  
- Moves all assigned issues back to the backlog
- Shows affected issues before deletion

**Safety Features:**

- Requires confirmation by default
- Shows milestone details and affected issues
- Lists all issues that will be unassigned
- Cannot be undone

## 🔄 GitHub Synchronization

### `roadmap sync setup`

Configure GitHub integration with secure credential storage.

```bash
# Recommended: Secure credential manager storage
roadmap sync setup \
  --token "your-github-token" \
  --repo "username/repository"

# Repository-only setup (if token already configured)
roadmap sync setup --repo "username/repository"

# Environment variable setup (alternative)
export GITHUB_TOKEN="your-github-token"
roadmap sync setup --repo "username/repository"

# Enterprise GitHub setup
roadmap sync setup \
  --token "enterprise-token" \
  --repo "org/project" \
  --github-url "https://github.enterprise.com"

# Insecure config file storage (NOT RECOMMENDED)
roadmap sync setup \
  --token "token" \
  --repo "user/repo" \
  --insecure
```

**🔐 Credential Storage Options (Recommended Order):**

1. **System Credential Manager** (Default & Recommended)
   - macOS: Keychain Access
   - Windows: Windows Credential Manager  
   - Linux: Secret Service API
   - Tokens stored securely, encrypted at rest
   - Use: `roadmap sync setup --token YOUR_TOKEN`

2. **Environment Variable** (Good for CI/CD)
   - Set: `export GITHUB_TOKEN="your-token"`
   - Temporary, not persisted across sessions
   - Good for automation and CI/CD pipelines

3. **Config File** (NOT RECOMMENDED)
   - Stores token in plain text in `.roadmap/config.yaml`
   - Use `--insecure` flag (only for testing)
   - Security risk - tokens visible in file system

**Options:**

- `--token`: GitHub personal access token
- `--repo`: Repository in format "owner/repo"  
- `--github-url`: Custom GitHub URL for enterprise
- `--insecure`: Store token in config file (NOT RECOMMENDED)

**🔑 Creating a GitHub Personal Access Token:**

1. Go to [GitHub Settings > Tokens](https://github.com/settings/tokens)
2. Click "Generate new token" → "Generate new token (classic)"
3. Name: "Roadmap CLI Tool"
4. Select scopes:
   - ✅ `public_repo` (for public repositories)
   - ✅ `repo` (for private repositories) 
   - ✅ `write:issues` (to create/update issues)
5. Click "Generate token"
6. Copy token immediately (shown only once)

**Token Permissions Required:**

- `repo` (for private repositories)
- `public_repo` (for public repositories)
- `write:issues` (to create/update issues)

**🛡️ Security Best Practices:**

- ✅ Use credential manager storage (default)
- ✅ Use environment variables for CI/CD
- ✅ Generate tokens with minimal required scopes
- ✅ Regularly rotate tokens (30-90 days)
- ❌ Never commit tokens to version control
- ❌ Avoid `--insecure` flag in production

### `roadmap sync test`

Test GitHub connection and permissions.

```bash
# Test current configuration
roadmap sync test

# Verbose test output
roadmap sync test --verbose
```

**Example Output:**

```
🔍 Testing GitHub connection...
✅ Successfully connected to GitHub
✅ Repository access confirmed: username/repository
✅ Issue creation permissions verified
✅ Milestone access permissions verified
🎉 GitHub integration is working correctly!
```

### `roadmap sync status`

Show GitHub sync configuration and status.

```bash
# Show sync status
roadmap sync status
```

**Example Output:**

```
🔄 GitHub Sync Status
─────────────────────

Repository: username/repository
Last Sync: 2024-10-10 14:30:22
Token: ••••••••••••••••••••••••••••••••••••••••
Status: ✅ Connected and working

Local Issues: 15
GitHub Issues: 18
Local Milestones: 3
GitHub Milestones: 4

Sync needed: Yes (3 new GitHub issues)
```

### `roadmap sync pull`

Pull changes from GitHub to local roadmap.

```bash
# Standard pull (all items)
roadmap sync pull

# Pull only issues
roadmap sync pull --issues

# Pull only milestones
roadmap sync pull --milestones

# High-performance pull (recommended for 50+ items)
roadmap sync pull --high-performance

# High-performance with custom settings
roadmap sync pull --high-performance \
  --workers 16 \
  --batch-size 100

# Pull issues only with high performance
roadmap sync pull --issues --high-performance
```

**Performance Options:**

- `--high-performance`: Enable parallel processing mode
- `--workers`: Number of parallel workers (default: 8)
- `--batch-size`: Items per batch (default: 50)

**Standard Pull Output:**

```
🔄 Pulling from GitHub...
📋 Syncing milestones...
   ✅ 3 milestones synced
🎯 Syncing issues...
   ✅ 15 issues synced

✅ Successfully synced 18 items from GitHub
```

**High-Performance Pull Output:**

```
🚀 Using high-performance sync mode...
📋 High-performance milestone sync...
   Fetching milestones from GitHub...
   Processing 6 milestones...
   ✅ 6 created, 0 updated
🎯 High-performance issue sync...
   Fetching issues from GitHub...
   Caching milestones...
   Processing 100 issues...
   Batch 0: 50 issues processed
   Batch 1: 100 issues processed
   ✅ 100 created, 0 updated

📊 Performance Report:
   ⏱️  Total time: 1.30 seconds
   🚀 Throughput: 81.2 items/second
   📞 API calls: 2
   💾 Disk writes: 106
   ✅ Success rate: 98.1%
```

### `roadmap sync push`

Push local changes to GitHub.

```bash
# Standard push (all items)
roadmap sync push

# Push only issues
roadmap sync push --issues

# Push only milestones
roadmap sync push --milestones

# High-performance push
roadmap sync push --high-performance
```

**Behavior:**

- Creates new issues/milestones on GitHub
- Updates existing issues/milestones
- Preserves GitHub-specific metadata
- Maintains bidirectional sync

### `roadmap sync delete-token`

Remove stored GitHub credentials.

```bash
# Delete token
roadmap sync delete-token

# Delete with confirmation
roadmap sync delete-token --confirm
```

### 🔧 GitHub Sync Troubleshooting

**Common Issues and Solutions:**

**❌ "GitHub client not configured"**
```bash
# Check current status
roadmap sync status

# Solution: Set up repository
roadmap sync setup --repo "username/repository"
```

**❌ "No token configured"**
```bash
# Check token sources
roadmap sync status

# Solution 1: Use credential manager (recommended)
roadmap sync setup --token "your-github-token"

# Solution 2: Use environment variable
export GITHUB_TOKEN="your-github-token"
roadmap sync test

# Solution 3: Check existing credential storage
roadmap sync status  # Shows which method is active
```

**❌ "Authentication failed" / 401 Unauthorized**
```bash
# Test current token
roadmap sync test

# Solutions:
# 1. Token expired - generate new token
# 2. Wrong token scope - ensure 'public_repo' or 'repo' scope
# 3. Token revoked - check GitHub settings
# 4. Repository access - ensure token has access to specified repo
```

**❌ "Repository not found" / 404 Not Found**
```bash
# Check repository configuration
roadmap sync status

# Solution: Verify repository name format
roadmap sync setup --repo "correct-owner/correct-repo"
# Example: roadmap sync setup --repo "shanewilkins/roadmap"
```

**❌ "Rate limit exceeded"**
```bash
# GitHub API rate limits reached
# Solutions:
# 1. Wait for rate limit reset (typically 1 hour)
# 2. Use high-performance mode with smaller batches
roadmap sync pull --high-performance --batch-size 25
```

**❌ "SSL verification failed"**
```bash
# For enterprise GitHub with custom certificates
roadmap sync setup --github-url "https://github.enterprise.com"

# Temporary workaround (NOT RECOMMENDED for production)
roadmap sync setup --insecure
```

**💡 Diagnostic Commands:**
```bash
# Full diagnostic check
roadmap sync status    # Check configuration
roadmap sync test      # Test connection
roadmap status         # Check local roadmap health

# Clear all credentials and reconfigure
roadmap sync delete-token
roadmap sync setup --token "new-token" --repo "owner/repo"
```

## 🗂️ Bulk Operations

### `roadmap bulk validate`

Validate YAML files in a directory.

```bash
# Validate current roadmap
roadmap bulk validate .roadmap/

# Validate specific directory
roadmap bulk validate /path/to/roadmaps/

# Validate with detailed output
roadmap bulk validate .roadmap/ --verbose

# Validate and show only errors
roadmap bulk validate .roadmap/ --errors-only
```

**Example Output:**

```
🔍 Validating roadmap files...

✅ .roadmap/issues/auth-feature.yaml - Valid
✅ .roadmap/issues/bug-fix.yaml - Valid
❌ .roadmap/issues/broken-issue.yaml - Invalid YAML syntax
✅ .roadmap/milestones/v1.0.yaml - Valid

Validation Summary:
├── Total files: 4
├── Valid: 3
├── Invalid: 1
└── Success rate: 75%

Errors found:
├── broken-issue.yaml: Invalid YAML syntax at line 5
```

### `roadmap bulk health-report`

Generate comprehensive health report for roadmap directory.

```bash
# Generate health report
roadmap bulk health-report .roadmap/

# Save report to file
roadmap bulk health-report .roadmap/ > health-report.txt

# Detailed health report
roadmap bulk health-report .roadmap/ --detailed
```

**Example Output:**

```
📊 Roadmap Health Report
Generated: 2024-10-10 15:45:30

📁 Directory: .roadmap/
├── Total files: 25
├── Issues: 20
├── Milestones: 5
└── Templates: 2

✅ File Health:
├── Valid YAML: 24/25 (96%)
├── Schema compliant: 23/25 (92%)
├── No orphaned references: ✅
└── Consistent formatting: ✅

⚠️  Warnings:
├── 2 issues missing assignees
├── 1 milestone past due date
└── 3 issues with unknown labels

❌ Errors:
├── 1 file with invalid YAML syntax
└── 1 issue referencing non-existent milestone

🎯 Recommendations:
├── Fix YAML syntax in auth-feature.yaml
├── Update milestone "v0.9" due date
└── Assign owners to unassigned issues
```

### `roadmap bulk backup`

Create backups of roadmap directories.

```bash
# Backup current roadmap
roadmap bulk backup .roadmap/

# Backup to specific location
roadmap bulk backup .roadmap/ --destination ./backups/

# Backup with custom name
roadmap bulk backup .roadmap/ --name "pre-migration-backup"

# Backup multiple directories
roadmap bulk backup /projects/roadmap1/ /projects/roadmap2/
```

**Features:**

- Timestamps all backups automatically
- Preserves directory structure
- Compresses large backups
- Creates restoration instructions

### `roadmap bulk update-field`

Batch update fields across multiple files.

```bash
# Update priority for all issues in milestone
roadmap bulk update-field .roadmap/ \
  --field priority \
  --condition "milestone=v1.0" \
  --new-value high

# Update assignee for specific status
roadmap bulk update-field .roadmap/ \
  --field assignee \
  --condition "status=todo" \
  --old-value "former-employee" \
  --new-value "new-team-lead"

# Add labels to issues
roadmap bulk update-field .roadmap/ \
  --field labels \
  --condition "priority=critical" \
  --new-value "urgent,hotfix"

# Update milestone due dates
roadmap bulk update-field .roadmap/ \
  --field due-date \
  --condition "name=v1.0" \
  --new-value "2024-12-31"
```

**Options:**

- `--field`: Field to update (priority, status, assignee, labels, etc.)
- `--condition`: Filter condition for files to update
- `--old-value`: Current value to replace (optional)
- `--new-value`: New value to set
- `--dry-run`: Preview changes without applying them

## 🛠️ Advanced Usage

### Command Chaining

```bash
# Complete workflow automation
roadmap sync pull --high-performance && \
roadmap bulk validate .roadmap/ && \
roadmap bulk health-report .roadmap/ && \
roadmap sync push --issues
```

### Configuration Files

```bash
# Use custom configuration
roadmap --config /path/to/config.yaml issue list

# Set environment variables
export ROADMAP_GITHUB_TOKEN="your-token"
export ROADMAP_GITHUB_REPO="user/repo"
roadmap sync pull
```

### Output Formats

```bash
# JSON output for scripting
roadmap issue list --format json

# CSV export
roadmap issue list --format csv > issues.csv

# Quiet mode (minimal output)
roadmap sync pull --quiet
```

### Error Handling

```bash
# Continue on errors
roadmap bulk validate .roadmap/ --continue-on-error

# Verbose error reporting
roadmap sync pull --verbose

# Debug mode
roadmap --debug issue create "Debug test"
```

## � Team Commands

Team collaboration commands help manage workload distribution, track assignments, and analyze team productivity.

### `roadmap team workload`

Display workload summary for all team members, including estimated time calculations.

```bash
# Show team workload summary
roadmap team workload
```

**Output Format:**

```
📊 Team Workload Summary
┌─────────────────┬───────────┬─────────────┬──────────┬─────────────┐
│ Assignee        │ Total     │ In Progress │ Estimate │ Avg. Hours  │
├─────────────────┼───────────┼─────────────┼──────────┼─────────────┤
│ dev-team        │ 8         │ 3           │ 42.5h    │ 5.3h        │
│ qa-team         │ 5         │ 2           │ 18.0h    │ 3.6h        │
│ security-team   │ 3         │ 1           │ 24.0h    │ 8.0h        │
└─────────────────┴───────────┴─────────────┴──────────┴─────────────┘
```

The workload command shows:
- **Total**: Total number of assigned issues
- **In Progress**: Issues currently being worked on
- **Estimate**: Total estimated time for all assigned issues
- **Avg. Hours**: Average estimated time per issue

### `roadmap team members`

List all team members (assignees) found in the roadmap.

```bash
# List all team members
roadmap team members
```

### `roadmap team assignments`

Show detailed assignment breakdown by team member.

```bash
# Show detailed assignments
roadmap team assignments
```

## �💡 Best Practices

### Naming Conventions

```bash
# Use descriptive, actionable issue titles
roadmap issue create "Implement OAuth2 authentication for user login"
roadmap issue create "Fix memory leak in data processing pipeline"

# Use clear milestone names
roadmap milestone create "v1.0-beta" --description "Beta release candidate"
roadmap milestone create "Security-Audit-Complete" --due-date "2024-12-01"
```

### Workflow Optimization

```bash
# Daily sync routine
roadmap sync pull --high-performance
roadmap issue list --status todo,in-progress
roadmap sync push --issues

# Weekly maintenance
roadmap bulk validate .roadmap/
roadmap bulk health-report .roadmap/
roadmap bulk backup .roadmap/
```

### Team Coordination

```bash
# Use consistent labels across team
--labels "backend,api,security"
--labels "frontend,ui,accessibility"
--labels "devops,infrastructure,monitoring"

# Standardize assignee naming
--assignee "team-frontend"
--assignee "team-backend"  
--assignee "team-devops"
```

---

For more examples and advanced usage patterns, see the [User Workflow Guide](USER_WORKFLOWS.md).
