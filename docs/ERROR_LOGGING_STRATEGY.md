# Error Logging Strategy for Critical Commands

## Overview

Based on our recent experiences with `archive`, `health`, `cleanup`, and `init` commands, we've learned critical failure points and patterns that need robust error logging. This document outlines a comprehensive error logging strategy for these expanding commands.

---

## Part 1: Critical Failure Points by Command

### 1. Archive Command (`roadmap/presentation/cli/issues/archive.py`)

**Lessons Learned:**
- `.glob()` vs `.rglob()` confusion caused silent failures
- Issues not found when searching for files in milestone subfolders
- Archive directory structure not preserved, causing organizational issues
- Database marking operations failing silently

**Critical Failure Points:**
| Operation | Error Type | Severity | Current Logging |
|-----------|-----------|----------|-----------------|
| File search (rglob) | FileNotFoundError | HIGH | None - silently skips |
| Directory creation | OSError/PermissionError | HIGH | Minimal |
| File rename/move | OSError/FileExistsError | HIGH | Catch-all only |
| Database marking | DatabaseError | MEDIUM | Warning only |
| Issue parsing | ParseError | MEDIUM | Silent skip |

**Specific Issues:**
```python
# PROBLEM: Silent failures when files not found
issue_files = list((roadmap_dir / "issues").rglob(f"{issue_id[:8]}*.md"))
if issue_files:
    # Success path logs nothing
    issue_file = issue_files[0]
    issue_file.rename(archive_file)
else:
    # Only final error logged, intermediate steps lost
    console.print(f"❌ Issue file not found for: {issue_id}")
```

**Recommended Logging Pattern:**
```python
logger.debug("searching_for_issue_file",
    search_pattern=f"{issue_id[:8]}*.md",
    search_path=str(roadmap_dir / "issues"),
    search_recursive=True)

issue_files = list((roadmap_dir / "issues").rglob(f"{issue_id[:8]}*.md"))

if issue_files:
    logger.info("issue_file_located",
        issue_id=issue_id,
        file_path=str(issue_files[0]),
        file_count=len(issue_files))
else:
    logger.warning("issue_file_not_found",
        issue_id=issue_id,
        search_pattern=f"{issue_id[:8]}*.md",
        search_path=str(roadmap_dir / "issues"))
    # More context needed here
```

---

### 2. Health Command (`roadmap/application/health.py`)

**Lessons Learned:**
- File parsing failures need context about what was attempted
- Folder structure issues are silent (only reported in final summary)
- Duplicate detection works but doesn't prevent downstream issues
- Malformed files detected but not acted upon by health itself

**Critical Failure Points:**
| Operation | Error Type | Severity | Current Logging |
|-----------|-----------|----------|-----------------|
| File parsing | YAMLError | MEDIUM | Silent skip |
| Folder traversal | OSError | HIGH | Generic catch-all |
| Issue retrieval | IssueNotFoundError | LOW | Silent skip |
| Duplicate detection | Logic issue | MEDIUM | None |

**Specific Issues:**
```python
# PROBLEM: Silent exceptions with minimal context
try:
    issue = core.issue_service.get_issue(issue_id)
    if issue and issue.milestone:
        # ...
except Exception:
    # Skip files that can't be parsed - but what was the actual error?
    pass

# PROBLEM: Folder structure issues found but not categorized by severity
potential_issues = {"misplaced": [], "orphaned": []}
# These are reported in summary but no granular logging of each discovery
```

**Recommended Logging Pattern:**
```python
# Log parsing attempts
logger.debug("attempting_issue_parse",
    file_path=str(issue_file),
    issue_id=issue_id)

try:
    issue = core.issue_service.get_issue(issue_id)
    logger.debug("issue_retrieved", issue_id=issue_id, has_milestone=bool(issue.milestone))

    if issue and issue.milestone:
        # Detailed logging of the check
        logger.info("misplaced_issue_detected",
            issue_id=issue_id,
            current_location=str(issue_file),
            expected_location=str(milestone_folder / issue_file.name),
            milestone=issue.milestone)
except IssueNotFoundError as e:
    logger.warning("issue_not_found", issue_id=issue_id, error=str(e))
except YAMLError as e:
    logger.error("yaml_parse_error",
        file_path=str(issue_file),
        error_type=type(e).__name__,
        error_message=str(e),
        classification="system_error")
except Exception as e:
    logger.error("unexpected_error_parsing_issue",
        file_path=str(issue_file),
        issue_id=issue_id,
        error_type=type(e).__name__,
        error_message=str(e),
        classification=classify_error(e))
```

---

### 3. Cleanup Command (`roadmap/presentation/cli/cleanup.py`)

**Lessons Learned:**
- Malformed file fixing requires detailed tracking of what changed
- YAML parsing failures need before/after context
- Partial fixes should be logged separately from full failures
- Type mismatches (git_commits, git_branches) need specific logging

**Critical Failure Points:**
| Operation | Error Type | Severity | Current Logging |
|-----------|-----------|----------|-----------------|
| File read | FileNotFoundError | HIGH | Generic |
| YAML parse | YAMLError | HIGH | Generic |
| YAML dump | YAMLError | HIGH | Generic |
| File write | PermissionError/OSError | HIGH | Generic |
| Type conversion | ValueError | MEDIUM | None |

**Specific Issues:**
```python
# PROBLEM: Generic error reporting without operation context
try:
    content = file_path.read_text(encoding="utf-8")
    # ...
    frontmatter = yaml.safe_load(frontmatter_str)
except yaml.YAMLError:
    result["errors"].append(file_rel)
    continue  # No logging of what failed or why

# PROBLEM: Type conversions don't log what was converted
if isinstance(commit, str):
    fixed_commits.append({"hash": commit})
    needs_fix = True
    # No logging of this conversion
```

**Recommended Logging Pattern:**
```python
# Log file processing
logger.debug("processing_file", file_path=str(file_path), file_size_bytes=file_path.stat().st_size)

try:
    content = file_path.read_text(encoding="utf-8")

    # Log YAML parsing attempt
    logger.debug("parsing_frontmatter", file_path=str(file_path))
    frontmatter = yaml.safe_load(frontmatter_str)

    # Log type conversions with details
    if "git_commits" in frontmatter and isinstance(frontmatter["git_commits"], list):
        for i, commit in enumerate(frontmatter["git_commits"]):
            if isinstance(commit, str):
                logger.info("converting_git_commit_format",
                    file_path=str(file_path),
                    commit_index=i,
                    from_type="str",
                    to_type="dict",
                    commit_hash=commit[:8] if len(commit) >= 8 else commit)
                fixed_commits.append({"hash": commit})
                needs_fix = True

    # Log write operations
    if needs_fix:
        logger.info("writing_fixed_frontmatter",
            file_path=str(file_path),
            changes_made=needs_fix,
            dry_run=dry_run)

        if not dry_run:
            fixed_content = f"---\n{yaml.dump(frontmatter)}---\n{markdown_content}"
            file_path.write_text(fixed_content, encoding="utf-8")
            logger.info("file_fixed_successfully",
                file_path=str(file_path))

except FileNotFoundError as e:
    logger.error("file_not_found",
        file_path=str(file_path),
        original_error=str(e),
        classification="system_error")
    result["errors"].append(file_rel)
except yaml.YAMLError as e:
    logger.error("yaml_parse_error",
        file_path=str(file_path),
        error_line=getattr(e, 'problem_mark', None),
        error_detail=str(e),
        classification="system_error")
    result["errors"].append(file_rel)
```

---

### 4. Init Command (`roadmap/cli/core.py` + `roadmap/cli/init_workflow.py`)

**Lessons Learned:**
- Concurrent initialization attempts need locking and clear error messages
- Partial initialization requires rollback on error
- Directory creation failures prevent subsequent steps
- Validation failures happen at different stages (pre, during, post)

**Critical Failure Points:**
| Operation | Error Type | Severity | Current Logging |
|-----------|-----------|----------|-----------------|
| Lock acquisition | LockError | HIGH | Minimal |
| Validation (pre) | ValidationError | MEDIUM | Minimal |
| Directory creation | OSError/PermissionError | CRITICAL | Minimal |
| File creation (config/templates) | OSError/WriteError | CRITICAL | None |
| Validation (post) | ValidationError | MEDIUM | None |
| Rollback on error | OSError/RollbackError | CRITICAL | Generic |

**Specific Issues:**
```python
# PROBLEM: Lock failures not logged properly
lock = InitializationLock(lock_path)
if not lock.acquire():
    console.print("❌ Initialization already in progress...", style="bold red")
    # No logging of WHO holds the lock, WHEN it was acquired, etc.

# PROBLEM: Directory creation failures lose context
def cleanup_existing(self) -> bool:
    try:
        if self.core.roadmap_dir.exists():
            shutil.rmtree(self.core.roadmap_dir)
        return True
    except Exception as e:
        console.print(f"❌ Failed to remove existing roadmap: {e}", style="bold red")
        # Exception type and details not logged
        return False

# PROBLEM: Rollback failure doesn't prevent further operations
def rollback_on_error(self) -> None:
    if self.core.roadmap_dir.exists():
        try:
            shutil.rmtree(self.core.roadmap_dir)
        except Exception:
            pass  # Silently ignores rollback failures
```

**Recommended Logging Pattern:**
```python
# Lock acquisition with context
logger.info("attempting_init_lock_acquisition",
    lock_path=str(lock_path),
    current_time=datetime.now().isoformat())

lock = InitializationLock(lock_path)
if not lock.acquire():
    # Log the EXISTING lock details
    lock_info = lock.get_lock_info()
    logger.error("init_lock_conflict",
        lock_path=str(lock_path),
        lock_holder_pid=lock_info.get("pid"),
        lock_acquired_at=lock_info.get("timestamp"),
        classification="system_error",
        suggested_action="wait_or_remove_lock")
    return

logger.info("init_lock_acquired",
    lock_path=str(lock_path),
    process_id=os.getpid())

# Pre-validation logging
logger.info("starting_pre_initialization_validation",
    roadmap_name=name,
    force_flag=force,
    skip_github=skip_github,
    skip_project=skip_project)

try:
    # Directory creation with detailed logging
    logger.debug("creating_directory",
        path=str(self.core.roadmap_dir),
        mode="0o755",
        parent_creation=True)

    create_secure_directory(self.core.roadmap_dir, 0o755)

    logger.info("directory_created_successfully",
        path=str(self.core.roadmap_dir))

except PermissionError as e:
    logger.error("permission_denied_creating_directory",
        path=str(self.core.roadmap_dir),
        error=str(e),
        classification="system_error",
        suggested_action="check_directory_permissions")
    # Attempt rollback with logging
    self._rollback_with_logging()
    raise

except OSError as e:
    logger.error("os_error_creating_directory",
        path=str(self.core.roadmap_dir),
        error_type=type(e).__name__,
        error_code=getattr(e, 'errno', None),
        error_message=str(e),
        classification="system_error")
    self._rollback_with_logging()
    raise
```

---

## Part 2: Logging Infrastructure Assessment

### Current Capabilities

**Available:**
- `roadmap.shared.logging.get_logger()` - Structured logging with correlation IDs
- `roadmap.presentation.cli.error_logging.log_error_with_context()` - Error classification
- `roadmap.shared.errors.ErrorHandler` - Centralized error handling
- Rich console for formatted output
- File-based structured logging (JSON)

**Limitations:**
- Limited per-operation logging in archive command
- Health check doesn't log intermediate discoveries
- Cleanup doesn't track conversion details
- Init lacks execution tracing and rollback logging

### Log Levels in Use

```
DEBUG   - Detailed diagnostic information (file searches, type checks)
INFO    - General informational messages (operations, discoveries)
WARNING - Unexpected but handled situations (malformed files, missing data)
ERROR   - Error events (parse failures, write failures)
CRITICAL - Application failure (permission denied, rollback failure)
```

---

## Part 3: Logging Enhancement Recommendations

### Phase 1: Add Operation-Level Tracing (HIGH PRIORITY)

**For Archive Command:**
```python
# Add operation tracking decorator
@log_command("issue_archive", entity_type="issue", track_duration=True)
def archive_issue(...):
    # Each major operation logs its state
    logger.info("archive_operation_starting",
        mode="all_done" if all_done else "orphaned" if orphaned else "single",
        issue_count=len(issues_to_archive) if all_done or orphaned else 1)

    # Intermediate checkpoints
    logger.info("archive_operation_checkpoint",
        checkpoint="file_search_complete",
        files_found=len(issue_files),
        file_path=str(issue_file) if issue_files else None)
```

**For Cleanup Command:**
```python
# Track each file's fix state
logger.info("file_fix_attempt",
    file_path=str(file_path),
    fixes_needed=needs_fix,
    fixes_applied=list(fixes_applied.keys()) if not dry_run else None,
    result="success" if not dry_run else "dry_run_only")
```

**For Health Command:**
```python
# Log each discovery with categorization
logger.info("health_check_discovering_issue",
    check_type="folder_structure",
    issue_id=issue_id,
    issue_type="misplaced" | "orphaned" | "duplicate",
    severity="high" | "medium" | "low")
```

**For Init Command:**
```python
# Track workflow progression
logger.info("init_workflow_step",
    step_name="directory_creation" | "config_creation" | "template_setup",
    step_sequence=1,
    total_steps=5,
    status="started" | "in_progress" | "completed",
    duration_seconds=elapsed)
```

### Phase 2: Error Classification and Recovery (HIGH PRIORITY)

**Create specialized error loggers:**

```python
# archive.py - new error logging patterns
def log_archive_error(error, operation, issue_id=None, file_path=None):
    """Log archive-specific errors with recovery suggestions."""
    if isinstance(error, FileNotFoundError):
        logger.error("archive_file_not_found",
            operation=operation,
            issue_id=issue_id,
            file_path=str(file_path),
            suggested_action="verify_issue_exists_in_current_directory")
    elif isinstance(error, OSError):
        logger.error("archive_os_error",
            operation=operation,
            error_code=getattr(error, 'errno', None),
            suggested_action="check_disk_space_and_permissions")
```

### Phase 3: Structured Context Logging

**For all commands, add correlation IDs and request tracking:**

```python
# In command handler
request_id = str(uuid.uuid4())[:8]
logger.bind(request_id=request_id)

logger.info("command_received",
    command="archive",
    subcommand="--all-done",
    request_id=request_id,
    user=getpass.getuser(),
    working_directory=str(Path.cwd()))

# All subsequent logs in that command contain request_id
```

### Phase 4: Dry-Run Mode Logging

**Track all operations that would be performed:**

```python
if dry_run:
    logger.info("dry_run_mode_enabled",
        would_archive_count=len(issues_to_archive),
        would_move_files=archive_file_paths,
        would_update_db_records=db_updates)
```

---

## Part 4: Implementation Priority

### Critical (Implement First)
1. **Archive**: Add detailed file search/move logging
2. **Cleanup**: Track conversion details and write operations
3. **Init**: Add rollback logging and lock status logging

### Important (Implement Second)
4. **Health**: Log each discovery separately
5. **All commands**: Add request correlation IDs
6. **All commands**: Add checkpoint logging

### Nice-to-Have (Implement Third)
7. **All commands**: Dry-run operation simulation logging
8. **All commands**: Performance metrics per operation
9. **Archive/Cleanup**: Undo/Rollback capability logging

---

## Part 5: Log Output Examples

### Archive Success with Detailed Logging
```json
{
  "timestamp": "2025-12-03T14:32:15.123Z",
  "level": "INFO",
  "logger": "roadmap.presentation.cli.issues.archive",
  "request_id": "a7f2k9m3",
  "operation": "issue_archive",
  "checkpoint": "file_search_complete",
  "issue_id": "8a00a17e",
  "search_pattern": "8a00a17e*.md",
  "search_path": ".roadmap/issues",
  "search_recursive": true,
  "files_found": 1,
  "file_path": ".roadmap/issues/v.0.6.0/8a00a17e-example.md",
  "duration_ms": 45
}
```

### Archive Failure with Recovery Suggestion
```json
{
  "timestamp": "2025-12-03T14:33:22.456Z",
  "level": "ERROR",
  "logger": "roadmap.presentation.cli.issues.archive",
  "request_id": "b8g3l9p4",
  "operation": "issue_archive",
  "error_type": "FileNotFoundError",
  "issue_id": "8a00a17e",
  "file_path_attempted": ".roadmap/issues/8a00a17e*.md",
  "classification": "system_error",
  "suggested_action": "verify_issue_exists",
  "recovery_hint": "Try: roadmap issue list | grep 8a00a17e"
}
```

### Cleanup with Conversion Tracking
```json
{
  "timestamp": "2025-12-03T14:35:48.789Z",
  "level": "INFO",
  "logger": "roadmap.presentation.cli.cleanup",
  "request_id": "c9h4m0q5",
  "operation": "cleanup_fix_malformed",
  "file_path": ".roadmap/issues/v.0.4.0/example.md",
  "conversions": [
    {
      "field": "git_commits",
      "conversion": "str_to_dict",
      "count": 3,
      "samples": ["abc1234e", "def5678f"]
    }
  ],
  "write_status": "success",
  "duration_ms": 125
}
```

---

## Part 6: Testing Error Scenarios

### Archive Testing Checklist
- [ ] File not found (missing issue file)
- [ ] File in wrong location (should use rglob)
- [ ] Directory creation fails (permission denied)
- [ ] Database marking fails (while file was moved)
- [ ] Partial batch failure (some items succeed, others fail)

### Cleanup Testing Checklist
- [ ] YAML parse error (malformed frontmatter)
- [ ] File not readable (permission denied)
- [ ] File not writable (permission denied)
- [ ] Type conversion edge cases
- [ ] Dry-run mode verification

### Health Testing Checklist
- [ ] Concurrent file modifications
- [ ] Unreadable files
- [ ] Missing files during iteration
- [ ] Deep folder structure

### Init Testing Checklist
- [ ] Lock already exists (concurrent init)
- [ ] Directory already exists (force/no-force)
- [ ] Permission denied on directory creation
- [ ] Rollback on partial failure

---

## Conclusion

By implementing this logging strategy, we'll transform these critical commands from producing error messages to producing comprehensive diagnostic data that enables:

1. **Real-time debugging**: Understanding exactly what failed and why
2. **User support**: Providing clear recovery steps
3. **Operations monitoring**: Tracking success rates and performance
4. **Root cause analysis**: Understanding failure patterns
5. **Continuous improvement**: Data-driven enhancements

The key principle: **Every operation that can fail should log before and after that operation**, capturing enough context for debugging without overwhelming the logs.
