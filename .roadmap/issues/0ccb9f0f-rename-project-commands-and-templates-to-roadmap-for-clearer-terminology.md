---
id: 0ccb9f0f
title: Rename project commands and templates to roadmap for clearer terminology
priority: medium
status: todo
issue_type: feature
milestone: ''
labels: []
github_issue: null
created: '2025-10-11T20:34:42.628405'
updated: '2025-10-11T20:34:42.628410'
assignee: shane
estimated_hours: 3.0
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

# Rename project commands and templates to roadmap for clearer terminology

## Description

The current CLI uses "project" for the top-level document template and commands, but "roadmap" is a much clearer and more intuitive term for users. Since this is a roadmap CLI tool, the top-level planning document should be called a "roadmap" rather than a "project". This change will improve user understanding and make the tool's purpose more obvious.

## Current State Analysis

### Existing "Project" Usage
```bash
# Current CLI commands
roadmap project create "My Project"
roadmap project list
roadmap project overview
roadmap project update PROJECT_ID
roadmap project delete PROJECT_ID

# Current file structure
.roadmap/projects/abc123-my-project.md

# Current terminology in code
- Project class/model
- project_* functions  
- projects/ directory
- "project" in documentation
```

### User Confusion Points
- Tool is called "Roadmap CLI" but creates "projects" 
- Users naturally think in terms of "roadmaps" for planning
- "Project" is overloaded (could mean git project, work project, etc.)
- Documentation refers to "roadmap" but CLI uses "project"

## Proposed Terminology Changes

### CLI Command Renaming
```bash
# New CLI commands (proposed)
roadmap roadmap create "My Roadmap"     # was: roadmap project create
roadmap roadmap list                    # was: roadmap project list  
roadmap roadmap overview                # was: roadmap project overview
roadmap roadmap update ROADMAP_ID       # was: roadmap project update
roadmap roadmap delete ROADMAP_ID       # was: roadmap project delete

# Alternative shorter commands
roadmap create "My Roadmap"             # Top-level shortcut
roadmap list                            # Lists roadmaps by default
roadmap overview                        # Current roadmap overview
```

### File Structure Changes
```bash
# New file structure
.roadmap/roadmaps/abc123-my-roadmap.md  # was: .roadmap/projects/

# Or keep projects/ folder but change content
.roadmap/projects/abc123-my-roadmap.md  # File naming change only
```

### Documentation and Template Updates
```yaml
# New roadmap document header (was project)
---
id: abc123
title: My Roadmap
type: roadmap              # was: project
priority: high
status: active
owner: shane
created: '2025-10-11T20:30:00'
updated: '2025-10-11T20:30:00'
---

# My Roadmap

## Overview
This roadmap outlines...
```

## Implementation Options

### Option 1: Complete Renaming (Recommended)
- Rename all CLI commands from `project` to `roadmap`
- Update file templates and documentation
- Maintain backwards compatibility with aliases
- Update all internal code references

### Option 2: Dual Commands
- Keep existing `project` commands working
- Add new `roadmap` commands as primary
- Gradually deprecate `project` commands
- Allow both file types during transition

### Option 3: Top-Level Shortcut Only
- Keep `roadmap project` commands unchanged
- Add `roadmap create/list/overview` shortcuts
- Minimal code changes required
- Less disruptive to existing users

## Detailed Implementation Plan

### Phase 1: CLI Command Structure (1h)
```python
# Add new command group
@cli.group()
def roadmap():
    """Manage roadmaps (top-level planning documents)."""
    pass

# New commands
@roadmap.command()
def create(title, **kwargs):
    """Create a new roadmap."""
    # Implementation

@roadmap.command()
def list(**kwargs):  
    """List all roadmaps."""
    # Implementation
    
# Backwards compatibility aliases
@cli.group()
def project():
    """Manage projects (deprecated: use 'roadmap' commands)."""
    click.echo("⚠️  'project' commands are deprecated. Use 'roadmap' commands instead.")
    pass
```

### Phase 2: Template and Documentation Updates (1h)
- Update roadmap document templates
- Change all documentation references
- Update help text and examples
- Modify error messages and output

### Phase 3: Internal Code Refactoring (1h)
- Rename internal classes and functions
- Update file handling logic
- Modify database/storage schema if needed
- Update tests and examples

## Acceptance Criteria

### CLI Command Changes
- [ ] New `roadmap roadmap` commands work identically to old `roadmap project` commands
- [ ] Backwards compatibility: old `roadmap project` commands still work with deprecation warnings
- [ ] Help text and documentation updated throughout
- [ ] Error messages use new "roadmap" terminology

### File and Template Updates
- [ ] New roadmap documents use "roadmap" terminology in templates
- [ ] Existing project files continue to work without modification
- [ ] File naming conventions updated (configurable)
- [ ] Documentation examples use new terminology

### User Experience
- [ ] Clear migration path for existing users
- [ ] Deprecation warnings are helpful and informative
- [ ] New users naturally discover "roadmap" commands
- [ ] Command discovery improved with intuitive naming

### Backwards Compatibility
- [ ] Existing project files load and work correctly
- [ ] Old CLI commands continue to function
- [ ] No breaking changes for existing workflows
- [ ] Clear timeline for eventual deprecation removal

## Migration Strategy

### For Existing Users
```bash
# Automatic migration helper command
roadmap migrate project-to-roadmap     # Convert existing files/config

# Show migration status
roadmap migrate status                 # What needs converting

# Opt-in migration
roadmap config set terminology roadmap # Switch to new terms
```

### For New Users
- Default to "roadmap" terminology from `roadmap init`
- Documentation examples use new commands
- Help system primarily shows roadmap commands
- Project commands shown as "legacy" options

## Technical Implementation Details

### Command Structure Options
```python
# Option A: New top-level group
@cli.group()
def roadmap_cmd():  # Avoid conflict with @cli
    """Manage roadmaps."""
    pass

# Option B: Subcommand approach  
@cli.group()
def roadmap():
    """Roadmap management commands."""
    pass
    
@roadmap.command()
def create():
    pass

# Option C: Hybrid approach
@cli.command()
def create():  # Top-level shortcut
    """Create a new roadmap."""
    pass
```

### Configuration Options
```bash
# User preferences
roadmap config set commands.use_legacy_project_terms false
roadmap config set commands.show_deprecation_warnings true
roadmap config set files.roadmap_directory "roadmaps"  # vs "projects"
```

### Backwards Compatibility Code
```python
def handle_legacy_project_command(ctx, command_name):
    """Show deprecation warning and redirect to roadmap command."""
    click.echo("⚠️  DEPRECATED: 'project {command}' is deprecated.")
    click.echo(f"    Use: 'roadmap {command}' instead")
    click.echo()
    
    # Execute new command
    ctx.invoke(roadmap_commands[command_name])
```

## User Stories

### Story 1: New User Discovery
**As a** new user of roadmap CLI
**I want** the commands to use intuitive "roadmap" terminology
**So that** I can easily understand what the tool does and how to use it

### Story 2: Existing User Migration
**As an** existing user with project files
**I want** my existing files and workflows to continue working
**So that** I can adopt new terminology without losing my data

### Story 3: Team Onboarding
**As a** team lead onboarding new team members
**I want** consistent terminology between the tool name and commands
**So that** new users aren't confused by mismatched naming

### Story 4: Documentation Clarity
**As a** user reading documentation
**I want** examples and help text to use "roadmap" terminology consistently
**So that** I can follow along without terminology confusion

## Alternative Approaches Considered

### Keep "Project" Terminology
- **Pros**: No breaking changes, simpler implementation
- **Cons**: Continues user confusion, misaligned naming

### Complete Breaking Change
- **Pros**: Clean, consistent terminology
- **Cons**: Breaks existing workflows, user frustration

### Configuration-Based Toggle
- **Pros**: User choice, gradual adoption
- **Cons**: Code complexity, ongoing maintenance

## Success Metrics

- **Reduced user confusion** about tool purpose and commands
- **Improved discoverability** of main features
- **Maintained compatibility** with existing workflows
- **Positive user feedback** on terminology clarity

## Related Issues

- 1fb2b36c: Enhanced init command (should create "roadmaps" not "projects")
- 515a927c: Progress tracking (terminology should be consistent)
- Future: Documentation updates across all guides

## Priority Justification

**Medium Priority** because:
- **User experience**: Clear terminology improves tool adoption
- **Brand consistency**: Tool name should match command terminology  
- **Long-term maintenance**: Better to fix early than accumulate confusion
- **Low risk**: Can implement with full backwards compatibility
- **Quick win**: Relatively small change with high user experience impact