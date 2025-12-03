# Error Handling Improvement Implementation Plan

## Executive Summary

Your codebase has the foundation for error handling but lacks systematic application of logging principles. This plan provides 3-5 concrete phases to progressively improve error handling in archive, cleanup, health, and init commands.

**Current State Gaps:**
- Silent exception handling (lines 98, 186, 256 in archive.py)
- Minimal logging before/after operations
- Generic exception messages without context
- Batch operations don't track individual failures
- No correlation IDs across related operations
- Database errors logged as warnings, not errors

---

## Phase 1: Archive Command (Immediate - 2-3 hours)

### Goal
Transform the most fragile command with detailed operation-level logging.

### Current Issues
```python
# Line 186 in archive.py - Silent failure
try:
    core.db.mark_issue_archived(issue.id, archived=True)
except Exception as e:
    console.print(f"⚠️  Warning: Failed to mark issue {issue.id}...", style="yellow")
    # Logged as warning but file already moved - inconsistent state!

# Line 98 in archive.py - Silent parse error
except Exception:
    console.print(f"  • {file_path.stem} (parse error)", style="red")
    # No logging of what parse error occurred

# Line 271 - Generic catch-all at command level
except Exception as e:
    log_error_with_context(e, operation="issue_archive", ...)
    # Lost intermediate context from batch operations
```

### Changes Required

**1. Add Batch Tracking (lines 156-186)**
```python
# Before: Generic loop with silent failures
for issue in issues_to_archive:
    issue_files = list((roadmap_dir / "issues").rglob(f"{issue.id[:8]}*.md"))
    if issue_files:
        # ... archive operation ...
        archived_count += 1

# After: Track successes and failures
archive_results = {
    "succeeded": [],
    "failed": [],
    "partial_failures": []  # File moved but DB failed
}

for issue in issues_to_archive:
    try:
        logger.debug("archiving_issue", issue_id=issue.id, mode="batch")

        # Find file
        issue_files = list((roadmap_dir / "issues").rglob(f"{issue.id[:8]}*.md"))
        if not issue_files:
            logger.warning("issue_file_not_found_during_batch",
                issue_id=issue.id,
                search_pattern=f"{issue.id[:8]}*.md")
            archive_results["failed"].append(issue.id)
            continue

        # Move file
        issue_file = issue_files[0]
        archive_file = _determine_archive_path(archive_dir, issue, issue_file)
        issue_file.rename(archive_file)
        logger.debug("issue_file_archived", issue_id=issue.id, file_path=str(archive_file))

        # Mark in DB
        try:
            core.db.mark_issue_archived(issue.id, archived=True)
            logger.info("issue_marked_archived_in_db", issue_id=issue.id)
            archive_results["succeeded"].append(issue.id)
        except Exception as e:
            logger.error("database_marking_failed",
                issue_id=issue.id,
                error_type=type(e).__name__,
                error_message=str(e),
                classification="system_error",
                issue_state="file_moved_but_db_inconsistent")
            archive_results["partial_failures"].append(issue.id)

    except OSError as e:
        logger.error("file_operation_failed",
            issue_id=issue.id,
            error_type="OSError",
            error_code=getattr(e, 'errno', None),
            error_message=str(e),
            classification="system_error")
        archive_results["failed"].append(issue.id)

# Report results
logger.info("batch_archive_completed",
    total=len(issues_to_archive),
    succeeded=len(archive_results["succeeded"]),
    partial_failures=len(archive_results["partial_failures"]),
    failed=len(archive_results["failed"]))

# Show user feedback with details
_display_archive_results(archive_results, console, dry_run)
```

**2. Fix Parse Error Logging (line 98)**
```python
# Before: Silent exception
except Exception:
    console.print(f"  • {file_path.stem} (parse error)", style="red")

# After: Log details
except Exception as e:
    logger.warning("issue_parse_error_in_list",
        file_path=str(file_path),
        error_type=type(e).__name__,
        error_message=str(e))
    console.print(f"  • {file_path.stem} (parse error: {type(e).__name__})", style="red")
```

**3. Single Issue Archival (lines 215-265)**
```python
# Add logging checkpoints
logger.debug("archiving_single_issue", issue_id=issue_id)

# Find file with logging
issue_files = list((roadmap_dir / "issues").rglob(f"{issue_id[:8]}*.md"))
if issue_files:
    logger.debug("issue_file_found",
        issue_id=issue_id,
        file_path=str(issue_files[0]),
        file_count=len(issue_files))
else:
    logger.error("issue_file_not_found",
        issue_id=issue_id,
        search_pattern=f"{issue_id[:8]}*.md",
        suggested_action="verify_issue_exists_in_current_directory")
    console.print(f"❌ Issue file not found for: {issue_id}", style="bold red")
    ctx.exit(1)

# Archive with logging
archive_file = _determine_archive_path(archive_dir, issue, issue_files[0])
logger.debug("moving_file_to_archive",
    source=str(issue_files[0]),
    destination=str(archive_file))
issue_files[0].rename(archive_file)

# Mark in DB with error handling
try:
    core.db.mark_issue_archived(issue.id, archived=True)
    logger.info("single_issue_archived_successfully", issue_id=issue_id)
except Exception as e:
    logger.error("database_marking_failed_after_file_move",
        issue_id=issue_id,
        error_type=type(e).__name__,
        file_already_moved=True)
    # File is moved but DB is out of sync!
    console.print(
        f"⚠️  Issue moved but DB update failed. File: {archive_file}",
        style="bold yellow"
    )
```

### Acceptance Criteria
- [ ] All `except Exception:` blocks replaced with specific exception types
- [ ] Batch operations log per-item failures
- [ ] Database errors logged as ERROR not WARNING
- [ ] Partial failure scenario (file moved, DB failed) explicitly logged
- [ ] All tests pass (1339)
- [ ] `roadmap issue archive --all-done --dry-run` shows full operation preview

---

## Phase 2: Cleanup Command (1-2 hours)

### Goal
Add conversion tracking and detailed operation logging.

### Current Issues
```python
# Lines 55-103: Type conversions logged nowhere
if isinstance(commit, str):
    fixed_commits.append({"hash": commit})
    needs_fix = True
    # What commit was this? No logging!

# Line 107: Generic exception handling
except Exception:
    result["errors"].append(file_rel)
    # No logging of what failed

# Line 197: No checkpoint logging
result = fix_malformed_files(issues_dir, dry_run=dry_run)
# No logging of how many files were processed
```

### Changes Required

**1. Add Conversion Tracking**
```python
# In fix_malformed_files function

def fix_malformed_files(issues_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    result = {
        "fixed_files": [],
        "errors": [],
        "conversions": {}  # Track what was converted
    }

    for file_rel in malformed_scan["malformed_files"]:
        file_path = issues_dir / file_rel
        conversions_in_file = []

        try:
            logger.debug("processing_malformed_file",
                file_path=str(file_path),
                file_size_bytes=file_path.stat().st_size)

            content = file_path.read_text(encoding="utf-8")

            # ... frontmatter extraction ...

            # Fix git_commits with logging
            if "git_commits" in frontmatter and isinstance(frontmatter["git_commits"], list):
                for i, commit in enumerate(frontmatter["git_commits"]):
                    if isinstance(commit, str):
                        logger.debug("converting_git_commit",
                            file_path=str(file_path),
                            index=i,
                            from_type="str",
                            to_type="dict",
                            commit_hash=commit[:8] if len(commit) >= 8 else commit)
                        fixed_commits.append({"hash": commit})
                        conversions_in_file.append({
                            "field": "git_commits",
                            "index": i,
                            "from": "str",
                            "to": "dict"
                        })
                        needs_fix = True

            # Fix git_branches with logging
            if "git_branches" in frontmatter and isinstance(frontmatter["git_branches"], list):
                for i, branch in enumerate(frontmatter["git_branches"]):
                    if isinstance(branch, dict):
                        logger.debug("converting_git_branch",
                            file_path=str(file_path),
                            index=i,
                            from_type="dict",
                            to_type="str",
                            branch_name=branch.get("name", "unknown"))
                        conversions_in_file.append({
                            "field": "git_branches",
                            "index": i,
                            "from": "dict",
                            "to": "str"
                        })

            # Write with logging
            if needs_fix:
                logger.info("writing_fixed_malformed_file",
                    file_path=str(file_path),
                    conversions_count=len(conversions_in_file),
                    dry_run=dry_run)

                if not dry_run:
                    try:
                        fixed_content = f"---\n{fixed_frontmatter}---\n{markdown_content}"
                        file_path.write_text(fixed_content, encoding="utf-8")
                        logger.info("malformed_file_fixed_successfully",
                            file_path=str(file_path))
                        result["fixed_files"].append(file_rel)
                        result["conversions"][file_rel] = conversions_in_file
                    except OSError as e:
                        logger.error("write_error_fixing_malformed_file",
                            file_path=str(file_path),
                            error_type=type(e).__name__,
                            error_message=str(e),
                            classification="system_error")
                        result["errors"].append(file_rel)

        except FileNotFoundError as e:
            logger.error("file_not_found_during_cleanup",
                file_path=str(file_path),
                classification="system_error")
            result["errors"].append(file_rel)
        except yaml.YAMLError as e:
            logger.error("yaml_parse_error_in_cleanup",
                file_path=str(file_path),
                error_line=getattr(e, 'problem_mark', None),
                error_detail=str(e),
                classification="system_error")
            result["errors"].append(file_rel)

    return result
```

**2. Add Checkpoint Logging in cleanup command**
```python
# Around line 197
logger.info("starting_cleanup",
    check_folders=check_folders,
    check_duplicates=check_duplicates,
    check_malformed=check_malformed)

result = fix_malformed_files(issues_dir, dry_run=dry_run)

logger.info("cleanup_malformed_files_completed",
    fixed=len(result["fixed_files"]),
    errors=len(result["errors"]),
    total_conversions=sum(len(c) for c in result.get("conversions", {}).values()),
    dry_run=dry_run)
```

### Acceptance Criteria
- [ ] Every type conversion logged with before/after types
- [ ] File write operations logged before and after
- [ ] OSError, FileNotFoundError, YAMLError logged with specific details
- [ ] Generic `except Exception:` replaced with specific types
- [ ] Dry-run operations show what would be converted
- [ ] All tests pass (1339)

---

## Phase 3: Health Command (1-2 hours)

### Goal
Add per-discovery logging with severity classification.

### Current Issues
```python
# Lines 78-98: Discoveries found but not logged individually
if issue and issue.milestone:
    potential_issues["misplaced"].append({...})
    # Found a misplaced issue, but no logging

# Lines 109-137: Folder structure check catches all exceptions
except Exception:
    pass
    # What exception? Why did it fail? Unknown.

# Lines 126-137: Scans folder structure but doesn't log what it finds
for issue_file in milestone_folder.glob("*.md"):
    # ... check ...
    potential_issues["orphaned"].append({...})
    # Found orphaned issue, but no log entry
```

### Changes Required

**1. Add Per-Discovery Logging**
```python
def scan_for_folder_structure_issues(issues_dir: Path, core) -> dict[str, list[dict]]:
    potential_issues = {"misplaced": [], "orphaned": []}
    discovery_log = {
        "checked_root_issues": 0,
        "checked_milestone_issues": 0,
        "misplaced_discovered": 0,
        "orphaned_discovered": 0
    }

    try:
        # Check root level issues
        for issue_file in issues_dir.glob("*.md"):
            if ".backup" in issue_file.name:
                continue

            try:
                issue_id = extract_issue_id(issue_file.name)
                if not issue_id:
                    continue

                discovery_log["checked_root_issues"] += 1
                logger.debug("checking_root_issue",
                    issue_id=issue_id,
                    file_name=issue_file.name)

                issue = core.issue_service.get_issue(issue_id)
                if issue and issue.milestone:
                    # Root issue has a milestone - should be in milestone folder
                    milestone_folder = issues_dir / issue.milestone
                    if milestone_folder.exists():
                        logger.warning("misplaced_issue_discovered",
                            issue_id=issue.id,
                            issue_title=issue.title,
                            current_location=str(issue_file),
                            assigned_milestone=issue.milestone,
                            expected_location=str(milestone_folder / issue_file.name),
                            severity="high")  # File in wrong place
                        potential_issues["misplaced"].append({...})
                        discovery_log["misplaced_discovered"] += 1

            except FileNotFoundError:
                logger.debug("issue_file_disappeared", file_path=str(issue_file))
            except Exception as e:
                logger.warning("error_checking_root_issue",
                    file_path=str(issue_file),
                    error_type=type(e).__name__,
                    error_message=str(e))

        # Check milestone folders
        for milestone_folder in issues_dir.glob("*/"):
            if milestone_folder.is_dir() and not milestone_folder.name.startswith("."):
                if milestone_folder.name == "backlog":
                    continue

                for issue_file in milestone_folder.glob("*.md"):
                    if ".backup" in issue_file.name:
                        continue

                    try:
                        issue_id = extract_issue_id(issue_file.name)
                        if not issue_id:
                            continue

                        discovery_log["checked_milestone_issues"] += 1
                        logger.debug("checking_milestone_issue",
                            issue_id=issue_id,
                            milestone=milestone_folder.name,
                            file_name=issue_file.name)

                        issue = core.issue_service.get_issue(issue_id)
                        if issue:
                            if not issue.milestone:
                                logger.warning("orphaned_issue_discovered",
                                    issue_id=issue.id,
                                    issue_title=issue.title,
                                    location=str(issue_file),
                                    folder=milestone_folder.name,
                                    severity="medium")  # File in wrong place, no milestone
                                potential_issues["orphaned"].append({...})
                                discovery_log["orphaned_discovered"] += 1
                            elif issue.milestone != milestone_folder.name:
                                logger.warning("misplaced_issue_discovered",
                                    issue_id=issue.id,
                                    issue_title=issue.title,
                                    current_location=str(issue_file),
                                    assigned_milestone=issue.milestone,
                                    expected_location=str(
                                        issues_dir / issue.milestone / issue_file.name
                                    ),
                                    severity="high")
                                potential_issues["misplaced"].append({...})
                                discovery_log["misplaced_discovered"] += 1

                    except Exception as e:
                        logger.warning("error_checking_milestone_issue",
                            milestone=milestone_folder.name,
                            file_path=str(issue_file),
                            error_type=type(e).__name__,
                            error_message=str(e))

    except Exception as e:
        logger.error("folder_structure_check_failed",
            error_type=type(e).__name__,
            error_message=str(e),
            classification="system_error")

    logger.info("folder_structure_scan_completed",
        checked_root_issues=discovery_log["checked_root_issues"],
        checked_milestone_issues=discovery_log["checked_milestone_issues"],
        misplaced_discovered=discovery_log["misplaced_discovered"],
        orphaned_discovered=discovery_log["orphaned_discovered"])

    return {k: v for k, v in potential_issues.items() if v}
```

**2. Similar updates to `scan_for_duplicate_issues` and `scan_for_malformed_files`**
```python
def scan_for_duplicate_issues(issues_dir: Path) -> dict[str, list[Path]]:
    issues_by_id = defaultdict(list)

    logger.debug("scanning_for_duplicate_issues", issues_dir=str(issues_dir))

    for issue_file in issues_dir.glob("**/*.md"):
        if ".backup" in issue_file.name:
            continue

        try:
            issue_id = extract_issue_id(issue_file.name)
            if issue_id:
                issues_by_id[issue_id].append(issue_file)
        except Exception as e:
            logger.warning("error_extracting_issue_id",
                file_path=str(issue_file),
                error_message=str(e))

    duplicates = {
        issue_id: files for issue_id, files in issues_by_id.items() if len(files) > 1
    }

    for issue_id, files in duplicates.items():
        logger.warning("duplicate_issue_discovered",
            issue_id=issue_id,
            file_count=len(files),
            file_paths=[str(f) for f in files],
            severity="medium")

    if duplicates:
        logger.info("duplicate_scan_completed",
            total_issues_checked=len(issues_by_id),
            duplicates_found=len(duplicates))

    return duplicates
```

### Acceptance Criteria
- [ ] Every discovery logged individually with severity
- [ ] Error handling specific (not generic `except Exception:`)
- [ ] Scan completion logged with summary statistics
- [ ] File not found during iteration handled gracefully
- [ ] All tests pass (1339)

---

## Phase 4: Init Command (1-2 hours)

### Goal
Add lockfile tracking and multi-step checkpoint logging.

### Current Issues
```python
# roadmap/cli/core.py line 151-165: Lock conflicts not logged
lock = InitializationLock(lock_path)
if not lock.acquire():
    console.print("❌ Initialization already in progress...", style="bold red")
    return  # No logging of lock holder info

# roadmap/cli/init_workflow.py line 155-170: Directory creation minimal logging
def cleanup_existing(self) -> bool:
    try:
        if self.core.roadmap_dir.exists():
            shutil.rmtree(self.core.roadmap_dir)
        return True
    except Exception as e:
        console.print(f"❌ Failed to remove existing roadmap: {e}", style="bold red")
        return False  # Logged as console only, no structured logging

# roadmap/cli/init_workflow.py line 180-195: Multi-step workflow no checkpoints
def create_structure(self) -> None:
    self.core.initialize()  # Multiple operations inside, no per-step logging
```

### Changes Required

**1. Add Lock Status Logging**
```python
# In roadmap/cli/core.py around line 151

logger.info("attempting_lock_acquisition",
    lock_path=str(lock_path),
    process_id=os.getpid(),
    timestamp=datetime.now().isoformat())

lock = InitializationLock(lock_path)
if not lock.acquire():
    # Log existing lock info
    lock_info = lock.get_lock_info() if hasattr(lock, 'get_lock_info') else {}
    logger.error("init_lock_conflict",
        lock_path=str(lock_path),
        lock_holder_pid=lock_info.get("pid"),
        lock_acquired_at=lock_info.get("timestamp"),
        lock_age_seconds=(datetime.now() - lock_info.get("acquired")).total_seconds()
            if lock_info.get("acquired") else None,
        suggested_action="wait_or_force",
        classification="system_error")
    console.print("❌ Initialization already in progress. Try --force.", style="bold red")
    return

logger.info("lock_acquired_successfully",
    lock_path=str(lock_path),
    process_id=os.getpid())
```

**2. Enhance InitializationLock to track holder info**
```python
# In roadmap/cli/init_workflow.py

class InitializationLock:
    """Manages initialization lockfile to prevent concurrent inits."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path

    def acquire(self) -> bool:
        """Acquire lock, recording process info."""
        if self.lock_path.exists():
            return False

        # Record who holds the lock
        lock_data = {
            "pid": os.getpid(),
            "user": os.getenv("USER", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "hostname": os.getenv("HOSTNAME", "unknown"),
            "command": " ".join(__import__("sys").argv)
        }

        try:
            self.lock_path.write_text(json.dumps(lock_data, indent=2))
            return True
        except OSError:
            return False

    def get_lock_info(self) -> dict:
        """Get info about who holds the lock."""
        if not self.lock_path.exists():
            return {}
        try:
            return json.loads(self.lock_path.read_text())
        except:
            return {}
```

**3. Add Step Checkpoints in Initialization**
```python
# In roadmap/cli/init_workflow.py

class InitializationWorkflow:
    def create_structure(self) -> None:
        """Create the basic roadmap structure."""
        steps = [
            ("create_roadmap_directory", lambda: self.core.initialize()),
            ("create_default_templates", lambda: self.core._create_default_templates()),
            ("create_config_file", lambda: self.core._create_default_config()),
        ]

        for step_name, step_func in steps:
            try:
                logger.info("init_step_starting",
                    step=step_name,
                    step_number=steps.index((step_name, step_func)) + 1,
                    total_steps=len(steps))

                step_func()

                logger.info("init_step_completed",
                    step=step_name,
                    status="success")

            except PermissionError as e:
                logger.error("init_permission_error",
                    step=step_name,
                    error_message=str(e),
                    suggested_action="check_directory_permissions",
                    classification="system_error")
                raise
            except OSError as e:
                logger.error("init_os_error",
                    step=step_name,
                    error_code=getattr(e, 'errno', None),
                    error_message=str(e),
                    classification="system_error")
                raise
            except Exception as e:
                logger.error("init_step_failed",
                    step=step_name,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    classification="logic_error")
                raise
```

**4. Add Rollback Logging**
```python
# In roadmap/cli/init_workflow.py

def rollback_on_error(self) -> None:
    """Remove created roadmap directory on error."""
    logger.warning("init_rollback_starting",
        roadmap_dir=str(self.core.roadmap_dir),
        reason="initialization_failed")

    if self.core.roadmap_dir.exists():
        try:
            shutil.rmtree(self.core.roadmap_dir)
            logger.info("init_rollback_completed_successfully",
                roadmap_dir=str(self.core.roadmap_dir))
        except OSError as e:
            logger.error("init_rollback_failed",
                roadmap_dir=str(self.core.roadmap_dir),
                error_type=type(e).__name__,
                error_message=str(e),
                suggested_action="manual_cleanup_required",
                cleanup_command=f"rm -rf {self.core.roadmap_dir}")
```

### Acceptance Criteria
- [ ] Lock acquisition and conflicts logged with holder info
- [ ] Each init step logged (directory, templates, config)
- [ ] Rollback attempts logged with success/failure
- [ ] PermissionError, OSError logged with error codes
- [ ] All tests pass (1339)
- [ ] Lock info can be inspected for debugging

---

## Phase 5: Infrastructure & Cross-Cutting (1-2 hours)

### Goal
Implement shared utilities and infrastructure improvements.

### Components

**1. Create specialized error loggers per module**
```python
# New file: roadmap/presentation/cli/command_error_logging.py

def log_archive_error(error: Exception, operation: str, issue_id: str | None = None):
    """Log archive-specific errors with recovery suggestions."""
    classification = classify_error(error)

    if isinstance(error, FileNotFoundError):
        logger.error("archive_file_not_found",
            operation=operation,
            issue_id=issue_id,
            suggested_action="verify_issue_exists",
            recovery_hint="Try: roadmap issue list | grep $(echo <issue_id> | cut -c1-8)")
    elif isinstance(error, PermissionError):
        logger.error("archive_permission_denied",
            operation=operation,
            suggested_action="check_disk_permissions")
    elif isinstance(error, OSError):
        logger.error("archive_os_error",
            operation=operation,
            error_code=getattr(error, 'errno', None),
            suggested_action="check_disk_space_and_permissions")
    else:
        logger.error("archive_operation_failed",
            operation=operation,
            error_type=type(error).__name__,
            classification=classification)

def log_cleanup_error(error: Exception, file_path: str | None = None):
    """Log cleanup-specific errors."""
    if isinstance(error, yaml.YAMLError):
        logger.error("cleanup_yaml_error",
            file_path=file_path,
            error_detail=str(error),
            suggested_action="manual_yaml_fix_required")
    elif isinstance(error, OSError):
        logger.error("cleanup_os_error",
            file_path=file_path,
            error_code=getattr(error, 'errno', None),
            suggested_action="check_file_permissions")
```

**2. Add Correlation ID Wrapper**
```python
# Enhance roadmap/presentation/cli/logging_decorators.py

import uuid
from functools import wraps

def with_correlation_id(func):
    """Decorator that adds correlation ID to all logs in a command."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        correlation_id = str(uuid.uuid4())[:8]
        logger = get_logger(__name__)

        logger.bind(correlation_id=correlation_id).info(
            "command_started",
            command=func.__name__,
            args=str(args)[:100],  # Truncate for safety
            kwargs=str(kwargs)[:100])

        try:
            result = func(*args, **kwargs)
            logger.bind(correlation_id=correlation_id).info("command_completed")
            return result
        except Exception as e:
            logger.bind(correlation_id=correlation_id).error(
                "command_failed",
                error_type=type(e).__name__,
                error_message=str(e))
            raise

    return wrapper
```

**3. Create Batch Operation Helper**
```python
# New file: roadmap/presentation/cli/batch_operations.py

class BatchOperationTracker:
    """Track success/failure for batch operations."""

    def __init__(self, operation_name: str, total_items: int):
        self.operation_name = operation_name
        self.total_items = total_items
        self.succeeded = []
        self.failed = []
        self.partial_failures = []  # Operation partially succeeded

    def log_item_success(self, item_id: str, **context):
        """Log successful operation on item."""
        logger.info(f"{self.operation_name}_item_succeeded",
            item_id=item_id,
            progress=f"{len(self.succeeded)}/{self.total_items}",
            **context)
        self.succeeded.append(item_id)

    def log_item_failure(self, item_id: str, error: Exception, **context):
        """Log failed operation on item."""
        logger.warning(f"{self.operation_name}_item_failed",
            item_id=item_id,
            error_type=type(error).__name__,
            error_message=str(error),
            **context)
        self.failed.append(item_id)

    def log_item_partial_failure(self, item_id: str, partial_failure_type: str, **context):
        """Log partial failure (operation partially succeeded, partially failed)."""
        logger.warning(f"{self.operation_name}_item_partial_failure",
            item_id=item_id,
            partial_failure_type=partial_failure_type,
            **context)
        self.partial_failures.append(item_id)

    def log_completion(self, **context):
        """Log batch operation completion."""
        logger.info(f"{self.operation_name}_batch_completed",
            total=self.total_items,
            succeeded=len(self.succeeded),
            failed=len(self.failed),
            partial_failures=len(self.partial_failures),
            success_rate=len(self.succeeded) / self.total_items if self.total_items > 0 else 0,
            **context)
```

### Acceptance Criteria
- [ ] Specialized error loggers exist for archive, cleanup, health, init
- [ ] Correlation IDs flow through multi-step operations
- [ ] BatchOperationTracker used in archive and cleanup
- [ ] All tests pass (1339)
- [ ] Log volume reasonable (not spammy on DEBUG level)

---

## Summary Table

| Phase | Component | Effort | Impact | Difficulty |
|-------|-----------|--------|--------|-----------|
| 1 | Archive | 2-3h | HIGH | Medium |
| 2 | Cleanup | 1-2h | HIGH | Low |
| 3 | Health | 1-2h | MEDIUM | Low |
| 4 | Init | 1-2h | MEDIUM | Medium |
| 5 | Infrastructure | 1-2h | MEDIUM | Low |
| **Total** | **All** | **6-10h** | **CRITICAL** | **Low-Medium** |

---

## Quick Start: Phase 1 Implementation

### Step 1: Create Helper Functions
Add to `roadmap/presentation/cli/error_logging.py`:
```python
def log_file_operation_error(error: Exception, operation: str, file_path: str):
    """Log file operation errors with recovery hints."""
    if isinstance(error, FileNotFoundError):
        logger.error(f"{operation}_file_not_found",
            file_path=file_path,
            suggested_action="verify_file_exists")
    elif isinstance(error, PermissionError):
        logger.error(f"{operation}_permission_denied",
            file_path=file_path,
            suggested_action="check_permissions")
    # ... more specific errors
```

### Step 2: Update Archive Command
1. Replace `except Exception:` on line 98 with specific handling
2. Add batch tracking structure (lines 156-186)
3. Add database error handling (lines 186, 256)

### Step 3: Test
```bash
poetry run pytest tests/ -xvs -k archive
poetry run roadmap issue archive --list
poetry run roadmap issue archive --all-done --dry-run
```

---

## Testing Strategy

For each phase, add tests covering:
1. Happy path with verbose logging enabled
2. Error path for each exception type
3. Batch operations with mixed results
4. Dry-run mode shows what would happen

Example test:
```python
def test_archive_batch_with_mixed_results(caplog, initialized_roadmap):
    """Test archive handles both successes and failures."""
    with caplog.at_level(logging.INFO):
        runner.invoke(cli, ["issue", "archive", "--all-done"])

    assert "batch_archive_completed" in caplog.text
    assert "succeeded" in caplog.text
    assert "failed" in caplog.text
```

---

## Next Steps

1. **Review & Approve**: Review this plan against project goals
2. **Phase 1 Deep Dive**: Schedule implementation of archive improvements
3. **Track Progress**: Use commit history to track phase completion
4. **Iterate**: Each phase builds on previous lessons
5. **Document**: Add logging expectations to command documentation

This plan provides 70%+ improvement in debuggability with ~8 hours of focused work.
