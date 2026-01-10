---
id: 5b7cc2a5
title: Enhance init command with automatic project setup and credential flow
headline: '# Enhance init command with automatic project setup and credential flow'
priority: medium
status: closed
issue_type: feature
milestone: null
labels:
- priority:high
- status:done
remote_ids:
  github: '9'
created: '2026-01-09T21:32:38.017081+00:00'
updated: '2026-01-09T23:58:36.757226+00:00'
assignee: shanewilkins
estimated_hours: null
due_date: null
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
comments: []
github_issue: '9'
---

# Enhance init command with automatic project setup and credential flow

## Description

The current `roadmap init` command creates basic directory structure but doesn't provide a smooth onboarding experience for new users. We need to enhance the initialization process to automatically create a top-level project document and guide users through essential setup steps including credential configuration for GitHub integration.

## Current State Analysis

### What `init` Currently Does

- Creates `.roadmap/` directory structure
- Sets up basic configuration files
- Creates empty folders for issues, milestones, projects

### What's Missing

- No automatic project creation for the repository/workspace
- No guided credential setup flow
- No GitHub integration configuration prompts
- No validation of setup completion
- Limited user guidance for next steps

## Proposed Enhanced Flow

### 1. Smart Project Detection & Creation

```bash
roadmap init [project-name]

# If no project-name provided, infer from:

# - Git repository name

# - Current directory name

# - Prompt user for input

```text

### 2. Automatic Top-Level Project Generation

- Create a main project document that represents the entire repository/workspace
- Include sensible defaults based on detected information
- Set appropriate timeline and initial milestones

### 3. Interactive Credential Setup

- Detect if GitHub integration is desired (check for .git directory)
- Guide user through GitHub token creation
- Test connection and validate permissions
- Store credentials securely

### 4. Configuration Validation

- Verify all setup steps completed successfully
- Provide clear success/failure feedback
- Suggest next steps for getting started

## Detailed Feature Requirements

### Enhanced Init Command Options

```bash
roadmap init [OPTIONS] [PROJECT_NAME]

Options:
  --project-name TEXT     Name of the main project (auto-detected if not provided)
  --description TEXT      Project description
  --github-repo TEXT      GitHub repository (user/repo format)
  --skip-github          Skip GitHub integration setup
  --skip-project         Skip automatic project creation
  --interactive          Run in interactive mode with prompts
  --template TEXT        Use project template (basic, software, research, etc.)

```text

### Automatic Project Creation Logic

```python

# Pseudo-code for enhanced init flow

def enhanced_init():
    # 1. Detect context

    project_name = detect_project_name()
    git_repo = detect_git_repository()

    # 2. Create directory structure

    create_roadmap_structure()

    # 3. Generate main project

    if not skip_project:
        create_main_project(project_name)

    # 4. GitHub integration setup

    if git_repo and not skip_github:
        setup_github_integration(git_repo)

    # 5. Validation and next steps

    validate_setup()
    show_getting_started_guide()

```text

### Interactive Setup Flow

1. **Welcome & Context Detection**
   ```

   🚀 Roadmap CLI Initialization

   Detected: Git repository "shanewilkins/roadmap"
   Current directory: /Users/shane/roadmap

   We'll set up your roadmap with:
   ✓ Main project creation
   ✓ GitHub integration
   ✓ Credential configuration
   ```

2. **Project Setup**
   ```

   📋 Creating Main Project

   Project name: [roadmap] (auto-detected)
   Description: [A powerful CLI tool for project roadmaps]
   Owner: [shane] (from git config)
   Priority: [high]
   ```

3. **GitHub Integration**
   ```

   🔗 GitHub Integration Setup

   Repository: shanewilkins/roadmap ✓

   To sync with GitHub, you'll need a personal access token.
   → Open: https://github.com/settings/tokens
   → Create token with 'public_repo' scope
   → Paste token when prompted (secure input)
   ```

4. **Validation & Next Steps**
   ```

   ✅ Setup Complete!

   Created:
   ✓ Main project: roadmap (ID: abc12345)
   ✓ GitHub connection: Connected as shanewilkins
   ✓ Credentials: Stored securely in keychain

   Next steps:
   → roadmap project overview
   → roadmap issue create "Your first issue"
   → roadmap sync bidirectional
   ```

## Acceptance Criteria

### Core Functionality

- [x] `roadmap init` automatically creates a main project document
- [x] Project name auto-detection from git repo or directory name
- [x] Interactive prompts for missing information
- [x] Optional GitHub integration setup during init
- [ ] Credential setup flow with validation
- [x] Setup completion verification

### User Experience

- [ ] Clear progress indicators during initialization
- [ ] Helpful error messages with recovery suggestions
- [x] Option to skip optional steps (--skip-github, --skip-project)
- [x] Getting started guide after successful init
- [x] Template support for different project types

### Technical Requirements

- [x] Backwards compatibility with existing init behavior
- [ ] Proper error handling for all setup steps
- [ ] Secure credential handling during setup
- [ ] GitHub API validation during credential setup
- [ ] Configuration validation and rollback on errors

### Documentation & Testing

- [ ] Update CLI documentation with new init options
- [ ] Add examples for different initialization scenarios
- [ ] Unit tests for auto-detection logic
- [ ] Integration tests for full init flow
- [ ] Error handling test cases

## Implementation Plan

### Phase 1: Core Enhancement (2h)

- [ ] Enhance init command with project creation
- [ ] Add auto-detection for project name and git repo
- [ ] Implement basic interactive prompts
- [ ] Add validation for successful setup

### Phase 2: GitHub Integration (1.5h)

- [ ] Add GitHub credential setup to init flow
- [ ] Implement connection testing during init
- [ ] Add GitHub configuration validation
- [ ] Handle credential setup errors gracefully

### Phase 3: Polish & Documentation (0.5h)

- [ ] Add progress indicators and better UX
- [ ] Update documentation and help text
- [ ] Add template support (if time permits)
- [ ] Test edge cases and error conditions

## Progress Update

Summary of work completed (so far):

- Implemented automatic main project creation (`roadmap init` creates a project file under `.roadmap/projects`).
- Project name auto-detection from Git remote or current directory implemented in `_detect_project_context()`.
- Interactive and non-interactive flows supported (`--non-interactive`, `--yes`).
- `--skip-github` and `--skip-project` options supported.
- Template support expanded with `--template` builtin options and `--template-path` for custom template files.
- Post-init validation added (`_post_init_validate`) checking `config.yaml` and project files.
- Init manifest and targeted rollback implemented (`.roadmap/.init_manifest.json`).
- `--github-token` CLI option and `ROADMAP_GITHUB_TOKEN` env var support implemented.
- Credential flow wired to `CredentialManager` with token storage; `GitHubClient` integration tested via unit/integration tests (mocked).
- UX improvements: progress status messages and clearer prompts/ guidance for token creation.
- Documentation: `docs/INIT_ENHANCEMENTS.md` added with examples.

Remaining tasks / follow-ups:

- Add more integration tests that exercise real credential backends (or full mocks covering failure modes).
- Add environment-var fallback for `GITHUB_TOKEN` (widely used in CI) as an additional convenience.
- Polish error messages and add a short troubleshooting section to the docs.
- Decide fate of `roadmap/cli_backup_original.py` (archive/delete/keep) and update repository cleanup docs.

If you want, I can: add the `GITHUB_TOKEN` env-var fallback, create a CHANGELOG entry and bump `pyproject.toml` version, or open a PR for this branch.

## Technical Considerations

### Auto-Detection Logic

```python
def detect_project_name():
    # Priority order:

    # 1. Git repository name

    # 2. Directory name

    # 3. Package name (pyproject.toml, package.json)

    # 4. Prompt user

```text

### GitHub Repository Detection

```python
def detect_git_repository():
    # Check git remote origin

    # Parse owner/repo from URL

    # Validate repository exists and is accessible

```text

### Credential Setup Integration

```python
def setup_github_integration(repo_info):
    # Guide user through token creation

    # Test connection with minimal API call

    # Store credentials using existing credential manager

    # Configure repository settings

```text

## User Stories

### Story 1: New User - Fresh Repository

**As a** developer starting a new project
**I want** to run `roadmap init` and have everything set up automatically
**So that** I can start managing my roadmap immediately without manual configuration

### Story 2: Existing Project - Adding Roadmap

**As a** project maintainer adding roadmap to an existing repository
**I want** the init command to detect my project context and GitHub repository
**So that** I don't have to manually configure obvious settings

### Story 3: Team Onboarding - GitHub Integration

**As a** team member joining a project with roadmap
**I want** the init command to guide me through GitHub credential setup
**So that** I can collaborate on the roadmap without technical barriers

## Success Metrics

- **Reduced time to first productive use** from ~10 minutes to ~2 minutes
- **Elimination of common setup errors** (missing credentials, wrong repo config)
- **Improved user satisfaction** with onboarding experience
- **Increased GitHub integration adoption** due to easier setup

## Related Issues

- b55e5d2f: Investigate GitHub sync inconsistencies (this will help prevent future issues)
- Documentation updates needed for enhanced init flow
- Consider impact on existing roadmap installations

## Priority Justification

**High Priority** because:
- **First impressions matter**: Init is the first command new users run
- **Adoption barrier**: Complex setup prevents tool adoption
- **Support reduction**: Better onboarding reduces user support requests
- **Competitive advantage**: Smooth setup experience vs manual configuration

**Finished:** Successfully implemented comprehensive init command enhancement with automatic project setup, credential flow, and GitHub integration

---
*Created by roadmap CLI*
Assignee: @shanewilkins
