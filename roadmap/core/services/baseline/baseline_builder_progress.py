"""Enhanced baseline building with progress display.

This module provides progress bar integration for sync state rebuilding,
allowing users to see real-time feedback during optimization phases.
"""

from datetime import UTC, datetime
from pathlib import Path
from time import time

from structlog import get_logger

from roadmap.core.services.sync.sync_state import SyncState
from roadmap.core.services.baseline.optimized_baseline_builder import (
    CachedBaselineState,
    OptimizedBaselineBuilder,
)

logger = get_logger(__name__)


class ProgressTrackingBaselineBuilder:
    """Wraps OptimizedBaselineBuilder with progress bar support.

    Provides real-time feedback during baseline rebuilding operations,
    showing which phase is active (detection, rebuilding, merging).
    """

    def __init__(
        self,
        issues_dir: Path,
        show_progress: bool = True,
    ):
        """Initialize with progress tracking.

        Args:
            issues_dir: Path to issues directory
            show_progress: Whether to show progress bars
        """
        self.builder = OptimizedBaselineBuilder(issues_dir)
        self.show_progress = show_progress
        self._progress = None
        self._current_task = None

    def set_progress_context(self, progress) -> None:
        """Set progress context from rich.progress.Progress.

        Args:
            progress: Progress instance from rich library
        """
        self._progress = progress
        self.builder.set_progress_context(progress)

    def _log_phase(self, phase: str, details: dict | None = None) -> None:
        """Log phase transition with progress.

        Args:
            phase: Name of phase
            details: Optional details dict
        """
        logger.info(
            "baseline_rebuild_phase",
            phase=phase,
            **(details or {}),
        )

    def rebuild_with_progress(
        self,
        all_issue_files: list[Path],
        cached_state: SyncState | None,
        git_ref: str = "HEAD~1",
    ) -> tuple[dict[str, Path] | None, list[str] | None, CachedBaselineState]:
        """Rebuild baseline with progress tracking.

        Args:
            all_issue_files: All current issue file paths
            cached_state: Previous sync state (if any)
            git_ref: Git reference for change detection

        Returns:
            Tuple of (issues_to_update, deleted_issues, metrics)
            - issues_to_update: {issue_id: path} dict for issues to rebuild
            - deleted_issues: [issue_id] list of deleted issues
            - metrics: CachedBaselineState with rebuild stats
        """
        start_time = time()

        try:
            # Phase 1: Determine rebuild strategy
            self._log_phase(
                "Determining rebuild strategy",
                {"cached": cached_state is not None},
            )

            should_full = self.builder.should_rebuild_all(
                cached_state,
                time_since_last_sync=None,
            )

            if should_full:
                return self._rebuild_full_with_progress(all_issue_files, start_time)
            elif cached_state is not None:
                return self._rebuild_incremental_with_progress(
                    all_issue_files, cached_state, git_ref, start_time
                )
            else:
                # No cached state and not full rebuild - treat as full
                return self._rebuild_full_with_progress(all_issue_files, start_time)

        except Exception as e:
            logger.error(
                "baseline_rebuild_error",
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            # Return empty rebuild (will fall back to default)
            return (
                None,
                None,
                CachedBaselineState(
                    SyncState(last_sync_time=datetime.now(UTC), base_issues={}),
                    from_cache=False,
                    rebuilt_issues=0,
                    reused_issues=0,
                    rebuild_time_ms=time() - start_time,
                ),
            )

    def _rebuild_full_with_progress(
        self,
        all_issue_files: list[Path],
        start_time: float,
    ) -> tuple[dict[str, Path], list[str], CachedBaselineState]:
        """Full rebuild with progress display.

        Args:
            all_issue_files: All files
            start_time: Rebuild start time

        Returns:
            Tuple of (issues_to_update, [], metrics)
        """
        self._log_phase("Full rebuild", {"issue_count": len(all_issue_files)})

        # All issues need rebuilding
        issues_to_update = {}
        for idx, file_path in enumerate(all_issue_files):
            relative = str(file_path.relative_to(self.builder.issues_dir))
            issue_id = self.builder.extract_issue_id_from_path(relative)
            if issue_id:
                issues_to_update[issue_id] = file_path

            # Log progress every 10 items
            if (idx + 1) % 10 == 0 or idx == 0:
                self._log_phase(
                    f"Preparing rebuild ({idx + 1}/{len(all_issue_files)})",
                    {"prepared": idx + 1},
                )

        rebuild_time_ms = (time() - start_time) * 1000

        self._log_phase(
            f"Full rebuild ready ({len(issues_to_update)} issues)",
            {"rebuild_time_ms": f"{rebuild_time_ms:.1f}"},
        )

        return (
            issues_to_update,
            [],
            CachedBaselineState(
                SyncState(
                    last_sync_time=datetime.now(UTC),
                    base_issues={},
                ),
                from_cache=False,
                rebuilt_issues=len(issues_to_update),
                reused_issues=0,
                rebuild_time_ms=rebuild_time_ms,
            ),
        )

    def _rebuild_incremental_with_progress(
        self,
        all_issue_files: list[Path],
        cached_state: SyncState,
        git_ref: str,
        start_time: float,
    ) -> tuple[dict[str, Path], list[str], CachedBaselineState]:
        """Incremental rebuild with progress display.

        Args:
            all_issue_files: All files
            cached_state: Previous state
            git_ref: Git reference
            start_time: Rebuild start time

        Returns:
            Tuple of (issues_to_update, deleted_issues, metrics)
        """
        self._log_phase("Detecting file changes", {"git_ref": git_ref})

        # Phase 2: Get changed files
        changed_files = self.builder.get_changed_issue_files(git_ref)
        self._log_phase(
            "File changes detected",
            {"changed_count": len(changed_files)},
        )

        # Phase 3: Determine which issues need updates
        self._log_phase(
            f"Analyzing {len(all_issue_files)} issues",
            {"cached_count": len(cached_state.base_issues)},
        )

        issues_to_update, deleted_issues = self.builder.get_incremental_update_issues(
            all_issue_files, changed_files, cached_state
        )

        rebuild_time_ms = (time() - start_time) * 1000
        reused_count = len(cached_state.base_issues) - len(issues_to_update)

        self._log_phase(
            "Rebuild analysis complete",
            {
                "rebuild_count": len(issues_to_update),
                "reused_count": reused_count,
                "deleted_count": len(deleted_issues),
                "rebuild_time_ms": f"{rebuild_time_ms:.1f}",
            },
        )

        return (
            issues_to_update,
            deleted_issues,
            CachedBaselineState(
                SyncState(
                    last_sync_time=cached_state.last_sync_time,
                    base_issues=cached_state.base_issues,
                ),
                from_cache=False,
                rebuilt_issues=len(issues_to_update),
                reused_issues=reused_count,
                rebuild_time_ms=rebuild_time_ms,
            ),
        )


def create_progress_builder(
    issues_dir: Path,
    show_progress: bool = True,
) -> ProgressTrackingBaselineBuilder | None:
    """Create a progress-enabled baseline builder.

    Args:
        issues_dir: Path to issues directory
        show_progress: Whether to show progress

    Returns:
        ProgressTrackingBaselineBuilder or None if progress not supported

    Example:
        >>> from rich.progress import Progress
        >>> builder = create_progress_builder(Path("roadmap/issues"))
        >>> with Progress() as progress:
        ...     builder.set_progress_context(progress)
        ...     updates, deleted, metrics = builder.rebuild_with_progress(files, state)
        ...     print(metrics.to_dict())
    """
    if not show_progress:
        logger.debug("progress_bars_disabled")
        return None

    return ProgressTrackingBaselineBuilder(issues_dir, show_progress)
