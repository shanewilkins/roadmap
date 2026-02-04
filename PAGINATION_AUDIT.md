# GitHub API Pagination Audit

## Summary
Audit of all GitHub API handlers to identify which list endpoints lack proper pagination handling.

## Status: ✅ COMPLETED

All pagination issues have been fixed with a reusable utility pattern.

## Findings

### Implementation Details

#### New: Reusable Pagination Utility
**File**: `roadmap/adapters/github/handlers/base.py`
- **Method**: `_paginate_request(method, endpoint, params, per_page)`
- **Purpose**: Centralized pagination handling for all list endpoints
- **Implementation**:
  - Loops through pages using `page` parameter
  - Checks `Link` header for `rel="next"` to detect end of pagination
  - Returns complete list of all items across all pages
  - Logs progress at DEBUG level

#### Fixed Handlers

✅ **`roadmap/adapters/github/handlers/issues.py`**
- **Method**: `get_issues()`
- **Issue**: Was returning only first 100 issues
- **Fix**: Refactored to use `_paginate_request()` utility
- **Verified**: Now correctly fetches all 1309+ issues

✅ **`roadmap/adapters/github/handlers/milestones.py`**
- **Method**: `get_milestones(state='open')`
- **Issue**: No pagination - only returned first 30 items
- **Fix**: Refactored to use `_paginate_request()` utility
- **Impact**: Now handles repos with unlimited milestones

✅ **`roadmap/adapters/github/handlers/labels.py`**
- **Method**: `get_labels()`
- **Issue**: No pagination - only returned first 30 items
- **Fix**: Refactored to use `_paginate_request()` utility
- **Impact**: Now handles repos with unlimited labels

✅ **`roadmap/adapters/github/handlers/comments.py`**
- **Method**: `get_issue_comments(issue_number)`
- **Issue**: No pagination - only returned first 30 items
- **Fix**: Refactored to use `_paginate_request()` utility
- **Impact**: Now fetches all comments for issues with high discussion

### Already Correct

✓ **`roadmap/adapters/github/handlers/collaborators.py`**
- Already had manual pagination implementation - serves as reference pattern

## Prevention Strategy

To prevent pagination bugs in the future:

1. **Use the utility**: All list endpoints in GitHub handlers should use `_paginate_request()`
2. **Code review**: PRs adding new GitHub API calls should be reviewed for pagination
3. **Testing**: Test suite should verify >100 item pagination with mock data
4. **Documentation**: Add guidelines for using `_paginate_request()` in handler docstrings

## Verification

```bash
# Before fix: Shows only 100 "Needs Pull"
uv run roadmap sync --dry-run

# After fix: Shows all 1258 "Needs Pull"
✓ Up-to-date: 51
📥 Needs Pull: 1258
Potential Conflicts: 0
```

## Files Modified

1. `roadmap/adapters/github/handlers/base.py` - Added `_paginate_request()` utility
2. `roadmap/adapters/github/handlers/issues.py` - Refactored to use utility
3. `roadmap/adapters/github/handlers/milestones.py` - Refactored to use utility
4. `roadmap/adapters/github/handlers/labels.py` - Refactored to use utility
5. `roadmap/adapters/github/handlers/comments.py` - Refactored to use utility
