"""Unit tests for sync progress tracker helpers."""

from unittest.mock import Mock

import pytest
from rich.progress import Progress

from roadmap.adapters.cli.sync_handlers.progress_tracker import (
    SyncProgressTracker,
    create_spinner_progress,
)


@pytest.mark.parametrize("total", [1, 3])
def test_track_sync_creates_task_and_supports_updates(total):
    """track_sync should initialize a task and accept updates."""
    tracker = SyncProgressTracker()

    with tracker.track_sync(total_issues=total) as active:
        assert active.current_task is not None
        active.update(advance=1, description="Syncing one")
        active.set_description("Syncing done")

        with active.track_phase("Fetch", total=2) as phase_id:
            assert phase_id is not None
            active.update_phase(phase_id, advance=1, description="Fetched one")


def test_track_phase_without_progress_yields_none():
    """track_phase should be a no-op when no progress context is active."""
    tracker = SyncProgressTracker(console=Mock())

    with tracker.track_phase("No progress") as phase_id:
        assert phase_id is None


@pytest.mark.parametrize(
    "method_name,args,kwargs",
    [
        ("update", (), {}),
        ("update", (), {"advance": 2, "description": "noop"}),
        ("set_description", ("noop",), {}),
        ("update_phase", (None,), {}),
    ],
)
def test_update_methods_noop_outside_progress(method_name, args, kwargs):
    """Mutation methods should not error when called without active progress."""
    tracker = SyncProgressTracker(console=Mock())
    getattr(tracker, method_name)(*args, **kwargs)


def test_create_spinner_progress_returns_progress_instance():
    """Spinner helper should return a ready-to-use Progress object."""
    spinner = create_spinner_progress()
    assert isinstance(spinner, Progress)
