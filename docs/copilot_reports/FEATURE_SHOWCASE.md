# Roadmap CLI Feature Showcase

This document showcases the advanced features and capabilities of the Roadmap CLI tool, demonstrating real-world usage scenarios and technical capabilities.

## 🌟 Feature Overview

The Roadmap CLI has evolved from a simple task management tool into an enterprise-grade project management solution with advanced persistence, GitHub integration, and performance optimization features.

### ✨ Core Capabilities

| Feature | Description | Benefits |
|---------|-------------|----------|
| **Enhanced YAML Persistence** | Advanced validation, backup, and recovery | Data integrity and safety |
| **Data Visualization** | Interactive charts and stakeholder dashboards | Project insights and reporting |
| **Time Estimation & Workload** | Issue time tracking with smart display and team analytics | Project planning and resource allocation |
| **High-Performance Sync** | 40x faster GitHub synchronization | Efficiency at scale |
| **Bulk Operations** | Directory-wide validation and updates | Team and enterprise management |
| **File Locking** | Concurrent access protection | Multi-user safety |
| **Schema Validation** | Pydantic-based data validation | Data consistency |
| **Intelligent Caching** | API response caching with TTL | Reduced API usage |

## 🔧 Enhanced YAML Persistence

### Advanced Validation System

The enhanced persistence system provides multiple layers of validation to ensure data integrity.

## 📊 Data Visualization & Analytics

### Interactive Chart Generation

The visualization system transforms project data into actionable insights through interactive charts and comprehensive dashboards.

#### Status Distribution Analysis

```bash

# Generate interactive donut chart

$ roadmap visualize status --chart-type donut --format html
✅ Status distribution chart generated: .roadmap/artifacts/charts/status_distribution_donut_20241011_143500.html

# Bar chart for milestone analysis

$ roadmap visualize status --milestone "v1.0" --chart-type bar --format png
✅ Status chart saved: .roadmap/artifacts/charts/status_distribution_bar_20241011_143515.png

```text

**Output Example**: Visual breakdown showing:
- 40% Done (4 issues)
- 30% In Progress (3 issues)
- 20% Todo (2 issues)
- 10% Blocked (1 issue)

#### Burndown Chart Generation

```bash

# Sprint burndown analysis

$ roadmap visualize burndown --milestone "Sprint 3"
✅ Burndown chart generated: .roadmap/artifacts/charts/burndown_chart_20241011_143530.html

# Includes:

# - Ideal burndown line (linear decline)

# - Actual progress line

# - Completion projections

# - Milestone deadline markers

```text

#### Team Velocity Tracking

```bash

# Weekly velocity trends

$ roadmap visualize velocity --period W --format html
✅ Velocity chart generated: .roadmap/artifacts/charts/velocity_chart_20241011_143545.html

# Shows:

# - Issues completed per week

# - Velocity score trends

# - Performance predictions

# - Capacity planning insights

```text

#### Comprehensive Stakeholder Dashboard

```bash

# Executive-ready dashboard

$ roadmap visualize dashboard --output quarterly_report.html
✅ Stakeholder dashboard generated: quarterly_report.html

# Includes:

# - Project overview metrics

# - Status distribution (interactive donut)

# - Milestone progress bars

# - Team velocity trends

# - Workload distribution analysis

# - Professional styling and branding

```text

### Real-World Analytics Example

**Scenario**: Project manager needs to prepare weekly status report for stakeholders.

```bash

# 1. Generate comprehensive dashboard

$ roadmap visualize dashboard --milestone "Q4 Release"
✅ Dashboard: .roadmap/artifacts/dashboards/stakeholder_dashboard_20241011_143600.html

# 2. Generate milestone-specific charts

$ roadmap visualize milestones --format png
✅ Milestone chart: .roadmap/artifacts/charts/milestone_progress_20241011_143615.png

# 3. Team workload analysis

$ roadmap visualize team --format svg
✅ Team chart: .roadmap/artifacts/charts/team_workload_20241011_143630.svg

# Result: Complete visual package for stakeholder presentation

```text

**Dashboard Output Features**:
- **Summary Metrics**: Total issues, completion rate, average cycle time
- **Interactive Charts**: Click to drill down into specific data points
- **Trend Analysis**: Velocity over time with performance indicators
- **Risk Indicators**: Blocked issues, overdue items, capacity concerns
- **Team Insights**: Workload balance, individual performance, bottlenecks

#### YAML Syntax Validation

```yaml

# Example: Valid issue YAML structure

---
id: "feature-auth"
title: "Implement user authentication"
content: |
  Add OAuth2 authentication system with the following requirements:
  - Social login (Google, GitHub)
  - JWT token management
  - Role-based access control
priority: high
status: in-progress
milestone: "v1.0"
assignee: "security-team"
labels:
  - security
  - backend
  - oauth
created: 2024-10-10T10:30:00Z
updated: 2024-10-10T14:15:00Z
github_issue: 123

```text

#### Schema Validation with Pydantic

```python

# Automatic validation ensures data integrity

class Issue(BaseModel):
    id: str = Field(..., regex=r'^[a-zA-Z0-9-_]+$')
    title: str = Field(..., min_length=1, max_length=200)
    priority: Priority = Priority.MEDIUM
    status: Status = Status.TODO
    milestone: Optional[str] = None
    assignee: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)

```text

#### Error Recovery and Backup

```bash

# Automatic backup before any modification

$ roadmap issue update "auth-feature" --status done

# Creates timestamped backup

.roadmap/.backups/issues_20241010_143022/auth-feature.yaml

# Recovery from corruption

$ roadmap bulk validate .roadmap/
❌ .roadmap/issues/corrupted-file.yaml - Invalid YAML syntax

$ ls .roadmap/.backups/
issues_20241010_143022/
issues_20241010_120515/

$ cp .roadmap/.backups/issues_20241010_120515/corrupted-file.yaml \
     .roadmap/issues/corrupted-file.yaml

$ roadmap bulk validate .roadmap/
✅ All files valid

```text

### Real-World Example: Data Corruption Recovery

**Scenario**: A team member accidentally corrupts several YAML files during a bulk edit operation.

```bash

# 1. Detect the problem

$ roadmap bulk validate .roadmap/
❌ .roadmap/issues/feature-auth.yaml - Invalid YAML syntax at line 15
❌ .roadmap/issues/bug-fix-123.yaml - Missing required field 'title'
✅ .roadmap/issues/performance-opt.yaml - Valid

# 2. Check available backups

$ ls .roadmap/.backups/ -la
drwxr-xr-x  issues_20241010_143022/
drwxr-xr-x  issues_20241010_120515/
drwxr-xr-x  milestones_20241010_143022/

# 3. Restore from most recent backup

$ cp .roadmap/.backups/issues_20241010_143022/*.yaml .roadmap/issues/

# 4. Verify restoration

$ roadmap bulk validate .roadmap/
✅ Validation complete: 15/15 files valid

# 5. Generate health report

$ roadmap bulk health-report .roadmap/
📊 Roadmap Health Report
✅ All systems healthy
├── 15 issues validated
├── 5 milestones validated
└── No integrity issues found

```text

## 🚀 High-Performance Sync Engine

### Performance Comparison

The high-performance sync engine provides dramatic improvements for large-scale operations.

#### Before: Standard Sync

```bash

# Sequential processing - slow and resource intensive

$ time roadmap sync pull  # Standard mode

# Processing 100 issues sequentially:

# - 100+ individual API calls

# - Sequential file operations

# - No progress feedback

# - Takes ~52 seconds

real    0m52.134s
user    0m2.341s
sys     0m0.892s

```text

#### After: High-Performance Sync

```bash

# Parallel processing - fast and efficient

$ time roadmap sync pull --high-performance

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

real    0m1.300s  # 40x faster!

user    0m0.234s
sys     0m0.089s

```text

### Smart Caching System

The caching system minimizes API calls and improves performance through intelligent data management.

```bash

# First sync: Cache miss - fetches fresh data

$ roadmap sync pull --high-performance
📞 API calls: 2 (issues + milestones)
🎯 Cache: 0 hits, 2 misses

# Subsequent syncs within 5 minutes: Cache hit

$ roadmap sync pull --high-performance
📞 API calls: 0 (using cached data)
🎯 Cache: 2 hits, 0 misses

# Performance improvement from caching

Time saved: ~1.5 seconds per sync
API calls saved: 100% (2/2 calls cached)

```text

### Customizable Performance Parameters

```bash

# Optimize for different scenarios

# High-end development machine

$ roadmap sync pull --high-performance \
  --workers 16 \           # Utilize all CPU cores

  --batch-size 200         # Large batches for maximum throughput

# Network-constrained environment

$ roadmap sync pull --high-performance \
  --workers 4 \            # Fewer workers

  --batch-size 25          # Smaller batches

# Rate-limited API environment

$ roadmap sync pull        # Use standard sync to respect rate limits

```text

## 🗂️ Bulk Operations

### Directory-Wide Validation

Validate entire project structures with comprehensive reporting.

```bash

# Comprehensive validation of large project

$ roadmap bulk validate /enterprise-project/.roadmap/

🔍 Validating roadmap files...

Processing: /enterprise-project/.roadmap/
├── issues/ (347 files)
├── milestones/ (23 files)
└── templates/ (5 files)

Validation Results:
├── ✅ YAML syntax: 374/375 valid (99.7%)
├── ✅ Schema compliance: 372/375 valid (99.2%)
├── ✅ Reference integrity: 375/375 valid (100%)
└── ⚠️  3 warnings, 1 error found

❌ Errors:
├── issues/legacy-task.yaml: Invalid priority value 'super-high'

⚠️  Warnings:
├── issues/orphaned-task.yaml: References non-existent milestone 'v0.8'
├── milestones/overdue.yaml: Due date is 45 days past
└── issues/unassigned-critical.yaml: Critical issue without assignee

```text

### Health Reporting

Generate comprehensive health reports for project monitoring.

```bash
$ roadmap bulk health-report /enterprise-project/.roadmap/ --detailed

📊 Enterprise Project Health Report
Generated: 2024-10-10 15:45:30
Analysis Time: 2.3 seconds

📁 Project Structure:
├── Total files: 375
├── Issues: 347
├── Milestones: 23
├── Templates: 5
└── Size: 15.2 MB

📈 Content Analysis:
├── Active issues: 234 (67.4%)
├── Completed issues: 113 (32.6%)
├── Open milestones: 18 (78.3%)
├── Overdue milestones: 2 (8.7%)
└── Unassigned issues: 23 (6.6%)

🎯 Priority Distribution:
├── Critical: 12 (3.5%)
├── High: 89 (25.6%)
├── Medium: 156 (45.0%)
└── Low: 90 (25.9%)

👥 Team Distribution:
├── backend-team: 89 issues (25.6%)
├── frontend-team: 76 issues (21.9%)
├── devops-team: 34 issues (9.8%)
├── qa-team: 25 issues (7.2%)
└── Unassigned: 23 issues (6.6%)

🏷️ Label Analysis:
├── Most used: bug (45), enhancement (38), security (29)
├── Orphaned labels: deprecated-feature, old-api
└── Suggested labels: performance, accessibility

⚠️  Health Warnings:
├── 2 milestones past due date
├── 12 critical issues older than 30 days
├── 5 issues with invalid label references
└── 1 milestone with no associated issues

💡 Recommendations:
├── Review overdue milestones: v1.2, security-audit
├── Assign owners to 23 unassigned issues
├── Update 5 legacy issues with current labels
└── Consider closing empty milestone: unused-feature

```text

### Bulk Field Updates

Perform mass updates across multiple files with conditions and safety checks.

```bash

# Example: Team reorganization

# Reassign all backend issues from departing team lead

$ roadmap bulk update-field /project/.roadmap/ \
  --field assignee \
  --condition "assignee=former-backend-lead" \
  --new-value "new-backend-lead" \
  --dry-run  # Preview changes first

📝 Bulk Update Preview (DRY RUN):
Would update 23 files:
├── issues/api-redesign.yaml: assignee: former-backend-lead → new-backend-lead
├── issues/database-migration.yaml: assignee: former-backend-lead → new-backend-lead
├── issues/auth-service.yaml: assignee: former-backend-lead → new-backend-lead
└── ... 20 more files

Continue? (y/N): y

# Apply the changes

$ roadmap bulk update-field /project/.roadmap/ \
  --field assignee \
  --condition "assignee=former-backend-lead" \
  --new-value "new-backend-lead"

✅ Successfully updated 23 files
📁 Backup created: /project/.roadmap/.backups/bulk_update_20241010_154530/

```text

## 🔒 File Locking System

### Concurrent Access Protection

Prevent data corruption during simultaneous operations by multiple users or processes.

```python

# Internal implementation example

class LockedFileOperations:
    def safe_write_context(self, file_path: Path):
        """Provides safe write context with automatic locking."""
        with FileLock(file_path):
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
                yield temp.name
            # Atomic move after successful write

            shutil.move(temp.name, file_path)

```text

### Real-World Scenario: Team Collaboration

**Scenario**: Multiple team members updating issues simultaneously during a sprint planning session.

```bash

# User 1: Updating issue priority

$ roadmap issue update "auth-feature" --priority critical
🔒 Acquiring lock for auth-feature.yaml...
✅ Issue updated successfully

# User 2: Simultaneously updating same issue status

$ roadmap issue update "auth-feature" --status in-progress
🔒 Waiting for lock on auth-feature.yaml...
🔒 Lock acquired
✅ Issue updated successfully

# Result: Both updates applied correctly without data corruption

$ roadmap issue list --title "auth-feature"
┌─────────────────────────┬──────────────┬──────────┐
│ Title                   │ Status       │ Priority │
├─────────────────────────┼──────────────┼──────────┤
│ Implement auth feature  │ in-progress  │ critical │
└─────────────────────────┴──────────────┴──────────┘

```text

### Lock Management

```bash

# View active locks during debugging

$ roadmap debug locks list
🔒 Active File Locks:
├── auth-feature.yaml: Locked by PID 12345 (user: alice)
├── milestone-v2.yaml: Locked by PID 12347 (user: bob)
└── Lock timeout: 30 seconds

# Force unlock if process crashed (admin only)

$ roadmap debug locks clear --file auth-feature.yaml --force
⚠️  Force unlocking auth-feature.yaml
✅ Lock cleared

```text

## ⏱️ Time Estimation and Workload Management

### Estimated Time Tracking

The Roadmap CLI includes comprehensive time estimation features for project planning and workload management.

#### Adding Time Estimates

```bash

# Create issue with time estimate

$ roadmap issue create "Implement OAuth2 authentication" \
  --priority high \
  --assignee "security-team" \
  --estimate 12.0

# Update existing issue estimate

$ roadmap issue update "auth-feature" --estimate 8.5

# Remove estimate (set to 0)

$ roadmap issue update "simple-fix" --estimate 0

```text

#### Smart Time Display

Time estimates are displayed in human-readable formats:

```bash
$ roadmap issue list
📋 Issues (4 found)
┌─────────────────────────┬──────────┬──────────┬───────────┬──────────┐
│ Title                   │ Status   │ Priority │ Milestone │ Estimate │
├─────────────────────────┼──────────┼──────────┼───────────┼──────────┤
│ OAuth2 implementation   │ todo     │ high     │ v2.0      │ 12.0h    │
│ Quick bug fix          │ todo     │ low      │ v1.1      │ 30m      │
│ Database migration     │ review   │ critical │ v2.0      │ 2.0d     │
│ UI redesign            │ todo     │ medium   │ v2.1      │ 40h      │
└─────────────────────────┴──────────┴──────────┴───────────┴──────────┘

```text

**Display Logic:**
- `< 1 hour`: Shows in minutes (e.g., "30m")
- `1-24 hours`: Shows in hours with decimals (e.g., "12.5h")
- `≥ 24 hours`: Shows in days (e.g., "2.0d")

#### Milestone Time Aggregation

```bash
$ roadmap milestone list
🎯 Milestones (3 found)
┌─────────────────┬──────────┬────────────┬──────────┬──────────┐
│ Name            │ Status   │ Due Date   │ Progress │ Estimate │
├─────────────────┼──────────┼────────────┼──────────┼──────────┤
│ v2.0            │ open     │ 2024-12-31 │ 45%(9/20)│ 156.5h   │
│ v1.1-hotfix     │ open     │ 2024-11-15 │ 80%(4/5) │ 8.5h     │
│ v2.1-features   │ planning │ 2025-02-28 │ 0%(0/12) │ 240.0h   │
└─────────────────┴──────────┴────────────┴──────────┴──────────┘

```text

#### Team Workload Analysis

```bash
$ roadmap team workload
📊 Team Workload Summary
┌─────────────────┬───────────┬─────────────┬──────────┬─────────────┐
│ Assignee        │ Total     │ In Progress │ Estimate │ Avg. Hours  │
├─────────────────┼───────────┼─────────────┼──────────┼─────────────┤
│ security-team   │ 8         │ 3           │ 67.5h    │ 8.4h        │
│ frontend-team   │ 12        │ 5           │ 89.0h    │ 7.4h        │
│ backend-team    │ 15        │ 4           │ 124.5h   │ 8.3h        │
│ qa-team         │ 6         │ 2           │ 18.0h    │ 3.0h        │
└─────────────────┴───────────┴─────────────┴──────────┴─────────────┘

📈 Workload Distribution:
├── Most loaded: backend-team (124.5h total)
├── Most active: frontend-team (5 in progress)
├── Lightest load: qa-team (18.0h total)
└── Average issue size: 6.8 hours

```text

### Project Planning Benefits

**Sprint Planning**: Use estimates to size sprints appropriately

```bash

# Find issues totaling ~40 hours for 1-week sprint

$ roadmap issue list --status todo | grep -E "(2\.0h|4\.0h|8\.0h)"

```text

**Resource Allocation**: Balance workload across team members

```bash

# Check team capacity before assignment

$ roadmap team workload
$ roadmap issue update "new-feature" --assignee "qa-team"  # Lightest load

```text

**Timeline Estimation**: Calculate milestone completion dates

```bash

# Milestone v2.0 has 156.5h remaining

# With 3 developers × 40h/week = 120h/week capacity

# Estimated completion: ~1.3 weeks

```text

## 📊 Schema Validation and Data Integrity

### Pydantic Model Validation

Ensure data consistency through comprehensive schema validation.

```python

# Example validation in action

from roadmap.models import Issue, Priority, Status

# Valid issue creation

issue = Issue(
    id="secure-login",
    title="Implement secure login system",
    priority=Priority.HIGH,
    status=Status.TODO,
    milestone="security-phase",
    assignee="security-team"
)

# ✅ Validation passes

# Invalid data detection

try:
    invalid_issue = Issue(
        id="invalid id with spaces",  # ❌ Invalid characters

        title="",                     # ❌ Empty title

        priority="super-high",        # ❌ Invalid enum value

        status=Status.TODO
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
    # Provides detailed error messages with field-level specificity

```text

### Data Migration and Schema Evolution

```bash

# Future feature: Automatic schema migration

$ roadmap migrate --from v1.0 --to v2.0 .roadmap/

📋 Schema Migration Plan:
├── Add new field: estimated_hours (default: null)
├── Rename field: labels → tags
├── Update enum: priority values (add 'urgent')
└── Remove deprecated field: legacy_id

🔄 Migrating 347 files...
├── ✅ issues/auth-feature.yaml: v1.0 → v2.0
├── ✅ issues/bug-fix.yaml: v1.0 → v2.0
└── ... 345 more files

✅ Migration complete: 347/347 files updated
📁 Backup created: .roadmap/.backups/migration_v1_to_v2_20241010/

```text

## 🎛️ Advanced Configuration

### Environment-Based Configuration

```yaml

# .roadmap/config.yaml

project:
  name: "Enterprise Application"
  version: "2.0"

github:
  repository: "${ROADMAP_GITHUB_REPO}"
  token: "${ROADMAP_GITHUB_TOKEN}"
  api_url: "${GITHUB_API_URL:-https://api.github.com}"

performance:
  sync:
    workers: 16
    batch_size: 100
    cache_ttl: 300

validation:
  strict_mode: true
  auto_backup: true
  max_file_size: "10MB"

teams:
  backend:
    members: ["alice", "bob", "charlie"]
    default_labels: ["backend", "api"]
  frontend:
    members: ["diana", "eve", "frank"]
    default_labels: ["frontend", "ui"]

```text

### Custom Field Definitions

```yaml

# Future feature: Custom fields

custom_fields:
  estimated_hours:
    type: integer
    min: 0
    max: 999
    default: null

  complexity:
    type: enum
    values: ["simple", "moderate", "complex", "epic"]
    default: "moderate"

  business_value:
    type: enum
    values: ["low", "medium", "high", "critical"]
    required: true

```text

## 🔍 Monitoring and Analytics

### Performance Metrics

Track and optimize system performance with detailed metrics.

```bash

# Performance monitoring during large sync

$ roadmap sync pull --high-performance --monitor

🚀 High-Performance Sync Monitor
┌─────────────────┬─────────┬─────────────┬──────────┐
│ Phase           │ Time    │ Throughput  │ API Calls│
├─────────────────┼─────────┼─────────────┼──────────┤
│ Fetch Issues    │ 0.8s    │ 125.0/sec   │ 1        │
│ Fetch Milestones│ 0.3s    │ 20.0/sec    │ 1        │
│ Process Batch 1 │ 0.2s    │ 250.0/sec   │ 0        │
│ Process Batch 2 │ 0.2s    │ 250.0/sec   │ 0        │
│ Write Files     │ 0.1s    │ 1000.0/sec  │ 0        │
└─────────────────┴─────────┴─────────────┴──────────┘

📊 Final Metrics:
├── Total time: 1.6 seconds
├── Items processed: 106
├── Overall throughput: 66.3 items/second
├── API calls: 2
├── Cache hit rate: 95%
└── Success rate: 100%

```text

### Usage Analytics

```bash

# Generate usage report

$ roadmap analytics report --period "last-30-days"

📈 Roadmap Usage Analytics (30 days)
─────────────────────────────────────

👤 User Activity:
├── alice: 156 operations (45.2%)
├── bob: 89 operations (25.8%)
├── charlie: 67 operations (19.4%)
└── diana: 33 operations (9.6%)

⚡ Command Usage:
├── issue create: 89 times
├── sync pull: 67 times
├── issue update: 45 times
├── milestone create: 23 times
└── bulk validate: 15 times

🚀 Performance Trends:
├── Avg sync time: 2.3s (↓ 40% from last month)
├── High-perf adoption: 78% of syncs
├── Bulk operations: 23% increase
└── API efficiency: 95% cache hit rate

💡 Recommendations:
├── Consider increasing default batch size
├── Schedule weekly bulk validation
└── Enable auto-sync for alice and bob

```text

## 🛡️ Security and Best Practices

### Secure Credential Management

```bash

# Secure token storage

$ roadmap sync setup --token "$(cat ~/.github-token)" --repo "org/project"
✅ Token encrypted and stored securely
🔐 Using system keychain for storage

# Token rotation

$ roadmap sync delete-token
$ roadmap sync setup --token "new-token" --repo "org/project"
✅ Token updated successfully

# Audit token usage

$ roadmap sync audit
🔍 Token Usage Audit:
├── Created: 2024-09-15 10:30:00
├── Last used: 2024-10-10 15:45:22
├── API calls this month: 1,247
├── Rate limit remaining: 4,753/5,000
└── Permissions: repo, write:issues

```text

### Data Validation Best Practices

```bash

# Pre-commit validation

$ cat .git/hooks/pre-commit
#!/bin/bash
roadmap bulk validate .roadmap/
if [ $? -ne 0 ]; then
    echo "❌ Roadmap validation failed!"
    echo "Run 'roadmap bulk validate .roadmap/' to see details"
    exit 1
fi

# Continuous integration

$ cat .github/workflows/roadmap-validation.yml
name: Roadmap Validation
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install Roadmap CLI
        run: pip install roadmap-cli
      - name: Validate roadmap files
        run: roadmap bulk validate .roadmap/
      - name: Generate health report
        run: roadmap bulk health-report .roadmap/

```text

---

This feature showcase demonstrates the enterprise-grade capabilities of the Roadmap CLI, from basic project management to advanced performance optimization and team collaboration features.
