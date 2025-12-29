"""Tests for sync_status command - GitHub sync history and statistics."""

from unittest.mock import Mock

import pytest

from roadmap.adapters.cli.issues.sync_status import (
    _build_aggregate_stats_table,
    _build_sync_history_table,
)


class TestBuildSyncHistoryTable:
    """Test sync history table building."""

    def test_build_history_table_with_successful_records(self):
        """Test building history table with successful sync records."""
        records = [
            Mock(
                sync_timestamp="2025-12-23T20:30:00Z",
                success=True,
                conflict_resolution=None,
                local_changes=["file1.md"],
                github_changes=[],
                error_message=None,
            )
        ]

        table = _build_sync_history_table(records)
        assert table is not None

    def test_build_history_table_with_conflict_records(self):
        """Test building history table with conflict records."""
        records = [
            Mock(
                sync_timestamp="2025-12-23T20:30:00Z",
                success=False,
                conflict_resolution="resolved by local",
                local_changes=["file1.md"],
                github_changes=["file2.md"],
                error_message=None,
            )
        ]

        table = _build_sync_history_table(records)
        assert table is not None

    def test_build_history_table_with_error_records(self):
        """Test building history table with error records."""
        records = [
            Mock(
                sync_timestamp="2025-12-23T20:30:00Z",
                success=False,
                conflict_resolution=None,
                local_changes=[],
                github_changes=[],
                error_message="Connection timeout",
            )
        ]

        table = _build_sync_history_table(records)
        assert table is not None

    def test_build_history_table_with_multiple_records(self):
        """Test building history table with multiple records."""
        records = [
            Mock(
                sync_timestamp="2025-12-23T20:30:00Z",
                success=True,
                conflict_resolution=None,
                local_changes=["file1.md"],
                github_changes=[],
                error_message=None,
            ),
            Mock(
                sync_timestamp="2025-12-22T10:15:00Z",
                success=False,
                conflict_resolution="resolved by github",
                local_changes=["file2.md"],
                github_changes=["file3.md"],
                error_message=None,
            ),
            Mock(
                sync_timestamp="2025-12-21T15:45:00Z",
                success=False,
                conflict_resolution=None,
                local_changes=[],
                github_changes=[],
                error_message="API error: rate limit exceeded",
            ),
        ]

        table = _build_sync_history_table(records)
        assert table is not None

    def test_build_history_table_empty_records(self):
        """Test building history table with empty records list."""
        records = []

        table = _build_sync_history_table(records)
        assert table is not None

    def test_build_history_table_with_long_error_message(self):
        """Test building history table with long error message truncation."""
        records = [
            Mock(
                sync_timestamp="2025-12-23T20:30:00Z",
                success=False,
                conflict_resolution=None,
                local_changes=[],
                github_changes=[],
                error_message="This is a very long error message that should be truncated to fit in the table column width properly",
            )
        ]

        table = _build_sync_history_table(records)
        assert table is not None

    def test_build_history_table_with_multiple_changes(self):
        """Test building history table with multiple local and GitHub changes."""
        records = [
            Mock(
                sync_timestamp="2025-12-23T20:30:00Z",
                success=True,
                conflict_resolution=None,
                local_changes=["file1.md", "file2.md", "file3.md", "file4.md"],
                github_changes=["pr1", "pr2"],
                error_message=None,
            )
        ]

        table = _build_sync_history_table(records)
        assert table is not None

    @pytest.mark.parametrize(
        "num_changes,change_type",
        [
            (0, "local"),
            (1, "local"),
            (5, "local"),
            (0, "github"),
            (1, "github"),
            (5, "github"),
        ],
    )
    def test_history_table_various_change_counts(self, num_changes, change_type):
        """Test history table with various change counts."""
        if change_type == "local":
            records = [
                Mock(
                    sync_timestamp="2025-12-23T20:30:00Z",
                    success=True,
                    conflict_resolution=None,
                    local_changes=[f"file{i}.md" for i in range(num_changes)],
                    github_changes=[],
                    error_message=None,
                )
            ]
        else:
            records = [
                Mock(
                    sync_timestamp="2025-12-23T20:30:00Z",
                    success=True,
                    conflict_resolution=None,
                    local_changes=[],
                    github_changes=[f"change{i}" for i in range(num_changes)],
                    error_message=None,
                )
            ]

        table = _build_sync_history_table(records)
        assert table is not None


class TestBuildAggregateStatsTable:
    """Test aggregate statistics table building."""

    def test_build_stats_table_basic(self):
        """Test building aggregate stats table with basic data."""
        stats = {
            "total_issues": 10,
            "total_sync_attempts": 50,
            "successful_syncs": 45,
            "success_rate": 90.0,
            "total_conflicts": 2,
            "conflict_rate": 4.0,
            "never_synced": 2,
        }

        table = _build_stats_table(stats)
        assert table is not None

    def test_build_stats_table_perfect_success_rate(self):
        """Test building stats table with 100% success rate."""
        stats = {
            "total_issues": 5,
            "total_sync_attempts": 25,
            "successful_syncs": 25,
            "success_rate": 100.0,
            "total_conflicts": 0,
            "conflict_rate": 0.0,
            "never_synced": 0,
        }

        table = _build_aggregate_stats_table(stats)
        assert table is not None

    def test_build_stats_table_low_success_rate(self):
        """Test building stats table with low success rate."""
        stats = {
            "total_issues": 10,
            "total_sync_attempts": 50,
            "successful_syncs": 25,
            "success_rate": 50.0,
            "total_conflicts": 10,
            "conflict_rate": 20.0,
            "never_synced": 3,
        }

        table = _build_aggregate_stats_table(stats)
        assert table is not None

    def test_build_stats_table_high_conflict_rate(self):
        """Test building stats table with high conflict rate."""
        stats = {
            "total_issues": 10,
            "total_sync_attempts": 50,
            "successful_syncs": 35,
            "success_rate": 70.0,
            "total_conflicts": 15,
            "conflict_rate": 30.0,
            "never_synced": 2,
        }

        table = _build_aggregate_stats_table(stats)
        assert table is not None

    def test_build_stats_table_no_syncs(self):
        """Test building stats table when no syncs attempted."""
        stats = {
            "total_issues": 5,
            "total_sync_attempts": 0,
            "successful_syncs": 0,
            "success_rate": 0.0,
            "total_conflicts": 0,
            "conflict_rate": 0.0,
            "never_synced": 5,
        }

        table = _build_aggregate_stats_table(stats)
        assert table is not None

    @pytest.mark.parametrize(
        "success_rate,conflict_rate",
        [
            (100.0, 0.0),
            (90.0, 5.0),
            (75.0, 10.0),
            (50.0, 25.0),
            (25.0, 50.0),
        ],
    )
    def test_build_stats_table_various_rates(self, success_rate, conflict_rate):
        """Test building stats table with various success and conflict rates."""
        total_syncs = 100
        successful = int(total_syncs * success_rate / 100)
        conflicts = int(total_syncs * conflict_rate / 100)

        stats = {
            "total_issues": 10,
            "total_sync_attempts": total_syncs,
            "successful_syncs": successful,
            "success_rate": success_rate,
            "total_conflicts": conflicts,
            "conflict_rate": conflict_rate,
            "never_synced": 5,
        }

        table = _build_aggregate_stats_table(stats)
        assert table is not None


class TestSyncStatusCommand:
    """Test sync_status CLI command."""

    def test_sync_status_no_args_no_flags_fails(self, cli_runner):
        """Test sync-status command without issue ID or flags fails."""
        from roadmap.adapters.cli import main

        with cli_runner.isolated_filesystem():
            cli_runner.invoke(main, ["init", "-y", "--skip-github", "--skip-project"])
            result = cli_runner.invoke(main, ["issue", "sync-status"])
            assert result.exit_code != 0

    def test_sync_status_with_invalid_issue_id(self, cli_runner):
        """Test sync-status command with invalid issue ID."""
        from roadmap.adapters.cli import main

        with cli_runner.isolated_filesystem():
            cli_runner.invoke(main, ["init", "-y", "--skip-github", "--skip-project"])
            result = cli_runner.invoke(main, ["issue", "sync-status", "nonexistent"])
            assert result.exit_code != 0

    def test_sync_status_help(self, cli_runner):
        """Test sync-status command help."""
        from roadmap.adapters.cli import main

        result = cli_runner.invoke(main, ["issue", "sync-status", "--help"])
        assert result.exit_code == 0
        assert "sync-status" in result.output or "Sync status" in result.output

    def test_sync_status_with_all_flag_no_issues(self, cli_runner):
        """Test sync-status --all flag with no linked issues returns appropriate message."""
        # Test that the function handles no linked issues gracefully
        pass  # Deferred - requires integration testing

    def test_sync_status_with_statistics_flag_no_issues(self, cli_runner):
        """Test sync-status --statistics flag with no linked issues returns appropriate message."""
        # Test that the function handles no linked issues gracefully
        pass  # Deferred - requires integration testing

    def test_sync_status_with_history_flag_unlinked_issue(self, cli_runner):
        """Test sync-status --history flag with unlinked issue returns appropriate message."""
        # Test that the function handles unlinked issues gracefully
        pass  # Deferred - requires integration testing


def _build_stats_table(stats):
    """Helper to build stats table (wrapper for testing)."""
    return _build_aggregate_stats_table(stats)
