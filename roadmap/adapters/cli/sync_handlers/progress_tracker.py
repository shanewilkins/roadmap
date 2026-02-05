"""Progress tracking for sync operations."""

from contextlib import contextmanager

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from roadmap.common.console import get_console


class SyncProgressTracker:
    """Tracks and displays progress during sync operations."""

    def __init__(self, console=None):
        """Initialize progress tracker.

        Args:
            console: Rich console instance (creates new one if None)
        """
        self.console = console or get_console()
        self.progress = None
        self.current_task = None

    @contextmanager
    def track_sync(self, total_issues: int):
        """Context manager for tracking overall sync progress.

        Args:
            total_issues: Total number of issues to sync

        Yields:
            Progress tracker instance
        """
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
        )

        with self.progress:
            self.current_task = self.progress.add_task(
                "Syncing issues...", total=total_issues
            )
            yield self

    def update(self, advance: int = 1, description: str | None = None):
        """Update progress.

        Args:
            advance: Number of steps to advance
            description: Optional new description
        """
        if self.progress and self.current_task is not None:
            if description:
                self.progress.update(self.current_task, description=description)
            self.progress.advance(self.current_task, advance)

    def set_description(self, description: str):
        """Set current task description.

        Args:
            description: New description text
        """
        if self.progress and self.current_task is not None:
            self.progress.update(self.current_task, description=description)

    @contextmanager
    def track_phase(self, phase_name: str, total: int | None = None):
        """Track a specific phase of sync operation.

        Args:
            phase_name: Name of the phase (e.g., "Fetching", "Pushing")
            total: Total items in this phase

        Yields:
            Task ID for this phase
        """
        if not self.progress:
            yield None
            return

        task_id = self.progress.add_task(
            f"[cyan]{phase_name}...",
            total=total if total is not None else None,
        )

        try:
            yield task_id
        finally:
            self.progress.update(task_id, completed=True)

    def update_phase(self, task_id, advance: int = 1, description: str | None = None):
        """Update a specific phase task.

        Args:
            task_id: Task ID returned from track_phase
            advance: Number of steps to advance
            description: Optional new description
        """
        if self.progress and task_id is not None:
            if description:
                self.progress.update(task_id, description=description)
            if advance:
                self.progress.advance(task_id, advance)


def create_spinner_progress() -> Progress:
    """Create a simple spinner progress for indeterminate operations.

    Returns:
        Progress instance with spinner
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        TimeElapsedColumn(),
        console=get_console(),
    )
