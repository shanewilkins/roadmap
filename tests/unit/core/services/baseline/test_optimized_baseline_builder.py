"""Tests for optimized baseline builder with incremental updates."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.core.models.sync_state import IssueBaseState, SyncState
from roadmap.core.services.baseline.optimized_baseline_builder import (
    CachedBaselineState,
    OptimizedBaselineBuilder,
)


@pytest.fixture
def builder(tmp_path):
    """Create OptimizedBaselineBuilder."""
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir()
    return OptimizedBaselineBuilder(issues_dir)


@pytest.fixture
def mock_sync_state():
    """Create mock sync state."""
    return SyncState(
        last_sync=datetime.now(UTC) - timedelta(hours=2),
        backend="git",
        issues={
            "TASK-123": IssueBaseState(
                id="TASK-123",
                status="todo",
                title="Task 1",
            ),
            "TASK-124": IssueBaseState(
                id="TASK-124",
                status="in-progress",
                title="Task 2",
            ),
        },
    )


class TestExtractIssueId:
    """Test issue ID extraction from file paths."""

    def test_extracts_id_from_backlog_path(self, builder):
        """Should extract ID from backlog issue file."""
        path = "issues/backlog/TASK-123-example.md"
        result = builder.extract_issue_id_from_path(path)
        assert result == "TASK-123"

    def test_extracts_id_from_milestone_path(self, builder):
        """Should extract ID from milestone issue file."""
        path = "issues/v1.0/FEAT-456-feature-name.md"
        result = builder.extract_issue_id_from_path(path)
        assert result == "FEAT-456"

    def test_returns_none_for_non_issue_file(self, builder):
        """Should return None for non-issue files."""
        path = "README.md"
        result = builder.extract_issue_id_from_path(path)
        assert result is None

    def test_returns_none_for_invalid_format(self, builder):
        """Should return None for invalid format."""
        path = "issues/backlog/invalid-file.md"
        result = builder.extract_issue_id_from_path(path)
        assert result is None


class TestGetChangedIssueFiles:
    """Test detection of changed issue files."""

    def test_returns_empty_set_when_no_changes(self, builder):
        """Should return empty set when no files changed."""
        with patch(
            "roadmap.core.services.baseline.optimized_baseline_builder.get_changed_files_since_commit",
            return_value=set(),
        ):
            result = builder.get_changed_issue_files("HEAD~1")
            assert result == set()

    def test_filters_to_markdown_files(self, builder):
        """Should filter to only .md files."""
        changed = {
            "issues/backlog/TASK-123.md",
            "issues/TASK-124.txt",
            "src/main.py",
        }
        with patch(
            "roadmap.core.services.baseline.optimized_baseline_builder.get_changed_files_since_commit",
            return_value=changed,
        ):
            result = builder.get_changed_issue_files("HEAD~1")
            assert result == {"issues/backlog/TASK-123.md"}

    def test_limits_to_specific_issues(self, builder):
        """Should limit to specified issues."""
        changed = {
            "issues/backlog/TASK-123.md",
            "issues/backlog/TASK-124.md",
            "issues/backlog/TASK-125.md",
        }
        with patch(
            "roadmap.core.services.baseline.optimized_baseline_builder.get_changed_files_since_commit",
            return_value=changed,
        ):
            result = builder.get_changed_issue_files(
                "HEAD~1", limit_to_issues=["TASK-123"]
            )
            assert "TASK-123" in str(result)


class TestShouldRebuildAll:
    """Test logic for determining full vs incremental rebuild."""

    def test_requires_rebuild_with_no_cache(self, builder):
        """Should require rebuild when no cached state."""
        result = builder.should_rebuild_all(None)
        assert result is True

    def test_requires_rebuild_if_cache_stale(self, builder, mock_sync_state):
        """Should recommend rebuild if cache older than 1 hour."""
        # Cache from 2+ hours ago
        result = builder.should_rebuild_all(mock_sync_state, time_since_last_sync=7200)
        assert result is True

    def test_allows_incremental_if_cache_fresh(self, builder, mock_sync_state):
        """Should allow incremental update for fresh cache."""
        # Cache from 5 minutes ago
        result = builder.should_rebuild_all(mock_sync_state, time_since_last_sync=300)
        assert result is False

    def test_allows_incremental_without_time_info(self, builder, mock_sync_state):
        """Should allow incremental if no time information."""
        result = builder.should_rebuild_all(mock_sync_state, time_since_last_sync=None)
        assert result is False


class TestGetIssueFilesToUpdate:
    """Test determination of which issues need updates."""

    def test_updates_new_issues(self, builder, mock_sync_state, tmp_path):
        """Should mark new issues for update."""
        # Create files for 3 issues (2 in cache + 1 new)
        backlog = tmp_path / "issues" / "backlog"
        backlog.mkdir(parents=True)

        files = [
            backlog / "TASK-123-existing.md",
            backlog / "TASK-124-existing.md",
            backlog / "TASK-125-new.md",
        ]
        for f in files:
            f.write_text("# Issue")

        file_paths = [Path(str(f)) for f in files]

        result = builder.get_issue_files_to_update(file_paths, set(), mock_sync_state)

        # Should include new issue
        assert "TASK-125" in result
        # Existing unchanged issues might not be included
        assert len(result) >= 1

    def test_updates_changed_files(self, builder, mock_sync_state, tmp_path):
        """Should mark changed files for update."""
        backlog = tmp_path / "issues" / "backlog"
        backlog.mkdir(parents=True)

        files = [
            backlog / "TASK-123-example.md",
            backlog / "TASK-124-example.md",
        ]
        for f in files:
            f.write_text("# Issue")

        file_paths = [Path(str(f)) for f in files]
        changed = {str(file_paths[0].relative_to(builder.issues_dir))}

        result = builder.get_issue_files_to_update(file_paths, changed, mock_sync_state)

        # TASK-123 should be marked for update (changed)
        assert "TASK-123" in result

    def test_skips_unchanged_files(self, builder, mock_sync_state, tmp_path):
        """Should skip unchanged files when cache available."""
        backlog = tmp_path / "issues" / "backlog"
        backlog.mkdir(parents=True)

        files = [
            backlog / "TASK-123-example.md",
            backlog / "TASK-124-example.md",
        ]
        for f in files:
            f.write_text("# Issue")

        file_paths = [Path(str(f)) for f in files]
        changed = set()  # No changes

        result = builder.get_issue_files_to_update(file_paths, changed, mock_sync_state)

        # No unchanged files should be updated
        assert len(result) == 0


class TestGetIncrementalUpdateIssues:
    """Test incremental update detection."""

    def test_returns_updates_and_removals(self, builder, mock_sync_state, tmp_path):
        """Should return issues to update and remove."""
        # Create current files (2 existing, 1 new)
        backlog = tmp_path / "issues" / "backlog"
        backlog.mkdir(parents=True)

        current_files = [
            backlog / "TASK-123-example.md",
            backlog / "TASK-125-new.md",
        ]
        for f in current_files:
            f.write_text("# Issue")

        file_paths = [Path(str(f)) for f in current_files]
        changed = {str(file_paths[1].relative_to(builder.issues_dir))}

        updates, removals = builder.get_incremental_update_issues(
            file_paths, changed, mock_sync_state
        )

        # TASK-125 is new, so should be in updates
        assert "TASK-125" in updates
        # TASK-124 was deleted (in cache but not in current)
        assert "TASK-124" in removals

    def test_incremental_is_faster_than_full(self, builder, mock_sync_state, tmp_path):
        """Incremental rebuild should estimate faster time."""
        # Full rebuild of 100 issues
        full_time = builder.estimate_rebuild_time(100)

        # Incremental update of just 5 changed issues
        incremental_time = builder.estimate_rebuild_time(5)

        # Incremental should be much faster (roughly 20x)
        assert incremental_time < full_time * 0.3  # Allow some overhead


class TestEstimateRebuildTime:
    """Test rebuild time estimation."""

    def test_estimates_time_per_issue(self, builder):
        """Should estimate time based on issue count."""
        time_5_issues = builder.estimate_rebuild_time(5)
        time_10_issues = builder.estimate_rebuild_time(10)
        time_100_issues = builder.estimate_rebuild_time(100)

        # Should scale linearly
        assert time_10_issues > time_5_issues
        assert time_100_issues > time_10_issues

    def test_provides_reasonable_estimates(self, builder):
        """Should provide reasonable time estimates."""
        # Single issue should be ~11ms
        time_1 = builder.estimate_rebuild_time(1)
        assert 5 < time_1 < 50

        # 100 issues should be ~1100ms
        time_100 = builder.estimate_rebuild_time(100)
        assert 500 < time_100 < 2000


class TestCachedBaselineState:
    """Test cached baseline state wrapper."""

    def test_tracks_cache_metadata(self):
        """Should track cache metadata."""
        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="git",
            issues={},
        )
        cached = CachedBaselineState(
            state=state,
            from_cache=False,
            rebuilt_issues=50,
            reused_issues=10,
            rebuild_time_ms=123.45,
        )

        assert cached.rebuilt_issues == 50
        assert cached.reused_issues == 10
        assert cached.rebuild_time_ms == 123.45

    def test_identifies_full_rebuild(self):
        """Should identify full rebuild."""
        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="git",
            issues={},
        )
        cached = CachedBaselineState(
            state=state,
            from_cache=False,
            rebuilt_issues=100,
            reused_issues=0,
        )

        assert cached.is_full_rebuild
        assert not cached.is_incremental

    def test_identifies_incremental_update(self):
        """Should identify incremental update."""
        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="git",
            issues={},
        )
        cached = CachedBaselineState(
            state=state,
            from_cache=False,
            rebuilt_issues=5,
            reused_issues=95,
        )

        assert not cached.is_full_rebuild
        assert cached.is_incremental

    def test_converts_to_dict_for_logging(self):
        """Should convert to dictionary for logging."""
        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="git",
            issues={"TASK-1": Mock(), "TASK-2": Mock()},
        )
        cached = CachedBaselineState(
            state=state,
            from_cache=False,
            rebuilt_issues=1,
            reused_issues=1,
            rebuild_time_ms=55.5,
        )

        result = cached.to_dict()

        assert result["is_incremental"] is True
        assert result["total_issues"] == 2
        assert "55.5" in result["rebuild_time_ms"]


class TestIntegrationOptimizedRebuild:
    """Integration tests for optimized rebuild workflow."""

    def test_full_rebuild_flow(self, builder, tmp_path):
        """Should support full rebuild flow."""
        # Create issue files
        backlog = tmp_path / "issues" / "backlog"
        backlog.mkdir(parents=True)

        files = [
            backlog / "TASK-123-example.md",
            backlog / "TASK-124-example.md",
        ]
        for f in files:
            f.write_text("# Issue")

        file_paths = [Path(str(f)) for f in files]

        # Full rebuild from scratch (no cached state)
        result = builder.get_issue_files_to_update(file_paths, set(), None)

        # Both issues should need baseline rebuild
        assert "TASK-123" in result
        assert "TASK-124" in result

    def test_incremental_rebuild_flow(self, builder, mock_sync_state, tmp_path):
        """Should support incremental rebuild flow."""
        # Create issue files matching cache
        backlog = tmp_path / "issues" / "backlog"
        backlog.mkdir(parents=True)

        files = [
            backlog / "TASK-123-example.md",
            backlog / "TASK-124-example.md",
        ]
        for f in files:
            f.write_text("# Issue")

        file_paths = [Path(str(f)) for f in files]

        # Only TASK-123 changed
        changed = {str(file_paths[0].relative_to(builder.issues_dir))}

        result = builder.get_issue_files_to_update(file_paths, changed, mock_sync_state)

        # Only changed issue needs update
        assert "TASK-123" in result
