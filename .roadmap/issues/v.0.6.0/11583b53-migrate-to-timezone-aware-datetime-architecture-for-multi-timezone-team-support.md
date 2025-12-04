---
id: 11583b53
title: Migrate to timezone-aware datetime architecture for multi-timezone team support
priority: high
status: closed
issue_type: feature
milestone: v.0.6.0
labels: []
github_issue: null
created: '2025-11-16T12:44:55.151844+00:00'
updated: '2025-11-26T18:22:03.990704+00:00'
assignee: shanewilkins
estimated_hours: 160.0
due_date: null
depends_on: []
blocks: []
actual_start_date: null
actual_end_date: null
progress_percentage: 100.0
handoff_notes: null
previous_assignee: null
handoff_date: null
git_branches: []
git_commits: []
completed_date: null
---

# Migrate to timezone-aware datetime architecture for multi-timezone team support

## Description

The current roadmap CLI uses timezone-naive datetime objects throughout the codebase, which creates significant challenges for distributed teams working across multiple timezones. This architectural decision will become a major bottleneck as teams scale globally.

### Current Problems with Timezone-Naive Policy

#### 1. Due Date Ambiguity

- Milestone due dates like "2025-12-31 23:59:59" are ambiguous
- Users in different timezones interpret deadlines differently
- 16-hour difference between earliest and latest possible interpretation

#### 2. Activity Timeline Confusion

- Issue creation times appear incorrect to users in different timezones
- Progress reports become meaningless across distributed teams
- Historical analysis is skewed by timezone assumptions

#### 3. GitHub API Integration Issues

- GitHub returns timezone-aware datetimes (ISO 8601 with Z suffix)
- Current system strips timezone info, losing critical context
- Sync operations can appear to have incorrect timestamps

#### 4. Enterprise Scalability Blocker

- Cannot support distributed teams without proper timezone handling
- "End of day" deadlines are meaningless without timezone context
- Sprint planning becomes impossible across timezones

### Strategic Analysis: Migration Timing

**Scenario A: Stay Naive → Future Migration = VERY HIGH PAIN 🔴**
- Data Migration: All existing dates need timezone context (guesswork required)
- User Impact: Historical dates could change meaning
- Code Changes: ~500+ locations need updates
- Testing: All datetime logic needs re-validation
- Rollback Risk: Extremely difficult to reverse

**Scenario B: Switch Now = MODERATE EFFORT 🟡**
- Data Migration: Clean slate - interpret all existing as UTC
- User Impact: Minimal (dates stay same, just become explicit)
- Code Changes: ~100 key locations
- Testing: New datetime logic validation
- Rollback Risk: Manageable with proper migration

### Recommended Solution: Timezone-Aware Architecture

Adopt UTC-based timezone-aware datetime handling with user-local display:

```python

# Core principle: Store in UTC, display in user's timezone

milestone.due_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

# User sees their local time

# London user: "Jan 1, 2026 12:59 AM GMT"

# SF user: "Dec 31, 2025 3:59 PM PST"

```text

## Implementation Plan

### Phase 1: Core Infrastructure (2 weeks, 80 hours)

**1.1 Timezone Utilities**

```python
from zoneinfo import ZoneInfo
from datetime import timezone

def now_utc():
    """Always return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def parse_user_input(date_str, user_timezone="UTC"):
    """Parse user input assuming their timezone."""
    naive_dt = datetime.fromisoformat(date_str)
    user_tz = ZoneInfo(user_timezone)
    return naive_dt.replace(tzinfo=user_tz).astimezone(timezone.utc)

```text

**1.2 Model Updates**
- Update all datetime fields to be timezone-aware by default
- Add timezone validation to Pydantic models
- Create migration utilities for existing data

**1.3 Parser Updates**
- Update `_parse_datetime` methods to preserve timezone information
- Handle GitHub API datetime format properly
- Ensure backward compatibility during transition

### Phase 2: Data Migration (1 week, 40 hours)

**2.1 Existing Data Migration**

```python
def migrate_roadmap_data():
    """Migrate all existing naive datetimes to UTC-aware."""
    for issue in all_issues():
        if issue.created.tzinfo is None:
            issue.created = issue.created.replace(tzinfo=timezone.utc)
        if issue.updated.tzinfo is None:
            issue.updated = issue.updated.replace(tzinfo=timezone.utc)
        # Save updated issue

```text

**2.2 GitHub Sync Alignment**
- Remove `.replace(tzinfo=None)` calls in GitHub integration
- Keep timezone information from GitHub API responses
- Ensure proper timezone handling in sync operations

### Phase 3: User Experience (2 weeks, 40 hours)

**3.1 User Timezone Preferences**

```python
class UserConfig:
    timezone: str = "UTC"  # Default to UTC

# CLI timezone display

@click.option('--timezone', help='Display timezone')
def list_issues(timezone):
    user_tz = timezone or get_user_config().timezone
    for issue in issues:
        local_time = issue.due_date.astimezone(ZoneInfo(user_tz))
        console.print(f"Due: {local_time}")

```text

**3.2 CLI Enhancements**
- Add timezone options to all date display commands
- Show timezone context in date outputs
- Support timezone-aware date input parsing

**3.3 Configuration System**
- Add user timezone configuration
- Default timezone detection from system
- Timezone validation and error handling

## Benefits

### Immediate Benefits

- 🌍 **Global Team Ready**: Support distributed teams from day one
- 🔗 **Perfect GitHub Sync**: No timezone conversion edge cases
- 📅 **Clear Deadlines**: "End of day" has specific meaning
- 📊 **Accurate Analytics**: Timeline analysis works across timezones

### Long-term Benefits

- 📈 **Enterprise Scalable**: Ready for large distributed organizations
- 🎯 **Professional UX**: Each user sees times in their local zone
- 🛡️ **Future-Proof**: No painful migration needed later
- 💼 **Competitive Advantage**: Superior timezone handling vs competitors

## Risk Assessment

**Technical Risks: LOW** 🟢
- Well-established Python timezone libraries (zoneinfo)
- Clear migration path from existing architecture
- Extensive test coverage can validate changes

**User Impact: LOW** 🟢
- Existing behavior preserved (dates display the same initially)
- Gradual rollout possible with feature flags
- Clear communication about timezone improvements

**Business Risk: HIGH if delayed** 🔴
- Competitor advantage in distributed team market
- Customer churn if timezone issues cause confusion
- Technical debt grows exponentially with codebase size

## Acceptance Criteria

- [ ] All datetime objects are timezone-aware (UTC storage)
- [ ] User can configure display timezone preference
- [ ] CLI commands show timezone context in outputs
- [ ] GitHub API integration preserves timezone information
- [ ] Existing data migrated without user-visible changes
- [ ] Comprehensive test coverage for timezone scenarios
- [ ] Documentation updated with timezone best practices
- [ ] Performance impact < 5% for datetime operations

## Dependencies

- Python 3.9+ (for zoneinfo support)
- Pydantic model updates
- Database/file format migration utilities

## Success Metrics

- Zero timezone-related user complaints post-migration
- Support for users in 3+ different timezones
- GitHub sync operations maintain correct timestamps
- All existing functionality preserved
- Performance benchmarks maintained

Brief description of the issue or feature request.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
