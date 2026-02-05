---
id: e0cdb51f
title: Refactor to unified datetime parser - eliminate DRY violations across codebase
headline: ''
priority: medium
status: todo
issue_type: other
milestone: backlog
labels:
- synced:from-github
remote_ids: {}
created: '2026-02-05T15:17:52.185215+00:00'
updated: '2026-02-05T15:17:52.185216+00:00'
assignee: null
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
github_issue: null
---

# Refactor to unified datetime parser - eliminate DRY violations across codebase

## Description

**🚨 CRITICAL TECHNICAL DEBT: Eliminate 20+ duplicate datetime parsing implementations**

### **Current Problem:**

- Multiple `_parse_datetime` methods in parser.py (IssueParser, MilestoneParser, ProjectParser)
- 15+ scattered `fromisoformat(x.replace("Z", "+00:00"))` implementations across modules
- Inconsistent timezone handling and error behavior
- Maintenance nightmare requiring changes in multiple files for any datetime bug

### **Solution: Unified DateTime Parser Architecture**

Create a single, centralized datetime parsing system that eliminates all duplication and provides consistent behavior across the entire codebase.

### **Benefits:**

- ✅ Eliminate ~500+ lines of duplicate code
- ✅ Single source of truth for datetime parsing
- ✅ Consistent timezone handling across entire codebase
- ✅ Easier maintenance and testing
- ✅ Better error handling and logging
- ✅ Future-proof architecture for datetime features

## Implementation Plan

1. **Create `roadmap/datetime_parser.py`** with UnifiedDateTimeParser class
2. **Single source of truth** for all datetime parsing needs:
   - `parse_any_datetime()` - Universal parser for all sources
   - `parse_github_timestamp()` - Specialized GitHub API handling
   - `parse_file_datetime()` - Frontmatter/file parsing
3. **Replace all duplicate implementations** across:
   - parser.py (3x _parse_datetime methods)
   - github_client.py (6x fromisoformat calls)
   - performance_sync.py (3x fromisoformat calls)
   - enhanced_github_integration.py (2x fromisoformat calls)
   - analytics.py (3x fromisoformat calls)
   - ci_tracking.py (1x fromisoformat call)
4. **Update all tests** to use unified parser
5. **Comprehensive validation** ensuring no behavioral regressions

## Acceptance Criteria

- [ ] UnifiedDateTimeParser class created with comprehensive datetime parsing methods
- [ ] All parser.py _parse_datetime methods replaced with unified parser calls
- [ ] All scattered fromisoformat implementations replaced with unified parser calls
- [ ] All existing tests pass without behavioral changes
- [ ] Comprehensive test coverage for unified parser (edge cases, timezones, formats)
- [ ] Performance benchmarks show no regression in datetime parsing speed
- [ ] Documentation updated with new parsing patterns and usage examples
- [ ] No duplicate datetime parsing logic remains in codebase
- [ ] Consistent error handling and logging across all datetime operations
