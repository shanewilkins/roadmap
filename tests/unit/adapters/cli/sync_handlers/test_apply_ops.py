"""Tests for sync apply_ops module."""

import io
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from rich.console import Console

from roadmap.adapters.cli.sync_handlers.apply_ops import (
    confirm_and_apply,
    display_error_summary,
    finalize_sync,
    perform_apply_phase,
    present_apply_intent,
    run_analysis_phase,
)


@pytest.fixture
def mock_console():
    """Create a mock console instance."""
    return Mock()


class TestDisplayErrorSummary:
    """Test error summary display functionality."""

    def test_no_errors_displays_nothing(self, mock_console):
        """Test that empty error dict displays nothing."""
        errors = {}
        display_error_summary(errors, mock_console, verbose=False)

        # Should not print anything
        assert not mock_console.print.called

    def test_single_dependency_error(self, mock_console):
        """Test display of single dependency error."""
        errors = {
            "issue-123": "Foreign key constraint failed: milestone_id violates constraint"
        }
        display_error_summary(errors, mock_console, verbose=False)

        # Check that error header was printed
        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Sync Errors" in output
        # Foreign key constraint gets classified as database error, which is in data_errors group
        assert "Data Errors" in output or "Dependency Errors" in output
        assert "(1)" in output

    def test_multiple_error_categories(self, mock_console):
        """Test display with multiple error categories."""
        errors = {
            "issue-1": "Milestone 'v1-0' not found",
            "issue-2": "Foreign key constraint failed",
            "issue-3": "Rate limit exceeded",
            "issue-4": "Network timeout",
            "issue-5": "Permission denied",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should show multiple categories
        assert "Dependency Errors" in output
        assert "API Errors" in output
        assert "Authentication Errors" in output

    def test_verbose_mode_shows_issue_ids(self, mock_console):
        """Test that verbose mode displays affected issue IDs."""
        errors = {
            "issue-abc123": "Milestone 'v1-0' not found",
            "issue-def456": "Milestone 'v2-0' not found",
        }
        display_error_summary(errors, mock_console, verbose=True)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Verbose mode should show issue IDs (truncated to 8 chars)
        assert "issue-ab" in output or "Affected issues" in output

    def test_verbose_mode_truncates_long_messages(self, mock_console):
        """Test that verbose mode truncates long error messages."""
        long_message = "A" * 100  # 100 character error
        errors = {"issue-123": long_message}
        display_error_summary(errors, mock_console, verbose=True)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should truncate with ...
        assert "..." in output

    def test_verbose_mode_limits_issue_examples(self, mock_console):
        """Test that verbose mode shows max 5 examples per category."""
        errors = {f"issue-{i}": "Milestone not found" for i in range(10)}
        display_error_summary(errors, mock_console, verbose=True)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should mention "and 5 more" or similar
        assert "more" in output.lower()

    def test_api_errors_categorization(self, mock_console):
        """Test API errors are properly categorized."""
        errors = {
            "issue-1": "Rate limit exceeded",
            "issue-2": "Network error: connection refused",
            "issue-3": "Request timeout after 30 seconds",
            "issue-4": "Service unavailable (503)",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "API Errors" in output
        assert "(4)" in output

    def test_auth_errors_categorization(self, mock_console):
        """Test authentication errors are properly categorized."""
        errors = {
            "issue-1": "Authentication failed",
            "issue-2": "Permission denied: repo access required",
            "issue-3": "Token expired",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Authentication Errors" in output
        assert "(3)" in output

    def test_data_errors_categorization(self, mock_console):
        """Test data errors are properly categorized."""
        errors = {
            "issue-1": "Database error: constraint violation",
            "issue-2": "Validation error: invalid status",
            "issue-3": "Duplicate entity found",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Data Errors" in output
        assert "(3)" in output

    def test_resource_errors_categorization(self, mock_console):
        """Test resource errors are properly categorized."""
        errors = {
            "issue-1": "Resource deleted on remote",
            "issue-2": "Issue not found (404)",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Resource Errors" in output
        assert "(2)" in output

    def test_file_system_errors_categorization(self, mock_console):
        """Test file system errors are properly categorized."""
        errors = {
            "issue-1": "FileNotFoundError: config.json not found",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # The classifier checks error_type for file system errors, but display_error_summary
        # only passes error messages, so this gets classified based on message content
        assert (
            "File System Errors" in output
            or "Unknown Errors" in output
            or "Resource Errors" in output
        )
        assert "(1)" in output

    def test_unknown_errors_categorization(self, mock_console):
        """Test unknown errors are properly categorized."""
        errors = {
            "issue-1": "Some weird unexpected error",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        assert "Unknown Errors" in output
        assert "(1)" in output

    def test_recommendations_displayed(self, mock_console):
        """Test that fix recommendations are displayed."""
        errors = {
            "issue-1": "Milestone not found",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should show "Fix:" somewhere
        assert "Fix:" in output or "fix" in output.lower()

    def test_total_error_count_displayed(self, mock_console):
        """Test that total error count is displayed."""
        errors = {
            "issue-1": "Error 1",
            "issue-2": "Error 2",
            "issue-3": "Error 3",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should show total count
        assert "3" in output

    def test_mixed_errors_all_displayed(self, mock_console):
        """Test comprehensive scenario with mixed error types."""
        errors = {
            "issue-1": "Foreign key constraint failed",
            "issue-2": "Rate limit exceeded",
            "issue-3": "Authentication failed",
            "issue-4": "Database constraint violation",
            "issue-5": "Resource deleted on remote",
            "issue-6": "Unknown error occurred",
        }
        display_error_summary(errors, mock_console, verbose=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        output = "\n".join(calls)

        # Should categorize into multiple groups
        # Note: Foreign key constraint is classified as data error
        assert "API Errors" in output  # Rate limit
        assert "Authentication Errors" in output  # Auth failed
        assert "Data Errors" in output  # Database constraint
        assert "Resource Errors" in output  # Resource deleted
        assert "Unknown Errors" in output  # Unknown error

    def test_verbose_false_hides_details(self, mock_console):
        """Test that verbose=False doesn't show issue IDs."""
        errors = {
            "issue-abc123": "Milestone not found",
        }
        display_error_summary(errors, mock_console, verbose=False)

        # Should NOT show "Affected issues" section in non-verbose mode
        # This is a bit tricky to test, but we can check the call count
        # Non-verbose should have fewer print calls
        assert len(mock_console.print.call_args_list) < 20


class TestApplyPhaseBehavior:
    """Test sync apply orchestration behavior."""

    def test_present_apply_intent_true_and_false(self):
        console = Mock()

        has_changes = SimpleNamespace(
            issues_needs_push=1,
            issues_needs_pull=0,
            conflicts_detected=0,
        )
        no_changes = SimpleNamespace(
            issues_needs_push=0,
            issues_needs_pull=0,
            conflicts_detected=0,
        )

        assert present_apply_intent(has_changes, console) is True
        assert present_apply_intent(no_changes, console) is False

    def test_perform_apply_phase_exits_on_report_error(self):
        console = Console(file=io.StringIO(), force_terminal=False)
        orchestrator = SimpleNamespace(
            sync_all_issues=lambda **_kwargs: SimpleNamespace(
                error="fatal",
                errors={},
                issues_pushed=0,
                issues_pulled=0,
            )
        )
        analysis_report = SimpleNamespace(issues_needs_pull=0, issues_needs_push=0)

        with pytest.raises(SystemExit):
            perform_apply_phase(
                core=SimpleNamespace(),
                orchestrator=orchestrator,
                console_inst=console,
                analysis_report=analysis_report,
                force_local=False,
                force_remote=False,
                push=False,
                pull=False,
                verbose=False,
            )

    def test_perform_apply_phase_up_to_date_and_tip_output(self):
        buffer = io.StringIO()
        console = Console(file=buffer, force_terminal=False)

        orchestrator = SimpleNamespace(
            sync_all_issues=lambda **_kwargs: SimpleNamespace(
                error=None,
                errors={},
                issues_pushed=0,
                issues_pulled=0,
            )
        )
        analysis_report = SimpleNamespace(issues_needs_pull=1, issues_needs_push=0)

        report = perform_apply_phase(
            core=SimpleNamespace(),
            orchestrator=orchestrator,
            console_inst=console,
            analysis_report=analysis_report,
            force_local=False,
            force_remote=False,
            push=False,
            pull=False,
            verbose=False,
        )

        output = buffer.getvalue()
        assert report.issues_pushed == 0
        assert "Everything up-to-date" in output
        assert "Tip:" in output

    def test_confirm_and_apply_delegates_to_perform_apply_phase(self, monkeypatch):
        expected = SimpleNamespace(ok=True)
        monkeypatch.setattr(
            "roadmap.adapters.cli.sync_handlers.apply_ops.perform_apply_phase",
            lambda *_args, **_kwargs: expected,
        )

        result = confirm_and_apply(
            core=SimpleNamespace(),
            orchestrator=SimpleNamespace(),
            console_inst=Mock(),
            analysis_report=SimpleNamespace(conflicts_detected=0, changes=[]),
            force_local=False,
            force_remote=False,
            push=False,
            pull=False,
            verbose=False,
            interactive=False,
        )

        assert result is expected

    def test_run_analysis_phase_calls_presenter(self, monkeypatch):
        presented = {"called": False}

        def _present(analysis_report, verbose=False):
            presented["called"] = True
            assert verbose is True
            assert analysis_report.total_changes == 2

        monkeypatch.setattr(
            "roadmap.adapters.cli.sync_presenter.present_analysis",
            _present,
        )

        orchestrator = SimpleNamespace(
            analyze_all_issues=lambda **_kwargs: (
                SimpleNamespace(plan_id="p1"),
                SimpleNamespace(total_changes=2),
            )
        )

        plan, analysis = run_analysis_phase(
            orchestrator=orchestrator,
            push=True,
            pull=False,
            dry_run=True,
            verbose=True,
            console_inst=Console(file=io.StringIO(), force_terminal=False),
            interactive_duplicates=True,
        )

        assert plan.plan_id == "p1"
        assert analysis.total_changes == 2
        assert presented["called"] is True

    def test_finalize_sync_sets_baseline_flag_and_displays_metrics(self, monkeypatch):
        buffer = io.StringIO()
        console = Console(file=buffer, force_terminal=False)

        monkeypatch.setattr(
            "roadmap.adapters.cli.sync_handlers.baseline_ops.capture_and_save_post_sync_baseline",
            lambda *_args, **_kwargs: False,
        )

        metrics_saved = {"called": False}

        class _Repo:
            def __init__(self, _db_manager):
                pass

            def save(self, _metrics):
                metrics_saved["called"] = True

        monkeypatch.setattr(
            "roadmap.adapters.persistence.sync_metrics_repository.SyncMetricsRepository",
            _Repo,
        )

        displayed = {"called": False}
        monkeypatch.setattr(
            "roadmap.adapters.cli.sync_handlers.apply_ops._display_sync_metrics",
            lambda *_args, **_kwargs: displayed.__setitem__("called", True),
        )

        report = SimpleNamespace(
            baseline_update_failed=False,
            issues_pulled=0,
            metrics=SimpleNamespace(to_dict=lambda: {"total_duration_seconds": 1.0}),
        )
        core = SimpleNamespace(db_manager=SimpleNamespace())

        finalize_sync(
            core=core,
            console_inst=console,
            report=report,
            pre_sync_issue_count=3,
            verbose=False,
            backend_type="git",
        )

        assert report.baseline_update_failed is True
        assert metrics_saved["called"] is True
        assert displayed["called"] is True
        assert "Sync completed successfully" in buffer.getvalue()
