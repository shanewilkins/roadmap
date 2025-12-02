---
id: 515a927c
title: Implement automatic milestone and project progress updates based on issue completion
priority: high
status: closed
issue_type: feature
milestone: v.0.3.0
labels: []
github_issue: 8
created: '2025-10-11T20:24:40.653811+00:00'
updated: '2025-11-16T13:41:23.264720'
assignee: shanewilkins
estimated_hours: 5.0
due_date: null
depends_on: []
blocks: []
actual_start_date: '2025-11-15T15:21:56.032509+00:00'
actual_end_date: null
progress_percentage: 0.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
---

# Implement automatic milestone and project progress updates based on issue completion

## Description

Currently, users work directly on issues but must manually track and update milestone and project-level progress. We need to implement automatic progress aggregation that flows upward: issue completion → milestone progress → project roadmap updates. This creates a single source of truth where individual work automatically reflects in higher-level planning documents.

## Current State Analysis

### What Works Now
- Individual issue tracking with status and progress
- Manual milestone and project management
- Basic relationships between issues and milestones

### What's Missing
- Automatic milestone progress calculation from assigned issues
- Project-level progress aggregation from multiple milestones
- Real-time updates when issue status changes
- Timeline adjustments based on actual completion rates
- Automatic milestone completion detection
- Project health indicators and risk assessment

## Proposed Integration Architecture

### Progress Flow Hierarchy
```
Issues (individual work)
    ↓ automatic aggregation
Milestones (feature/release groupings)
    ↓ automatic aggregation
Projects (top-level initiatives)
    ↓ automatic reporting
Project Portfolio Dashboard
```

### Automatic Update Triggers
1. **Issue Status Change** → Update milestone progress
2. **Issue Progress Update** → Recalculate milestone percentage
3. **Milestone Completion** → Update project timeline
4. **Issue Assignment to Milestone** → Refresh milestone scope
5. **Estimated Hours Change** → Update timeline projections

## Detailed Feature Requirements

### Issue-to-Milestone Integration

#### Progress Calculation
```python
# Milestone progress based on assigned issues
def calculate_milestone_progress(milestone_id):
    issues = get_issues_for_milestone(milestone_id)

    if not issues:
        return 0.0

    # Option 1: Simple count-based
    completed = len([i for i in issues if i.status == 'done'])
    return (completed / len(issues)) * 100

    # Option 2: Effort-weighted (preferred)
    total_effort = sum(i.estimated_hours or 1 for i in issues)
    completed_effort = sum(i.estimated_hours or 1 for i in issues if i.status == 'done')
    return (completed_effort / total_effort) * 100
```

#### Status Propagation
```python
# Automatic milestone status updates
def update_milestone_status(milestone_id):
    progress = calculate_milestone_progress(milestone_id)

    if progress >= 100.0:
        milestone.status = 'completed'
        milestone.actual_end_date = datetime.now()
    elif progress > 0:
        milestone.status = 'in-progress'
        if not milestone.actual_start_date:
            milestone.actual_start_date = datetime.now()
    else:
        milestone.status = 'not-started'
```

### Milestone-to-Project Integration

#### Project Progress Aggregation
```python
# Project progress from milestone completion
def calculate_project_progress(project_id):
    milestones = get_milestones_for_project(project_id)

    if not milestones:
        return 0.0

    # Weight by milestone importance/effort
    total_weight = sum(m.estimated_effort or 1 for m in milestones)
    completed_weight = sum(m.estimated_effort or 1 for m in milestones if m.status == 'completed')

    return (completed_weight / total_weight) * 100
```

#### Timeline Projection
```python
# Automatic timeline updates based on velocity
def update_project_timeline(project_id):
    project = get_project(project_id)
    milestones = get_milestones_for_project(project_id)

    # Calculate velocity from completed work
    velocity = calculate_completion_velocity(milestones)

    # Project remaining work based on incomplete milestones
    remaining_effort = sum(m.estimated_effort for m in milestones if m.status != 'completed')

    # Update projected end date
    projected_completion = calculate_projected_date(velocity, remaining_effort)
    project.projected_end_date = projected_completion

    # Risk assessment
    if projected_completion > project.target_end_date:
        project.risk_level = 'high'
        project.schedule_variance = (projected_completion - project.target_end_date).days
```

### Real-Time Update System

#### Event-Driven Updates
```python
# Hook into issue update events
@event_listener('issue_updated')
def on_issue_updated(issue_id, changes):
    if 'status' in changes or 'progress_percentage' in changes:
        # Find affected milestones
        milestones = get_milestones_containing_issue(issue_id)
        for milestone in milestones:
            update_milestone_progress(milestone.id)

            # Find affected projects
            projects = get_projects_containing_milestone(milestone.id)
            for project in projects:
                update_project_progress(project.id)
                update_project_timeline(project.id)
```

#### Batch Update Commands
```bash
# CLI commands for manual recalculation
roadmap recalculate milestone MILESTONE_ID
roadmap recalculate project PROJECT_ID
roadmap recalculate all

# Status reporting
roadmap milestone status MILESTONE_ID --show-issues
roadmap project status PROJECT_ID --show-milestones --show-timeline
```

## Acceptance Criteria

### Automatic Progress Calculation
- [ ] Milestone progress automatically updates when issue status changes
- [ ] Project progress automatically updates when milestone status changes
- [ ] Progress calculation supports both count-based and effort-weighted methods
- [ ] Real-time updates occur on issue/milestone modifications

### Status Propagation
- [ ] Milestone status automatically changes based on issue completion
- [ ] Project status reflects milestone completion state
- [ ] Automatic start/end date tracking for milestones and projects
- [ ] Completion detection and status finalization

### Timeline Management
- [ ] Project timeline updates based on actual completion velocity
- [ ] Schedule variance calculation and risk assessment
- [ ] Projected completion date calculation
- [ ] Timeline visualization shows actual vs planned progress

### Integration Points
- [ ] Issue assignment to milestone triggers progress recalculation
- [ ] Milestone assignment to project triggers project update
- [ ] Bulk operations maintain data consistency
- [ ] GitHub sync includes progress updates

### User Interface
- [ ] CLI commands for manual progress recalculation
- [ ] Progress reporting commands with drill-down capability
- [ ] Visual progress indicators in status displays
- [ ] Warning alerts for schedule risks

## Implementation Plan

### Phase 1: Core Progress Engine (2h)
- [ ] Implement milestone progress calculation from issues
- [ ] Implement project progress calculation from milestones
- [ ] Add automatic status propagation logic
- [ ] Create event system for real-time updates

### Phase 2: Timeline Intelligence (2h)
- [ ] Add velocity calculation from historical data
- [ ] Implement projected completion date calculation
- [ ] Add schedule variance and risk assessment
- [ ] Create timeline adjustment algorithms

### Phase 3: CLI Integration (1h)
- [ ] Add recalculation commands to CLI
- [ ] Enhance status display commands with progress info
- [ ] Add progress reporting and drill-down commands
- [ ] Integrate with existing issue/milestone/project commands

## Technical Implementation Details

### Data Model Enhancements
```yaml
# Enhanced milestone fields
milestone:
  calculated_progress: float  # Auto-calculated from issues
  last_progress_update: datetime
  completion_velocity: float  # Issues/week
  risk_level: enum  # low, medium, high

# Enhanced project fields
project:
  calculated_progress: float  # Auto-calculated from milestones
  projected_end_date: date    # Auto-calculated
  schedule_variance: int      # Days ahead/behind
  completion_velocity: float  # Milestones/week
  risk_level: enum
```

### Configuration Options
```bash
# Progress calculation preferences
roadmap config set progress.calculation_method "effort_weighted"  # or "count_based"
roadmap config set progress.auto_update true
roadmap config set progress.velocity_window_weeks 4

# Timeline projection settings
roadmap config set timeline.auto_adjust true
roadmap config set timeline.risk_threshold_days 7
roadmap config set timeline.velocity_smoothing 0.3
```

### Performance Considerations
- Batch updates to avoid excessive recalculation
- Caching of calculated values with invalidation
- Async processing for large project hierarchies
- Debounced updates for rapid issue changes

## User Stories

### Story 1: Project Manager - Real-Time Visibility
**As a** project manager
**I want** project progress to automatically update when team members complete issues
**So that** I have real-time visibility into project health without manual tracking

### Story 2: Team Lead - Milestone Tracking
**As a** team lead
**I want** milestone progress to reflect the actual completion of assigned issues
**So that** I can accurately communicate milestone status to stakeholders

### Story 3: Individual Contributor - Progress Visibility
**As a** developer completing issues
**I want** to see how my work contributes to milestone and project progress
**So that** I understand the impact of my individual contributions

### Story 4: Stakeholder - Timeline Confidence
**As a** project stakeholder
**I want** timeline projections based on actual completion velocity
**So that** I can make informed decisions about resource allocation and expectations

## Success Metrics

- **Reduced manual tracking time** by 80% for project managers
- **Improved timeline accuracy** through velocity-based projections
- **Increased visibility** into project health and risk factors
- **Better team alignment** through clear progress indicators

## Integration Considerations

### GitHub Sync Integration
- Progress updates should sync to GitHub issue milestones
- Project progress could update GitHub project boards
- Timeline changes might trigger GitHub milestone due date updates

### Visualization Integration
- Progress data should feed into charts and dashboards
- Timeline visualization should show actual vs projected completion
- Risk indicators should be prominently displayed

### Notification System
- Alert on milestone completion
- Warn on schedule variance exceeding thresholds
- Notify on risk level changes

## Related Issues

- 1fb2b36c: Enhanced init command (project creation integration)
- b55e5d2f: GitHub sync status (ensure progress syncs properly)
- Future: Dashboard and visualization features

## Priority Justification

**High Priority** because:
- **Core value proposition**: Automatic progress tracking is key differentiator
- **User experience**: Manual tracking defeats automation purpose
- **Data integrity**: Ensures consistency between individual work and project status
- **Decision making**: Accurate progress data enables better project decisions
- **Team motivation**: Visible progress contribution increases engagement

---
*Created by roadmap CLI*
Assignee: @shanewilkins
