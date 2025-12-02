# Roadmap CLI User Workflow Guide

This guide provides step-by-step workflows for using the Roadmap CLI tool effectively, from initial setup to advanced operations.

## 🚀 Getting Started

### Initial Setup

#### 1. Installation and Project Initialization

```bash

# Install the tool

pip install roadmap-cli

# Navigate to your project directory

cd /path/to/your/project

# Initialize a new roadmap

roadmap init

```text

**What happens:**
- Creates `.roadmap/` directory structure
- Sets up `config.yaml` with default settings
- Creates empty `issues/` and `milestones/` directories
- Generates template files for future use

#### 2. Basic Configuration Check

```bash

# Verify installation

roadmap --help

# Check project status

roadmap status

```text

### Your First Issue and Milestone

#### 3. Create Your First Milestone

```bash

# Create a milestone for your first release

roadmap milestone create "v1.0" \
  --description "First stable release with core features" \
  --due-date "2024-12-31" \
  --status open

```text

#### 4. Create Your First Issue

```bash

# Create a high-priority issue

roadmap issue create "Implement user authentication" \
  --priority high \
  --status todo \
  --milestone "v1.0" \
  --assignee "your-username" \
  --labels security,backend

```text

#### 5. View Your Progress

```bash

# List all issues

roadmap issue list

# List all milestones

roadmap milestone list

# Get a complete project status

roadmap status

```text

## 🔧 Workflow Overview

This guide covers five main workflow patterns for different use cases:

- **Workflow A: Solo Developer** - Individual project management and personal productivity
- **Workflow B: Team Development** - Collaborative development with team coordination
- **Workflow C: Large Project Management** - Enterprise-scale projects with hundreds of issues
- **Workflow D: Open Source Project** - Community-driven development with contributor management
- **Workflow E: Time Estimation and Project Planning** - Sprint planning with time tracking and workload management

Choose the workflow that best matches your project scale and team structure.

## 🔧 Daily Development Workflow

### Workflow A: Solo Developer

This workflow is perfect for individual developers managing their own projects.

#### Morning Routine

```bash

# 1. Check current status

roadmap issue list --status todo,in-progress

# 2. Start working on an issue

roadmap issue update "Implement user authentication" --status in-progress

# 3. Create new issues as you discover them

roadmap issue create "Add input validation to login form" \
  --priority medium \
  --milestone "v1.0" \
  --labels frontend,validation

```text

#### During Development

```bash

# Add specific implementation tasks

roadmap issue create "Create user model with bcrypt password hashing" \
  --priority high \
  --milestone "v1.0" \
  --labels backend,database

# Update progress

roadmap issue update "Create user model with bcrypt password hashing" \
  --status in-progress

```text

#### End of Day

```bash

# Mark completed work

roadmap issue update "Create user model with bcrypt password hashing" \
  --status done

# Create tomorrow's tasks

roadmap issue create "Write unit tests for user authentication" \
  --priority high \
  --milestone "v1.0" \
  --assignee "your-username"

# Review progress

roadmap milestone list
roadmap issue list --status done  # See what you accomplished

```text

### Workflow B: Team Development

This workflow supports teams collaborating on shared projects.

#### Team Lead Setup

```bash

# 1. Initialize project roadmap

roadmap init

# 2. Setup GitHub integration for team sync

roadmap sync setup \
  --token "your-github-token" \
  --repo "team-org/project-name"

# 3. Import existing GitHub issues

roadmap sync pull --high-performance

# 4. Create team milestones

roadmap milestone create "Sprint 1" \
  --description "First development sprint" \
  --due-date "2024-11-15"

roadmap milestone create "MVP" \
  --description "Minimum viable product" \
  --due-date "2024-12-01"

```text

#### Daily Team Sync

```bash

# Morning: Get latest updates from team

roadmap sync pull --high-performance

# Check what team members are working on

roadmap issue list --status in-progress

# Assign new work

roadmap issue create "Implement payment processing" \
  --priority high \
  --milestone "MVP" \
  --assignee "team-member-2" \
  --labels backend,payments

# Push your updates to team

roadmap sync push --issues --milestones

```text

#### Sprint Planning

```bash

# Create sprint milestone

roadmap milestone create "Sprint 2" \
  --description "Second development sprint" \
  --due-date "2024-11-30"

# Create issues with time estimates for sprint planning

roadmap issue create "Implement payment processing" \
  --priority high \
  --milestone "Sprint 2" \
  --assignee "backend-team" \
  --estimate 16.0

roadmap issue create "Add user dashboard" \
  --priority medium \
  --milestone "Sprint 2" \
  --assignee "frontend-team" \
  --estimate 12.0

roadmap issue create "Create admin panel" \
  --priority low \
  --milestone "Sprint 2" \
  --assignee "frontend-team" \
  --estimate 8.0

# Review sprint workload and time estimates

roadmap milestone list  # Shows total estimated time

roadmap team workload   # Shows distribution across team members

# Check if sprint is feasibly sized (e.g., 36h total for 40h sprint capacity)

roadmap issue list --milestone "Sprint 2"

# Adjust estimates based on team discussion

roadmap issue update "payment-processing" --estimate 20.0  # Increase after complexity analysis

# Sync with GitHub for team visibility

roadmap sync push --issues --milestones

```text

## 🌿 Workflow F: Git Integration Workflow

**Git-Integrated Development** - Seamless integration between Git version control and roadmap project management.

### Setup

```bash

# Initialize roadmap in Git repository

cd /path/to/your/git/project
roadmap init

# Your Git user will be auto-detected for issue assignments

git config user.name "John Developer"
git config user.email "john@example.com"

```text

### Daily Git-Integrated Development

#### 1. Create Issue with Automatic Git Branch

```bash

# Create an issue and Git branch in one command

roadmap issue create "Implement OAuth authentication" \
  --type feature \
  --priority high \
  --git-branch \
  --estimate 16

# This automatically:

# - Creates the issue assigned to your Git user

# - Creates branch: feature/abc12345-implement-oauth-authentication

# - Checks out the new branch

# - Links the issue to the branch

```text

#### 2. Work with Progress Tracking via Commits

```bash

# Work on your feature and track progress through commit messages

git commit -m "feat: add OAuth config setup [roadmap:abc12345] [progress:25%]"

git commit -m "feat: implement OAuth provider integration [roadmap:abc12345] [progress:60%]"

git commit -m "feat: add OAuth callback handling [roadmap:abc12345] [progress:85%]"

# Complete the feature

git commit -m "feat: finalize OAuth integration [closes roadmap:abc12345]"

```text

#### 3. Sync Issue Status from Git Activity

```bash

# Update issue status based on commit messages

roadmap git-sync abc12345

# Output shows automatic updates:

# 🔄 Synced issue from Git activity: Implement OAuth authentication

#    📊 Status: todo → done

#    📈 Progress: 0% → 100%

```text

#### 4. Monitor Git Integration Status

```bash

# Check Git repository status with roadmap integration

roadmap git-status

# Example output:

# 🔍 Git Repository Status

# 🌿 Current branch: feature/abc12345-implement-oauth-authentication

# 🔗 Linked issue:

#    📋 Implement OAuth authentication

#    🆔 abc12345

#    📊 Status: done

#    ⚡ Priority: high

#

# 🌿 Branch-Issue Links:

# 👉 feature/abc12345-implement-oauth-authentication → Implement OAuth authentication

#

# 📝 Recent Roadmap Commits:

#    a1b2c3d4 feat: finalize OAuth integration [closes road...

#      🔗 References: abc12345

```text

#### 5. Link Existing Branches to Issues

```bash

# If you have an existing branch that should be linked to an issue

git checkout feature/user-dashboard
roadmap git-link def67890  # Links current branch to issue def67890

# 🔗 Linked issue to branch: feature/user-dashboard

# 📋 Issue: Add user dashboard

```text

#### 6. View Commit History for Issues

```bash

# See all commits that reference a specific issue

roadmap git-commits abc12345

# Example output:

# 📝 Commits for: Implement OAuth authentication

# 🆔 Issue ID: abc12345

#

# 🔸 a1b2c3d4 John Developer

#    📅 2024-10-11 14:30

#    💬 feat: finalize OAuth integration [closes roadmap:abc12345]

#    📊 Progress: 100%

#    📁 3 files changed

#    ➕ 45 ➖ 12

#

# 🔸 b2c3d4e5 John Developer

#    📅 2024-10-11 12:15

#    💬 feat: add OAuth callback handling [roadmap:abc12345] [progress:85%]

#    📊 Progress: 85%

#    📁 2 files changed

#    ➕ 23 ➖ 5

```text

### Advanced Git Integration Patterns

#### Team Branch Workflow

```bash

# Team member creates issue and starts work

roadmap issue create "Add user profile management" \
  --type feature \
  --assignee "alice" \
  --git-branch

# Alice works on the feature

git commit -m "feat: add profile model [roadmap:def67890] [progress:30%]"

# Handoff to another team member

roadmap handoff def67890 "bob" \
  --notes "Profile model is complete, need to add validation and UI"

# Bob continues on the same branch

git commit -m "feat: add profile validation [roadmap:def67890] [progress:70%]"

# Complete and track

git commit -m "feat: complete profile management [closes roadmap:def67890]"
roadmap git-sync def67890  # Auto-updates issue to done

```text

#### Multi-Issue Feature Branch

```bash

# Create a feature branch that spans multiple issues

git checkout -b feature/user-management-system

# Link multiple related issues

roadmap git-link abc12345  # User authentication

roadmap git-link def67890  # User profiles

roadmap git-link ghi13579  # User permissions

# Work with specific issue references in commits

git commit -m "feat: implement user auth [roadmap:abc12345] [progress:100%]"
git commit -m "feat: add user profiles [roadmap:def67890] [progress:100%]"
git commit -m "feat: implement permissions [roadmap:ghi13579] [progress:100%]"

# Sync all related issues

roadmap git-sync abc12345
roadmap git-sync def67890
roadmap git-sync ghi13579

```text

#### Commit Message Patterns

The Git integration recognizes these commit message patterns:

```bash

# Progress tracking

git commit -m "feat: implement login [roadmap:abc12345] [progress:50%]"
git commit -m "fix: resolve auth bug roadmap:abc12345 progress:75%"

# Issue completion

git commit -m "feat: complete OAuth [closes roadmap:abc12345]"
git commit -m "fix: final auth fix [fixes roadmap:abc12345]"

# Multiple issue references

git commit -m "refactor: shared auth utils [roadmap:abc12345] [roadmap:def67890]"

```text

### Benefits of Git Integration Workflow

- **Seamless Context**: Never lose track of what issue you're working on
- **Automatic Progress**: Issue progress updates automatically from commit messages
- **Branch Organization**: Clean branch names linked to specific issues
- **Team Visibility**: Clear understanding of who's working on what branch
- **Historical Tracking**: Complete audit trail of work through Git commits
- **Reduced Friction**: Git and project management work together naturally

## 🚀 Advanced Workflows

### Workflow C: Large Project Management

For managing large projects with hundreds of issues and complex requirements.

#### Initial Large Project Setup

```bash

# 1. Initialize and import from active repository

roadmap init
roadmap sync setup --token "enterprise-token" --repo "org/large-project"

# 2. High-performance import of existing data

roadmap sync pull --high-performance \
  --workers 16 \
  --batch-size 100

# 3. Validate imported data

roadmap bulk validate .roadmap/

# 4. Generate health report

roadmap bulk health-report .roadmap/ > project-health.txt

```text

#### Bulk Operations for Project Management

```bash

# Backup before major changes

roadmap bulk backup .roadmap/

# Update all issues in a milestone

roadmap bulk update-field .roadmap/ \
  --field priority \
  --condition "milestone=v1.0,status=todo" \
  --old-value medium \
  --new-value high

# Reassign issues from departing team member

roadmap bulk update-field .roadmap/ \
  --field assignee \
  --old-value "former-employee" \
  --new-value "new-team-lead"

# Mass update labels

roadmap bulk update-field .roadmap/ \
  --field labels \
  --condition "assignee=backend-team" \
  --new-value "backend,api,database"

```text

#### Performance Monitoring

```bash

# Monitor sync performance

roadmap sync pull --high-performance  # Check performance metrics

# Optimize for your infrastructure

roadmap sync pull --high-performance \
  --workers 24 \        # Match your CPU cores

  --batch-size 200      # Larger batches for enterprise

# Regular health checks

roadmap bulk health-report .roadmap/

```text

### Workflow D: Open Source Project

Managing community contributions and public roadmaps.

#### Public Roadmap Setup

```bash

# Setup with public repository

roadmap init
roadmap sync setup \
  --token "public-repo-token" \
  --repo "username/opensource-project"

# Import community issues

roadmap sync pull --high-performance

# Create public milestones

roadmap milestone create "Community Features" \
  --description "Features requested by the community" \
  --due-date "2025-03-01"

roadmap milestone create "Performance Improvements" \
  --description "Optimization and performance work" \
  --due-date "2025-02-01"

```text

#### Community Issue Management

```bash

# Import new community issues daily

roadmap sync pull --high-performance

# Triage and categorize

roadmap issue update "Add dark mode support" \
  --priority medium \
  --milestone "Community Features" \
  --labels enhancement,ui

# Create meta-issues for complex features

roadmap issue create "Redesign user interface (Epic)" \
  --priority high \
  --milestone "Community Features" \
  --labels epic,ui,design \
  --assignee "ui-team-lead"

# Break down epics into tasks

roadmap issue create "Create wireframes for new UI" \
  --priority high \
  --milestone "Community Features" \
  --labels ui,design

# Sync back to GitHub for community visibility

roadmap sync push --issues --milestones

```text

### Workflow E: Time Estimation and Project Planning

For teams focusing on accurate time tracking, sprint planning, and workload management.

#### Initial Project Estimation

```bash

# Create project with estimated milestones

roadmap milestone create "Phase 1: Foundation" \
  --description "Core infrastructure and authentication" \
  --due-date "2024-12-15"

roadmap milestone create "Phase 2: Features" \
  --description "Main application features" \
  --due-date "2025-02-28"

# Create issues with time estimates

roadmap issue create "Set up CI/CD pipeline" \
  --priority high \
  --milestone "Phase 1: Foundation" \
  --assignee "devops-team" \
  --estimate 16.0  # 2 days

roadmap issue create "Implement user authentication" \
  --priority high \
  --milestone "Phase 1: Foundation" \
  --assignee "backend-team" \
  --estimate 24.0  # 3 days

roadmap issue create "Design user dashboard" \
  --priority medium \
  --milestone "Phase 2: Features" \
  --assignee "frontend-team" \
  --estimate 12.0  # 1.5 days

```text

#### Sprint Planning with Time Estimates

```bash

# Review available team capacity

roadmap team workload

# Create new sprint based on capacity

roadmap milestone create "Sprint 3" \
  --description "Development sprint 3" \
  --due-date "2024-11-29"

# Select issues that fit sprint capacity (e.g., 80 hours total)

roadmap issue list --status todo | head -10  # Review available work

# Assign issues to sprint with time validation

roadmap issue update "auth-feature" \
  --milestone "Sprint 3" \
  --estimate 20.0

roadmap issue update "dashboard-ui" \
  --milestone "Sprint 3" \
  --estimate 16.0

roadmap issue update "api-endpoints" \
  --milestone "Sprint 3" \
  --estimate 24.0

# Check sprint total time

roadmap milestone list  # Shows Sprint 3: 60h total

# Balance workload across team

roadmap team workload  # Check distribution

roadmap issue update "api-endpoints" --assignee "backend-team-2"  # Rebalance if needed

```text

#### Progress Tracking and Re-estimation

```bash

# Daily progress check

roadmap issue list --status in-progress
roadmap team workload

# Update estimates based on actual progress

roadmap issue update "complex-feature" --estimate 32.0  # Increase from 24h

roadmap issue update "simple-fix" --estimate 2.0       # Decrease from 8h

# Weekly sprint review

roadmap milestone list  # Check sprint progress and time remaining

roadmap issue list --milestone "Sprint 3" --status done  # Review completed work

# Adjust next sprint based on velocity

# If team completed 60h in this sprint, plan similar capacity for next

roadmap milestone create "Sprint 4" --due-date "2024-12-13"

# Select ~60h of work for Sprint 4 based on historical velocity

```text

#### Project Timeline Estimation

```bash

# Calculate project completion estimates

roadmap milestone list  # Review all milestone time totals

# Phase 1: 120h total, 3 developers × 32h/week = 96h/week capacity

# Estimated completion: ~1.25 weeks from start

# Monitor progress and adjust timeline

roadmap team workload  # Track actual vs estimated progress

```text

## 🛠️ Advanced Operations

### Backup and Recovery Workflows

#### Regular Backup Routine

```bash

# Daily automated backup

roadmap bulk backup .roadmap/ --destination ./backups/$(date +%Y%m%d)

# Validate backup integrity

roadmap bulk validate ./backups/$(date +%Y%m%d)/.roadmap/

# Weekly comprehensive health check

roadmap bulk health-report .roadmap/ > weekly-health-$(date +%Y%m%d).txt

```text

#### Recovery from Corruption

```bash

# Detect issues

roadmap bulk validate .roadmap/  # Shows validation errors

# Check available backups

ls .roadmap/.backups/

# Restore specific file

cp .roadmap/.backups/issues_20241010_143022/auth-issue.yaml \
   .roadmap/issues/auth-issue.yaml

# Validate restoration

roadmap bulk validate .roadmap/

```text

### Migration and Format Updates

```bash

# Backup before migration

roadmap bulk backup .roadmap/

# Migrate schema (when migration tools are implemented)

roadmap migrate --from v1.0 --to v2.0 .roadmap/

# Validate migration

roadmap bulk validate .roadmap/
roadmap bulk health-report .roadmap/

```text

### Performance Optimization Workflows

#### Benchmarking Sync Performance

```bash

# Test current performance

time roadmap sync pull --high-performance

# Optimize for your system

roadmap sync pull --high-performance \
  --workers $(nproc) \           # Use all CPU cores

  --batch-size 50               # Optimal batch size

# Monitor API usage

roadmap sync pull --high-performance  # Check API calls in performance report

```text

#### Optimizing for Different Scenarios

```bash

# For slow networks (reduce batch size)

roadmap sync pull --high-performance --batch-size 10 --workers 4

# For fast networks (increase batch size)

roadmap sync pull --high-performance --batch-size 200 --workers 16

# For rate-limited APIs (conservative approach)

roadmap sync pull  # Use standard sync to respect rate limits

```text

## 🚨 Troubleshooting Workflows

### Issue Resolution Process

#### 1. Identify Problems

```bash

# Check for validation errors

roadmap bulk validate .roadmap/

# Generate comprehensive health report

roadmap bulk health-report .roadmap/

# Test GitHub connectivity

roadmap sync test

```text

#### 2. Common Problem Solutions

**YAML Syntax Errors:**

```bash

# Find problematic files

roadmap bulk validate .roadmap/ | grep ERROR

# Restore from backup

ls .roadmap/.backups/
cp .roadmap/.backups/issues_latest/problematic-file.yaml .roadmap/issues/

# Verify fix

roadmap bulk validate .roadmap/

```text

**GitHub Sync Issues:**

```bash

# Check configuration

roadmap sync status

# Test connection

roadmap sync test

# Reset if needed

roadmap sync delete-token
roadmap sync setup --token "new-token" --repo "user/repo"

```text

**Performance Problems:**

```bash

# Use high-performance mode

roadmap sync pull --high-performance

# Reduce resource usage if needed

roadmap sync pull --high-performance --workers 4 --batch-size 25

# Monitor and optimize

roadmap sync pull --high-performance  # Review performance metrics

```text

#### 3. Recovery Procedures

```bash

# Complete project recovery

roadmap bulk backup .roadmap/ --destination ./recovery-backup
roadmap init  # Start fresh

roadmap sync setup --token "token" --repo "user/repo"
roadmap sync pull --high-performance  # Restore from GitHub

# Validate recovery

roadmap bulk validate .roadmap/
roadmap bulk health-report .roadmap/

```text

## 📊 Monitoring and Maintenance

### Regular Maintenance Schedule

#### Daily

```bash

# Quick status check

roadmap status

# Sync with team/GitHub

roadmap sync pull --high-performance

```text

#### Weekly

```bash

# Comprehensive health check

roadmap bulk health-report .roadmap/

# Backup project data

roadmap bulk backup .roadmap/

# Clean up completed issues (if desired)

roadmap issue list --status done | grep "old-milestone"

```text

#### Monthly

```bash

# Archive old milestones

roadmap milestone update "old-milestone" --status closed

# Review and update project structure

roadmap bulk health-report .roadmap/

# Performance review

roadmap sync pull --high-performance  # Check metrics

```text

## 💡 Best Practices

### Naming Conventions

```bash

# Issues: Use descriptive, action-oriented names

roadmap issue create "Add email validation to registration form"
roadmap issue create "Fix memory leak in data processing module"
roadmap issue create "Implement OAuth2 authentication"

# Milestones: Use version numbers or clear goals

roadmap milestone create "v1.0-beta"
roadmap milestone create "Security Audit Complete"
roadmap milestone create "Performance Optimization Phase"

```text

### Organizational Tips

```bash

# Use consistent labels

--labels backend,api,security
--labels frontend,ui,accessibility
--labels devops,deployment,monitoring

# Assign realistic priorities

--priority critical    # Only for production-breaking issues

--priority high        # Important features, security issues

--priority medium      # Nice-to-have features

--priority low         # Future considerations

# Set reasonable due dates

--due-date "2024-12-31"  # End of development cycle

--due-date "2024-11-15"  # Sprint deadline

```text

### Team Coordination

```bash

# Use descriptive assignee names

--assignee "frontend-team"
--assignee "backend-lead"
--assignee "security-specialist"

# Sync regularly with team

roadmap sync pull --high-performance  # Morning routine

roadmap sync push --issues --milestones  # End of day

```text

## 📈 Workflow Optimization

### Automation Opportunities

```bash

# Daily automation script

#!/bin/bash
cd /path/to/project
roadmap sync pull --high-performance > daily-sync.log 2>&1
roadmap bulk validate .roadmap/ > validation.log 2>&1
roadmap bulk health-report .roadmap/ > health.log 2>&1

# Weekly backup automation

#!/bin/bash
cd /path/to/project
roadmap bulk backup .roadmap/ --destination ./backups/weekly-$(date +%Y%m%d)

```text

### Integration with Development Tools

```bash

# Git hooks integration (example)

# In .git/hooks/pre-commit:

#!/bin/bash
roadmap bulk validate .roadmap/
if [ $? -ne 0 ]; then
  echo "Roadmap validation failed!"
  exit 1
fi

# CI/CD integration (example)

# In your CI pipeline:

roadmap sync pull --high-performance
roadmap bulk validate .roadmap/
roadmap sync push --issues --milestones

```text

---

This workflow guide provides comprehensive patterns for using the Roadmap CLI effectively in various scenarios. Choose the workflows that best match your project needs and team structure.
