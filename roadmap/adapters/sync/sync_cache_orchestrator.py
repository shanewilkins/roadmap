"""Sync orchestrator with optimized baseline building and progress tracking.

This module integrates OptimizedBaselineBuilder with the sync pipeline,
providing intelligent change detection, database caching, and progress feedback.
"""

from datetime import datetime

from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

from roadmap.adapters.sync.sync_retrieval_orchestrator import SyncRetrievalOrchestrator
from roadmap.core.models.sync_state import SyncState
from roadmap.core.services.baseline_builder_progress import (
    ProgressTrackingBaselineBuilder,
    create_progress_builder,
)
from roadmap.core.services.optimized_baseline_builder import (
    OptimizedBaselineBuilder,
)
from roadmap.core.services.sync_report import SyncReport

logger = get_logger(__name__)


class SyncCacheOrchestrator(SyncRetrievalOrchestrator):
    """Sync orchestrator with optimized baseline building and database caching.

    Extends SyncRetrievalOrchestrator with:
    1. OptimizedBaselineBuilder for intelligent change detection
    2. Database caching of baseline state
    3. Progress bar feedback during sync
    4. Prevention of re-syncing unchanged issues
    """

    def __init__(self, *args, show_progress: bool = True, **kwargs):
        """Initialize with optimized baseline builder.

        Args:
            show_progress: Whether to show progress bars
            *args, **kwargs: Passed to EnhancedSyncOrchestrator
        """
        super().__init__(*args, **kwargs)
        self.optimized_builder = OptimizedBaselineBuilder(self.issues_dir)
        self.show_progress = show_progress
        self._progress_builder: ProgressTrackingBaselineBuilder | None = None

    def _create_progress_context(self) -> Progress | None:
        """Create a progress context for sync operations.

        Returns:
            Progress instance or None if progress disabled
        """
        if not self.show_progress:
            return None

        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}[/bold blue]"),
            transient=True,
        )

    def _load_cached_baseline(self) -> SyncState | None:
        """Load baseline state from database cache.

        Returns:
            Cached SyncState or None if not available
        """
        try:
            import json
            import sqlite3

            db_path = self.core.roadmap_dir / ".roadmap" / "db" / "state.db"
            if not db_path.exists():
                logger.debug("cached_baseline_db_not_found")
                return None

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Query sync_base_state table
            cursor.execute(
                """
                SELECT last_sync, data FROM sync_base_state
                ORDER BY created_at DESC LIMIT 1
                """
            )
            result = cursor.fetchone()
            conn.close()

            if not result:
                logger.debug("cached_baseline_not_in_db")
                return None

            last_sync_str, data_json = result
            last_sync = datetime.fromisoformat(last_sync_str)
            data = json.loads(data_json)

            baseline = SyncState.from_dict(data)
            baseline.last_sync = last_sync

            logger.info(
                "cached_baseline_loaded",
                issue_count=len(baseline.issues),
                last_sync=last_sync.isoformat(),
            )
            return baseline

        except Exception as e:
            logger.warning(
                "cached_baseline_load_failed",
                operation="load_baseline",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                suggested_action="create_new_baseline",
            )
            return None

    def _save_baseline_to_cache(self, baseline: SyncState) -> None:
        """Save baseline state to database cache.

        Args:
            baseline: SyncState to cache
        """
        try:
            import json
            import sqlite3

            db_path = self.core.roadmap_dir / ".roadmap" / "db" / "state.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Insert into sync_base_state
            cursor.execute(
                """
                INSERT INTO sync_base_state (last_sync, data, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    baseline.last_sync.isoformat(),
                    json.dumps(baseline.to_dict()),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            conn.close()

            logger.info(
                "baseline_cached_to_db",
                issue_count=len(baseline.issues),
                last_sync=baseline.last_sync.isoformat(),
            )

        except OSError as e:
            logger.warning(
                "baseline_cache_save_failed",
                operation="save_baseline",
                entity_type="baseline",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                suggested_action="check_disk_space",
            )
        except Exception as e:
            logger.warning(
                "baseline_cache_save_failed",
                operation="save_baseline",
                error_type=type(e).__name__,
                error=str(e),
                error_classification="database_error",
            )

    def _get_baseline_with_optimization(
        self, progress_ctx: Progress | None = None
    ) -> SyncState | None:
        """Get baseline state using optimized builder with progress tracking.

        Args:
            progress_ctx: Optional Progress context for feedback

        Returns:
            SyncState or None if unable to construct
        """
        # PHASE 3: Try database baseline first (fastest - ~10ms)
        try:
            db_baseline = self.core.db.get_sync_baseline()
            if db_baseline:
                logger.debug(
                    "using_database_baseline",
                    issue_count=len(db_baseline),
                )
                from datetime import datetime

                from roadmap.core.models.sync_state import IssueBaseState, SyncState

                issues = {}
                for issue_id, data in db_baseline.items():
                    issues[issue_id] = IssueBaseState(
                        id=issue_id,
                        status=data.get("status", "todo"),
                        title=data.get("title", ""),
                        assignee=data.get("assignee"),
                        milestone=data.get("milestone"),
                        headline=data.get("headline", ""),
                        content=data.get("content", ""),
                        labels=data.get("labels", []),
                    )

                return SyncState(
                    last_sync=datetime.utcnow(),
                    backend="github",
                    issues=issues,
                )
        except Exception as e:
            logger.warning(
                "database_baseline_load_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Try to load from cache (fallback)
        cached = self._load_cached_baseline()
        if cached:
            logger.debug(
                "using_cached_baseline",
                issue_count=len(cached.issues),
            )
            return cached

        # Get all current issue files
        try:
            local_issues = self.core.issues.list()
            issue_files = [self.issues_dir / f"{issue.id}.md" for issue in local_issues]
            issue_files = [f for f in issue_files if f.exists()]

            logger.info(
                "baseline_construction_starting",
                issue_count=len(issue_files),
            )

            # Use progress builder if context available
            if progress_ctx and self.show_progress:
                self._progress_builder = create_progress_builder(
                    self.issues_dir,
                    show_progress=True,
                )
                if self._progress_builder:
                    self._progress_builder.set_progress_context(progress_ctx)
                    _updates, _deleted, metrics = (
                        self._progress_builder.rebuild_with_progress(
                            issue_files,
                            cached,
                            git_ref="HEAD~1",
                        )
                    )
                    logger.info(
                        "baseline_rebuilt_with_progress",
                        time_ms=metrics.rebuild_time_ms,
                    )

            # Build baseline using optimized builder
            baseline = SyncState(
                last_sync=datetime.now(),
                backend=self.backend.__class__.__name__.lower(),
            )

            # Reconstruct each issue from git history
            for issue in local_issues:
                try:
                    issue_file = self.issues_dir / f"{issue.id}.md"
                    if issue_file.exists():
                        local_baseline = self.baseline_retriever.get_local_baseline(
                            issue_file, baseline.last_sync
                        )
                        if local_baseline:
                            baseline.issues[issue.id] = local_baseline
                except Exception as e:
                    logger.warning(
                        "baseline_issue_reconstruction_failed",
                        issue_id=issue.id,
                        error=str(e),
                    )

            # Cache the baseline
            self._save_baseline_to_cache(baseline)

            logger.info(
                "baseline_constructed_and_cached",
                issue_count=len(baseline.issues),
            )
            return baseline

        except Exception as e:
            logger.warning(
                "baseline_construction_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def sync_all_issues(
        self,
        dry_run: bool = True,
        force_local: bool = False,
        force_remote: bool = False,
        show_progress: bool = True,
        push_only: bool = False,
        pull_only: bool = False,
    ) -> SyncReport:
        """Sync all issues with optimized baseline and progress tracking.

        Args:
            dry_run: If True, only detect changes without applying them
            force_local: Resolve conflicts by keeping local changes
            force_remote: Resolve conflicts by keeping remote changes
            show_progress: Show progress bars during sync
            push_only: If True, only push changes (skip pulling)
            pull_only: If True, only pull changes (skip pushing)

        Returns:
            SyncReport with detected changes and conflicts
        """
        # Create progress context
        progress_ctx = self._create_progress_context() if show_progress else None

        try:
            if progress_ctx:
                with progress_ctx as progress:
                    task = progress.add_task(
                        "Starting sync...",
                        total=None,
                    )

                    # Get optimized baseline
                    logger.info("optimized_sync_starting")
                    progress.update(task, description="Analyzing local changes...")

                    _baseline = self._get_baseline_with_optimization(progress_ctx)

                    progress.update(task, description="Syncing with remote...")

                    # Call parent's sync_all_issues
                    report = super().sync_all_issues(
                        dry_run=dry_run,
                        force_local=force_local,
                        force_remote=force_remote,
                        push_only=push_only,
                        pull_only=pull_only,
                    )

                    progress.update(task, description="Sync complete")

                    logger.info(
                        "optimized_sync_complete",
                        error=report.error,
                    )

                    return report
            else:
                # No progress - just run sync
                _baseline = self._get_baseline_with_optimization(None)
                return super().sync_all_issues(
                    dry_run=dry_run,
                    force_local=force_local,
                    force_remote=force_remote,
                    push_only=push_only,
                    pull_only=pull_only,
                )

        except Exception as e:
            logger.error(
                "optimized_sync_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            report = SyncReport()
            report.error = f"Optimized sync failed: {str(e)}"
            return report

    def capture_post_sync_baseline(self) -> SyncState | None:
        """Capture the current local state as the new baseline after successful sync.

        This creates a new baseline representing the agreed-upon state
        after changes have been applied locally and remotely.

        Returns:
            SyncState representing the current state, or None if capture fails
        """
        from datetime import datetime

        try:
            logger.info("capturing_post_sync_baseline")

            # Get all current local issues (including archived)
            local_issues = self.core.issues.list_all_including_archived()

            # Create new baseline from current state
            baseline = SyncState(
                last_sync=datetime.now(),
                backend=self.backend.__class__.__name__.lower(),
            )

            # Reconstruct each issue from current file state
            for issue in local_issues:
                try:
                    issue_file = self.issues_dir / f"{issue.id}.md"
                    if issue_file.exists():
                        # Get the current baseline state from file
                        local_baseline = self.baseline_retriever.get_baseline_from_file(
                            issue_file
                        )
                        if local_baseline:
                            baseline.issues[issue.id] = local_baseline
                except Exception as e:
                    logger.warning(
                        "post_sync_baseline_issue_reconstruction_failed",
                        issue_id=issue.id,
                        error=str(e),
                    )

            logger.info(
                "post_sync_baseline_captured",
                issue_count=len(baseline.issues),
                last_sync=baseline.last_sync.isoformat(),
            )
            return baseline

        except Exception as e:
            logger.error(
                "post_sync_baseline_capture_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None
