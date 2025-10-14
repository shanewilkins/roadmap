---
id: ea4606b6
title: Implement CI/CD integration for automatic issue branch and commit tracking
priority: high
status: todo
issue_type: feature
milestone: ''
labels: []
github_issue: 10
created: '2025-10-11T20:28:50.243433'
updated: '2025-10-14T16:42:00.143212'
assignee: ''
estimated_hours: 4.0
depends_on: []
blocks: []
actual_start_date: null
actual_end_date: null
progress_percentage: null
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
---

# Implement CI/CD integration for automatic issue branch and commit tracking

## Description

Currently, the issue YAML header includes `git_branches` and `git_commits` fields, but these are not automatically populated. We need to implement CI/CD integration that automatically tracks which branches and commits are associated with specific issues, enabling better traceability from work items to actual code changes and deployments.

## Current State Analysis

### Issue YAML Header Fields (Currently Manual)
```yaml
git_branches: []     # Empty - should auto-populate
git_commits: []      # Empty - should auto-populate  
actual_start_date: null    # Could auto-detect from first commit
actual_end_date: null      # Could auto-detect from issue closure
completed_date: null       # Could auto-populate on status=done
```

### Missing Integration Points
- No automatic branch detection from issue ID patterns
- No commit message parsing to associate commits with issues
- No CI/CD pipeline integration for deployment tracking
- No automatic issue closure on merge/deployment
- No traceability from code changes back to requirements

## Proposed CI/CD Integration Architecture

### Branch Detection Patterns
```bash
# Automatic detection of issue-related branches
feature/ea4606b6-*           # Feature branches with issue ID
bugfix/ea4606b6-*            # Bug fix branches  
hotfix/ea4606b6-*            # Hotfix branches
ea4606b6-*                   # Simple issue ID prefix
*/ea4606b6/*                 # Issue ID anywhere in branch path
```

### Commit Message Parsing
```bash
# Commit message patterns to associate with issues
"feat: implement CI/CD integration (fixes #ea4606b6)"
"fix: resolve sync issue ea4606b6" 
"docs: update CI/CD guide for ea4606b6"
"closes ea4606b6: add branch tracking"
"related to ea4606b6: refactor sync logic"
```

### CI/CD Pipeline Integration
```yaml
# GitHub Actions integration example
name: Roadmap Issue Tracking
on:
  push:
    branches: ["**"]
  pull_request:
    types: [opened, closed, merged]
  
jobs:
  track-issue-progress:
    runs-on: ubuntu-latest
    steps:
      - name: Update Issue Tracking
        run: |
          roadmap ci track-commit ${{ github.sha }}
          roadmap ci track-branch ${{ github.ref }}
          roadmap ci track-pr ${{ github.event.number }}
```

## Detailed Feature Requirements

### Automatic Branch Tracking

#### Git Hook Integration
```python
# Git hooks for local development
def on_branch_created(branch_name):
    issue_ids = extract_issue_ids_from_branch(branch_name)
    for issue_id in issue_ids:
        roadmap_add_branch_to_issue(issue_id, branch_name)

def on_branch_checkout(branch_name):
    # Optionally auto-start issues when checking out their branch
    issue_ids = extract_issue_ids_from_branch(branch_name)
    for issue_id in issue_ids:
        if get_issue_status(issue_id) == 'todo':
            roadmap_start_issue(issue_id)
```

#### CLI Commands for Branch Management
```bash
# Manual branch association
roadmap issue branch add ea4606b6 feature/ci-cd-integration
roadmap issue branch remove ea4606b6 old-branch-name
roadmap issue branch list ea4606b6

# Automatic branch detection  
roadmap ci scan-branches          # Scan all branches for issue patterns
roadmap ci track-branch <branch>  # Track specific branch
```

### Automatic Commit Tracking

#### Commit Message Analysis
```python
def parse_commit_for_issues(commit_message, commit_sha):
    patterns = [
        r'(?:fixes?|closes?|resolves?)\s+#?(\w{8})',  # "fixes ea4606b6"
        r'(\w{8})[:]\s',                              # "ea4606b6: commit message"
        r'(?:related to|refs?)\s+(\w{8})',           # "related to ea4606b6"
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, commit_message, re.IGNORECASE):
            issue_id = match.group(1)
            associate_commit_with_issue(issue_id, commit_sha, commit_message)
```

#### Git Hook Implementation
```bash
# Post-commit hook
#!/bin/sh
# .git/hooks/post-commit
roadmap ci track-commit HEAD

# Pre-push hook  
#!/bin/sh
# .git/hooks/pre-push
roadmap ci sync-branch-tracking
```

### CI/CD Pipeline Commands

#### New CLI Commands for CI/CD
```bash
# Commit tracking
roadmap ci track-commit <commit-sha> [--message "commit message"]
roadmap ci track-commits <from-sha>..<to-sha>

# Branch tracking
roadmap ci track-branch <branch-name> [--issue-id ea4606b6]
roadmap ci track-pr <pr-number> [--branch <branch>]

# Bulk operations
roadmap ci scan-repository         # Scan entire repo history
roadmap ci sync-with-github        # Sync branch/commit data from GitHub

# Issue lifecycle automation
roadmap ci auto-start <issue-id>   # Start issue when branch created
roadmap ci auto-close <issue-id>   # Close issue when PR merged
```

### Automatic Issue Status Updates

#### PR Integration
```python
def on_pull_request_opened(pr_info):
    # Auto-start issues when PR is opened
    issue_ids = extract_issue_ids_from_branch(pr_info.head_branch)
    for issue_id in issue_ids:
        if get_issue_status(issue_id) == 'todo':
            roadmap_update_issue(issue_id, status='in-progress')

def on_pull_request_merged(pr_info):
    # Auto-complete issues when PR is merged to main
    if pr_info.base_branch in ['main', 'master', 'develop']:
        issue_ids = extract_issue_ids_from_branch(pr_info.head_branch)
        for issue_id in issue_ids:
            roadmap_update_issue(issue_id, status='done', actual_end_date=now())
```

#### Deployment Tracking
```python
def on_deployment_success(deployment_info):
    # Track which issues were deployed
    commits = get_commits_in_deployment(deployment_info)
    deployed_issues = set()
    
    for commit in commits:
        issue_ids = get_issues_for_commit(commit.sha)
        deployed_issues.update(issue_ids)
    
    for issue_id in deployed_issues:
        add_deployment_info_to_issue(issue_id, deployment_info)
```

## Acceptance Criteria

### Branch Tracking
- [ ] Automatic detection of issue IDs in branch names
- [ ] Support for multiple branch naming conventions
- [ ] CLI commands to manually associate branches with issues
- [ ] Branch tracking in issue YAML header gets populated automatically
- [ ] Integration with git hooks for real-time tracking

### Commit Tracking  
- [ ] Automatic parsing of commit messages for issue references
- [ ] Support for multiple commit message patterns (fixes, closes, refs)
- [ ] CLI commands to manually associate commits with issues
- [ ] Commit tracking in issue YAML header gets populated automatically
- [ ] Historical repository scanning for existing commits

### CI/CD Integration
- [ ] GitHub Actions workflow examples for issue tracking
- [ ] Git hooks for local development workflow
- [ ] CLI commands designed for CI/CD pipeline usage
- [ ] Support for batch operations and bulk updates
- [ ] Integration with existing GitHub sync functionality

### Automatic Status Updates
- [ ] Auto-start issues when feature branch is created
- [ ] Auto-progress issues when PR is opened
- [ ] Auto-complete issues when PR is merged to main branch
- [ ] Deployment tracking and release association
- [ ] Configurable automation rules and triggers

### Data Integrity
- [ ] Validation of issue IDs before association
- [ ] Handling of branch renames and deletions
- [ ] Cleanup of stale branch/commit references
- [ ] Conflict resolution for multiple issue associations
- [ ] Rollback capabilities for incorrect associations

## Implementation Plan

### Phase 1: Core Tracking Engine (1.5h)
- [ ] Implement issue ID extraction from branch names and commit messages
- [ ] Create CLI commands for manual branch/commit association
- [ ] Add automatic population of git_branches and git_commits fields
- [ ] Basic validation and error handling

### Phase 2: Git Integration (1.5h)
- [ ] Implement git hooks for real-time tracking
- [ ] Add repository scanning for historical data
- [ ] Create bulk update and sync operations
- [ ] Integration with existing git operations

### Phase 3: CI/CD Automation (1h)
- [ ] Create CI/CD specific CLI commands
- [ ] Implement PR lifecycle automation
- [ ] Add GitHub Actions workflow examples
- [ ] Configure automatic status transitions

## Technical Implementation Details

### Git Integration
```python
# Core git operations
class GitTracker:
    def get_branches_for_issue(self, issue_id: str) -> List[str]:
        """Find all branches containing issue ID"""
        
    def get_commits_for_issue(self, issue_id: str) -> List[GitCommit]:
        """Find all commits mentioning issue ID"""
        
    def scan_repository_history(self) -> Dict[str, List[str]]:
        """Scan entire repo for issue associations"""
```

### Configuration Options
```bash
# Branch tracking configuration
roadmap config set ci.branch_patterns "feature/{issue_id}-*,{issue_id}-*"
roadmap config set ci.auto_start_on_branch true
roadmap config set ci.auto_close_on_merge true

# Commit tracking configuration  
roadmap config set ci.commit_patterns "fixes #{issue_id},closes {issue_id},{issue_id}:"
roadmap config set ci.scan_commit_history false
roadmap config set ci.track_all_commits false

# CI/CD integration
roadmap config set ci.github_actions true
roadmap config set ci.deployment_tracking true
roadmap config set ci.main_branches "main,master,develop"
```

### GitHub Actions Integration
```yaml
# .github/workflows/roadmap-tracking.yml
name: Roadmap Issue Tracking

on:
  push:
    branches: ["**"]
  pull_request:
    types: [opened, closed]

jobs:
  track-progress:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install roadmap CLI
        run: pip install roadmap-cli
        
      - name: Configure credentials
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          roadmap config set github.owner ${{ github.repository_owner }}
          roadmap config set github.repo ${{ github.event.repository.name }}
          
      - name: Track branch and commits
        run: |
          roadmap ci track-branch ${{ github.ref_name }}
          roadmap ci track-commit ${{ github.sha }}
          
      - name: Handle PR events
        if: github.event_name == 'pull_request'
        run: |
          roadmap ci track-pr ${{ github.event.number }} --branch ${{ github.head_ref }}
          
      - name: Sync with roadmap
        run: roadmap sync bidirectional
```

## User Stories

### Story 1: Developer - Branch Association
**As a** developer working on issue ea4606b6
**I want** my feature branch `feature/ea4606b6-ci-integration` to automatically associate with the issue
**So that** there's clear traceability from requirements to code changes

### Story 2: Project Manager - Progress Visibility
**As a** project manager
**I want** to see which branches and commits are associated with each issue
**So that** I can track actual development progress and code review status

### Story 3: DevOps Engineer - Deployment Tracking
**As a** DevOps engineer
**I want** issues to automatically close when their associated PR is merged
**So that** the roadmap reflects actual deployment status without manual updates

### Story 4: Team Lead - Historical Analysis
**As a** team lead
**I want** to scan our repository history to populate existing issue associations
**So that** we have complete traceability for past work items

## Success Metrics

- **Reduced manual tracking** by 90% through automation
- **Improved traceability** from requirements to deployed code
- **Faster issue closure** through automatic PR integration
- **Better project visibility** through real development progress tracking

## Integration Considerations

### Existing Features
- Must integrate with current GitHub sync functionality
- Should work with milestone and project progress tracking
- Compatible with credential management system
- Extends existing issue YAML structure

### Future Enhancements
- Integration with deployment platforms (Kubernetes, Docker)
- Support for additional git hosting platforms (GitLab, Bitbucket)
- Advanced analytics on development velocity
- Integration with project management tools (Jira, Linear)

## Related Issues

- b55e5d2f: GitHub sync status issues (ensure CI/CD data syncs properly)
- 515a927c: Automatic progress tracking (CI/CD data should feed into progress)
- 1fb2b36c: Enhanced init command (could include CI/CD setup)

## Priority Justification

**High Priority** because:
- **Developer workflow**: Seamless integration with existing git practices
- **Automation value**: Eliminates manual tracking of branches and commits
- **Traceability**: Essential for compliance and code review processes
- **CI/CD adoption**: Modern development requires automated issue tracking
- **Data accuracy**: Automatic tracking prevents human error and omissions

---
*Created by roadmap CLI*
Assignee: @shanewilkins