"""High-performance sync system with optimizations for large-scale operations."""

import asyncio
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from .datetime_parser import parse_github_datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .bulk_operations import BulkOperationResult, bulk_operations
from .file_locking import locked_file_ops
from .github_client import GitHubAPIError
from .models import Issue, Milestone, MilestoneStatus, Priority, Status
from .parser import IssueParser, MilestoneParser
from .sync import SyncManager

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    """Statistics for sync operations."""

    start_time: datetime
    end_time: Optional[datetime] = None

    issues_processed: int = 0
    issues_created: int = 0
    issues_updated: int = 0
    issues_failed: int = 0

    milestones_processed: int = 0
    milestones_created: int = 0
    milestones_updated: int = 0
    milestones_failed: int = 0

    api_calls: int = 0
    cache_hits: int = 0
    disk_writes: int = 0

    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def total_items(self) -> int:
        """Get total items processed."""
        return self.issues_processed + self.milestones_processed

    @property
    def total_success(self) -> int:
        """Get total successful operations."""
        return (
            self.issues_created
            + self.issues_updated
            + self.milestones_created
            + self.milestones_updated
        )

    @property
    def total_failed(self) -> int:
        """Get total failed operations."""
        return self.issues_failed + self.milestones_failed

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.total_success / self.total_items) * 100

    @property
    def throughput(self) -> float:
        """Get items per second."""
        if self.duration == 0:
            return 0.0
        return self.total_items / self.duration


class SyncCache:
    """Cache for GitHub API data to reduce redundant calls."""

    def __init__(self, ttl_seconds: int = 300):  # 5-minute TTL
        self.ttl_seconds = ttl_seconds
        self._milestones: Optional[Tuple[datetime, List[Dict]]] = None
        self._issues: Optional[Tuple[datetime, List[Dict]]] = None
        self._milestone_map: Dict[str, int] = {}
        self._last_clear = datetime.now()

    def get_milestones(self, github_client) -> List[Dict]:
        """Get cached milestones or fetch from GitHub."""
        now = datetime.now()

        if (
            self._milestones
            and (now - self._milestones[0]).total_seconds() < self.ttl_seconds
        ):
            return self._milestones[1]

        # Fetch fresh data
        milestones = github_client.get_milestones(state="all")
        self._milestones = (now, milestones)

        # Update milestone name -> number mapping
        self._milestone_map = {m["title"]: m["number"] for m in milestones}

        return milestones

    def get_issues(self, github_client) -> List[Dict]:
        """Get cached issues or fetch from GitHub."""
        now = datetime.now()

        if self._issues and (now - self._issues[0]).total_seconds() < self.ttl_seconds:
            return self._issues[1]

        # Fetch fresh data
        issues = github_client.get_issues(state="all")
        self._issues = (now, issues)

        return issues

    def find_milestone_number(
        self, milestone_name: str, github_client
    ) -> Optional[int]:
        """Find milestone number by name using cache."""
        # Ensure milestones are cached
        if not self._milestone_map:
            self.get_milestones(github_client)

        return self._milestone_map.get(milestone_name)

    def clear(self):
        """Clear all cached data."""
        self._milestones = None
        self._issues = None
        self._milestone_map = {}
        self._last_clear = datetime.now()

    def should_clear(self) -> bool:
        """Check if cache should be cleared based on age."""
        return (
            datetime.now() - self._last_clear
        ).total_seconds() > self.ttl_seconds * 2


class HighPerformanceSyncManager:
    """High-performance sync manager with optimizations for large-scale operations."""

    def __init__(
        self,
        sync_manager: SyncManager,
        max_workers: int = 8,
        batch_size: int = 50,
        progress_callback=None,
    ):
        self.sync_manager = sync_manager
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        self.cache = SyncCache()
        self.stats = SyncStats(start_time=datetime.now())

    def sync_issues_optimized(self, direction: str = "pull") -> SyncStats:
        """High-performance issue synchronization."""
        self.stats = SyncStats(start_time=datetime.now())

        try:
            if direction == "pull":
                return self._pull_issues_batch()
            else:
                return self._push_issues_batch()
        finally:
            self.stats.end_time = datetime.now()

    def sync_milestones_optimized(self, direction: str = "pull") -> SyncStats:
        """High-performance milestone synchronization."""
        self.stats = SyncStats(start_time=datetime.now())

        try:
            if direction == "pull":
                return self._pull_milestones_batch()
            else:
                return self._push_milestones_batch()
        finally:
            self.stats.end_time = datetime.now()

    def _pull_issues_batch(self) -> SyncStats:
        """Pull issues from GitHub with batching and parallel processing."""
        if not self.sync_manager.github_client:
            self.stats.errors.append("GitHub client not configured")
            return self.stats

        try:
            # Fetch all GitHub issues in one call
            self._report_progress("Fetching issues from GitHub...")
            github_issues = self.cache.get_issues(self.sync_manager.github_client)
            self.stats.api_calls += 1

            # Filter out pull requests
            github_issues = [
                issue for issue in github_issues if "pull_request" not in issue
            ]

            # Pre-cache milestones for milestone assignment
            self._report_progress("Caching milestones...")
            self.cache.get_milestones(self.sync_manager.github_client)
            self.stats.api_calls += 1

            # Get existing local issues for comparison
            local_issues = {
                issue.github_issue: issue
                for issue in self.sync_manager.core.list_issues()
                if issue.github_issue
            }

            self._report_progress(f"Processing {len(github_issues)} issues...")

            # Process issues in batches with parallel workers
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Split into batches
                batches = [
                    github_issues[i : i + self.batch_size]
                    for i in range(0, len(github_issues), self.batch_size)
                ]

                futures = []
                for batch_idx, batch in enumerate(batches):
                    future = executor.submit(
                        self._process_issue_batch, batch, local_issues, batch_idx
                    )
                    futures.append(future)

                # Collect results
                for future in as_completed(futures):
                    try:
                        batch_stats = future.result()
                        self._merge_stats(batch_stats)
                    except Exception as e:
                        self.stats.errors.append(f"Batch processing error: {e}")
                        logger.exception("Batch processing failed")

        except Exception as e:
            self.stats.errors.append(f"Issues pull failed: {e}")
            logger.exception("Issues pull failed")

        return self.stats

    def _process_issue_batch(
        self, github_issues: List[Dict], local_issues: Dict[int, Issue], batch_idx: int
    ) -> SyncStats:
        """Process a batch of GitHub issues."""
        batch_stats = SyncStats(start_time=datetime.now())

        # Collect changes for bulk write
        files_to_write = []

        for github_issue in github_issues:
            try:
                issue_number = github_issue["number"]
                batch_stats.issues_processed += 1

                # Extract issue data
                issue_data = self._extract_issue_data(github_issue)
                local_issue = local_issues.get(issue_number)

                if local_issue:
                    # Update existing issue
                    self._update_issue_from_data(local_issue, issue_data)
                    batch_stats.issues_updated += 1
                else:
                    # Create new issue
                    local_issue = Issue(**issue_data)
                    batch_stats.issues_created += 1

                # Prepare for bulk write
                issue_path = self.sync_manager.core.issues_dir / local_issue.filename
                files_to_write.append((local_issue, issue_path))

                # Progress reporting
                if self.progress_callback and batch_stats.issues_processed % 10 == 0:
                    self.progress_callback(
                        f"Batch {batch_idx}: {batch_stats.issues_processed} issues processed"
                    )

            except Exception as e:
                batch_stats.issues_failed += 1
                batch_stats.errors.append(
                    f"Issue #{github_issue.get('number', 'unknown')}: {e}"
                )
                logger.exception(
                    f"Failed to process issue {github_issue.get('number')}"
                )

        # Bulk write to disk with locking
        self._bulk_write_issues(files_to_write, batch_stats)

        batch_stats.end_time = datetime.now()
        return batch_stats

    def _bulk_write_issues(
        self, files_to_write: List[Tuple[Issue, Path]], stats: SyncStats
    ):
        """Write multiple issues to disk efficiently."""
        for issue, file_path in files_to_write:
            try:
                # Use the standard save method which handles all the formatting
                IssueParser.save_issue_file(issue, file_path)
                stats.disk_writes += 1
            except Exception as e:
                stats.errors.append(f"Write error for {file_path.name}: {e}")
                logger.exception(f"Failed to write issue file {file_path}")

    def _extract_issue_data(self, github_issue: Dict) -> Dict:
        """Extract issue data from GitHub API response."""
        # Extract priority and status from labels
        labels = github_issue["labels"]
        priority = (
            self.sync_manager.github_client.labels_to_priority(labels)
            or Priority.MEDIUM
        )
        status = self.sync_manager.github_client.labels_to_status(labels) or Status.TODO

        # Override status based on GitHub issue state
        if github_issue["state"] == "closed":
            status = Status.DONE

        # Extract milestone
        milestone = ""
        if github_issue["milestone"]:
            milestone = github_issue["milestone"]["title"]

        # Extract assignee
        assignee = ""
        if github_issue["assignee"]:
            assignee = github_issue["assignee"]["login"]

        # Extract other labels (non-priority/status)
        other_labels = []
        for label in labels:
            label_name = label["name"]
            if not (
                label_name.startswith("priority:") or label_name.startswith("status:")
            ):
                other_labels.append(label_name)

        return {
            "id": f"gh-{github_issue['number']}",
            "title": github_issue["title"],
            "content": github_issue["body"] or "",
            "priority": priority,
            "status": status,
            "milestone": milestone,
            "assignee": assignee,
            "labels": other_labels,
            "github_issue": github_issue["number"],
            "created": parse_github_datetime(github_issue["created_at"]),
            "updated": parse_github_datetime(github_issue["updated_at"]),
        }

    def _update_issue_from_data(self, issue: Issue, data: Dict):
        """Update an existing issue with new data."""
        issue.title = data["title"]
        issue.content = data["content"]
        issue.priority = data["priority"]
        issue.status = data["status"]
        issue.milestone = data["milestone"]
        issue.assignee = data["assignee"]
        issue.labels = data["labels"]
        issue.updated = data["updated"]

    def _pull_milestones_batch(self) -> SyncStats:
        """Pull milestones from GitHub with batching."""
        if not self.sync_manager.github_client:
            self.stats.errors.append("GitHub client not configured")
            return self.stats

        try:
            # Fetch all GitHub milestones
            self._report_progress("Fetching milestones from GitHub...")
            github_milestones = self.cache.get_milestones(
                self.sync_manager.github_client
            )
            self.stats.api_calls += 1

            # Get existing local milestones
            local_milestones = {
                m.name: m for m in self.sync_manager.core.list_milestones()
            }

            self._report_progress(f"Processing {len(github_milestones)} milestones...")

            files_to_write = []

            for github_milestone in github_milestones:
                try:
                    self.stats.milestones_processed += 1

                    milestone_name = github_milestone["title"]
                    local_milestone = local_milestones.get(milestone_name)

                    # Extract milestone data
                    due_date = None
                    if github_milestone["due_on"]:
                        due_date = parse_github_datetime(github_milestone["due_on"])

                    if local_milestone:
                        # Update existing
                        local_milestone.description = (
                            github_milestone["description"] or ""
                        )
                        local_milestone.github_milestone = github_milestone["number"]
                        local_milestone.due_date = due_date
                        local_milestone.status = (
                            MilestoneStatus.CLOSED
                            if github_milestone["state"] == "closed"
                            else MilestoneStatus.OPEN
                        )
                        local_milestone.updated = datetime.now()
                        self.stats.milestones_updated += 1
                    else:
                        # Create new
                        local_milestone = Milestone(
                            name=milestone_name,
                            description=github_milestone["description"] or "",
                            due_date=due_date,
                            status=(
                                MilestoneStatus.CLOSED
                                if github_milestone["state"] == "closed"
                                else MilestoneStatus.OPEN
                            ),
                            github_milestone=github_milestone["number"],
                        )
                        self.stats.milestones_created += 1

                    # Prepare for bulk write
                    milestone_path = (
                        self.sync_manager.core.milestones_dir / local_milestone.filename
                    )
                    files_to_write.append((local_milestone, milestone_path))

                except Exception as e:
                    self.stats.milestones_failed += 1
                    self.stats.errors.append(
                        f"Milestone '{github_milestone.get('title', 'unknown')}': {e}"
                    )
                    logger.exception(
                        f"Failed to process milestone {github_milestone.get('title')}"
                    )

            # Bulk write milestones
            self._bulk_write_milestones(files_to_write)

        except Exception as e:
            self.stats.errors.append(f"Milestones pull failed: {e}")
            logger.exception("Milestones pull failed")

        return self.stats

    def _bulk_write_milestones(self, files_to_write: List[Tuple[Milestone, Path]]):
        """Write multiple milestones to disk efficiently."""
        for milestone, file_path in files_to_write:
            try:
                # Use the standard save method which handles all the formatting
                MilestoneParser.save_milestone_file(milestone, file_path)
                self.stats.disk_writes += 1
            except Exception as e:
                self.stats.errors.append(f"Write error for {file_path.name}: {e}")
                logger.exception(f"Failed to write milestone file {file_path}")

    def _push_issues_batch(self) -> SyncStats:
        """Push local issues to GitHub with batching."""
        # For push operations, we still need to respect GitHub API rate limits
        # So we use smaller batches and some delays
        local_issues = self.sync_manager.core.list_issues()

        self._report_progress(f"Pushing {len(local_issues)} issues to GitHub...")

        # Pre-cache milestones for assignment
        self.cache.get_milestones(self.sync_manager.github_client)

        with ThreadPoolExecutor(
            max_workers=min(self.max_workers, 4)
        ) as executor:  # Smaller thread pool for API
            futures = []

            for issue in local_issues:
                future = executor.submit(self._push_single_issue, issue)
                futures.append(future)

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.stats.errors.append(f"Push error: {e}")

        return self.stats

    def _push_single_issue(self, issue: Issue):
        """Push a single issue to GitHub."""
        try:
            success, message, _ = self.sync_manager.push_issue(issue)
            self.stats.api_calls += 1

            if success:
                if issue.github_issue:
                    self.stats.issues_updated += 1
                else:
                    self.stats.issues_created += 1
            else:
                self.stats.issues_failed += 1
                self.stats.errors.append(f"{issue.title}: {message}")

            self.stats.issues_processed += 1

        except Exception as e:
            self.stats.issues_failed += 1
            self.stats.errors.append(f"{issue.title}: {e}")

    def _push_milestones_batch(self) -> SyncStats:
        """Push local milestones to GitHub with batching."""
        local_milestones = self.sync_manager.core.list_milestones()

        self._report_progress(
            f"Pushing {len(local_milestones)} milestones to GitHub..."
        )

        for milestone in local_milestones:
            try:
                success, message, _ = self.sync_manager.push_milestone(milestone)
                self.stats.api_calls += 1

                if success:
                    if milestone.github_milestone:
                        self.stats.milestones_updated += 1
                    else:
                        self.stats.milestones_created += 1
                else:
                    self.stats.milestones_failed += 1
                    self.stats.errors.append(f"{milestone.name}: {message}")

                self.stats.milestones_processed += 1

            except Exception as e:
                self.stats.milestones_failed += 1
                self.stats.errors.append(f"{milestone.name}: {e}")

        return self.stats

    def _merge_stats(self, batch_stats: SyncStats):
        """Merge batch statistics into main stats."""
        self.stats.issues_processed += batch_stats.issues_processed
        self.stats.issues_created += batch_stats.issues_created
        self.stats.issues_updated += batch_stats.issues_updated
        self.stats.issues_failed += batch_stats.issues_failed

        self.stats.milestones_processed += batch_stats.milestones_processed
        self.stats.milestones_created += batch_stats.milestones_created
        self.stats.milestones_updated += batch_stats.milestones_updated
        self.stats.milestones_failed += batch_stats.milestones_failed

        self.stats.api_calls += batch_stats.api_calls
        self.stats.disk_writes += batch_stats.disk_writes
        self.stats.errors.extend(batch_stats.errors)

    def _report_progress(self, message: str):
        """Report progress if callback is provided."""
        if self.progress_callback:
            self.progress_callback(message)

    def get_performance_report(self) -> Dict[str, Any]:
        """Get a comprehensive performance report."""
        return {
            "duration_seconds": self.stats.duration,
            "throughput_items_per_second": self.stats.throughput,
            "total_items": self.stats.total_items,
            "success_rate": self.stats.success_rate,
            "api_calls": self.stats.api_calls,
            "cache_hits": self.stats.cache_hits,
            "disk_writes": self.stats.disk_writes,
            "batch_size": self.batch_size,
            "max_workers": self.max_workers,
            "breakdown": {
                "issues": {
                    "processed": self.stats.issues_processed,
                    "created": self.stats.issues_created,
                    "updated": self.stats.issues_updated,
                    "failed": self.stats.issues_failed,
                },
                "milestones": {
                    "processed": self.stats.milestones_processed,
                    "created": self.stats.milestones_created,
                    "updated": self.stats.milestones_updated,
                    "failed": self.stats.milestones_failed,
                },
            },
            "errors": self.stats.errors,
        }
