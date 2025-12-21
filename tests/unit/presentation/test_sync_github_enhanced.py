"""Unit tests for Phase 2A-Part1: Enhanced sync command with dry-run and conflict resolution."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.issues.sync import sync_github


@pytest.fixture
def cli_runner():
    """Provide a Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_core():
    """Provide a mock core object."""
    core = Mock()
    core.issues = Mock()
    core.root_path = "/test/roadmap"
    core.github_service = Mock()
    return core


def test_sync_enhanced_help():
    """Test that enhanced sync command help shows new options."""
    runner = CliRunner()
    result = runner.invoke(sync_github, ["--help"])

    assert result.exit_code == 0
    assert "--dry-run" in result.output
    assert "--verbose" in result.output
    assert "--force-local" in result.output
    assert "--force-github" in result.output
    assert "--validate-only" in result.output


def test_sync_enhanced_no_config(cli_runner, mock_core):
    """Test sync when GitHub is not configured."""
    with patch(
        "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
    ) as mock_gh_service_cls:
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = None
        mock_gh_service_cls.return_value = mock_gh_service

        result = cli_runner.invoke(
            sync_github,
            ["--all"],
            obj=mock_core,
        )

        assert result.exit_code == 1


def test_sync_enhanced_no_issues_specified(cli_runner, mock_core):
    """Test sync without specifying which issues to sync."""
    with patch(
        "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
    ) as mock_gh_service_cls:
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = {
            "owner": "user",
            "repo": "repo",
        }
        mock_gh_service_cls.return_value = mock_gh_service

        result = cli_runner.invoke(
            sync_github,
            [],
            obj=mock_core,
        )

        assert result.exit_code == 1
        assert "Must specify issue_id, --all, --milestone, or --status" in result.output


def test_sync_enhanced_all_flag_no_linked_issues(cli_runner, mock_core):
    """Test sync --all when there are no linked issues."""
    mock_core.issues.all.return_value = [
        Mock(id="issue1", github_issue=None),  # Not linked
        Mock(id="issue2", github_issue=None),  # Not linked
    ]

    with patch(
        "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
    ) as mock_gh_service_cls:
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = {
            "owner": "user",
            "repo": "repo",
        }
        mock_gh_service_cls.return_value = mock_gh_service

        result = cli_runner.invoke(
            sync_github,
            ["--all"],
            obj=mock_core,
        )

        assert result.exit_code == 0
        assert "No issues to sync" in result.output


def test_sync_enhanced_dry_run_flag(cli_runner, mock_core):
    """Test that --dry-run stops after displaying report."""
    issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
    mock_core.issues.all.return_value = [issue1]

    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubSyncOrchestrator"
        ) as mock_orchestrator_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = {
            "owner": "user",
            "repo": "repo",
        }
        mock_gh_service_cls.return_value = mock_gh_service

        mock_orchestrator = Mock()
        mock_report = Mock()
        mock_report.has_conflicts.return_value = False
        mock_report.has_changes.return_value = False
        mock_orchestrator.sync_all_linked_issues.return_value = mock_report
        mock_orchestrator_cls.return_value = mock_orchestrator

        result = cli_runner.invoke(
            sync_github,
            ["--all", "--dry-run"],
            obj=mock_core,
        )

        assert result.exit_code == 0
        assert "Dry-run mode: No changes applied" in result.output
        # Should call report display method
        assert mock_report.display_brief.called


def test_sync_enhanced_verbose_flag(cli_runner, mock_core):
    """Test that --verbose calls display_verbose instead of display_brief."""
    issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
    mock_core.issues.all.return_value = [issue1]

    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubSyncOrchestrator"
        ) as mock_orchestrator_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = {
            "owner": "user",
            "repo": "repo",
        }
        mock_gh_service_cls.return_value = mock_gh_service

        mock_orchestrator = Mock()
        mock_report = Mock()
        mock_report.has_conflicts.return_value = False
        mock_report.has_changes.return_value = False
        mock_orchestrator.sync_all_linked_issues.return_value = mock_report
        mock_orchestrator_cls.return_value = mock_orchestrator

        result = cli_runner.invoke(
            sync_github,
            ["--all", "--dry-run", "--verbose"],
            obj=mock_core,
        )

        assert result.exit_code == 0
        # Should call display_verbose
        assert mock_report.display_verbose.called
        assert not mock_report.display_brief.called


def test_sync_enhanced_conflict_without_force_flag(cli_runner, mock_core):
    """Test that conflicts without --force flag exits with error."""
    issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
    mock_core.issues.all.return_value = [issue1]

    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubSyncOrchestrator"
        ) as mock_orchestrator_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = {
            "owner": "user",
            "repo": "repo",
        }
        mock_gh_service_cls.return_value = mock_gh_service

        mock_orchestrator = Mock()
        mock_report = Mock()
        mock_report.has_conflicts.return_value = True
        mock_report.has_changes.return_value = True
        mock_orchestrator.sync_all_linked_issues.return_value = mock_report
        mock_orchestrator_cls.return_value = mock_orchestrator

        result = cli_runner.invoke(
            sync_github,
            ["--all"],
            obj=mock_core,
        )

        assert result.exit_code == 1
        assert "Conflicts detected" in result.output
        assert "--force-local or --force-github" in result.output


def test_sync_enhanced_conflict_with_force_local_dry_run(cli_runner, mock_core):
    """Test that --dry-run stops before checking conflicts."""
    issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
    mock_core.issues.all = Mock(return_value=[issue1])

    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubSyncOrchestrator"
        ) as mock_orchestrator_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = {
            "owner": "user",
            "repo": "repo",
        }
        mock_gh_service_cls.return_value = mock_gh_service

        mock_orchestrator = Mock()
        mock_report = Mock()
        mock_report.has_conflicts.return_value = True
        mock_report.has_changes.return_value = True
        mock_orchestrator.sync_all_linked_issues.return_value = mock_report
        mock_orchestrator_cls.return_value = mock_orchestrator

        result = cli_runner.invoke(
            sync_github,
            ["--all", "--force-local", "--dry-run"],
            obj=mock_core,
        )

        assert result.exit_code == 0
        # In dry-run mode, we exit after report display, before conflict check
        assert "Dry-run mode" in result.output


def test_sync_enhanced_validate_only(cli_runner, mock_core):
    """Test --validate-only mode."""
    with patch(
        "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
    ) as mock_gh_service_cls:
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = {
            "owner": "user",
            "repo": "repo",
        }
        mock_gh_service_cls.return_value = mock_gh_service

        result = cli_runner.invoke(
            sync_github,
            ["--validate-only"],
            obj=mock_core,
        )

        assert result.exit_code == 0


def test_sync_enhanced_sync_by_milestone(cli_runner, mock_core):
    """Test syncing issues filtered by milestone."""
    issue1 = Mock(id="issue1", github_issue=123, title="Test 1", milestone="v1.0")
    issue2 = Mock(id="issue2", github_issue=124, title="Test 2", milestone="v1.1")
    mock_core.issues.all.return_value = [issue1, issue2]

    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubSyncOrchestrator"
        ) as mock_orchestrator_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = {
            "owner": "user",
            "repo": "repo",
        }
        mock_gh_service_cls.return_value = mock_gh_service

        mock_orchestrator = Mock()
        mock_report = Mock()
        mock_report.has_conflicts.return_value = False
        mock_report.has_changes.return_value = False
        mock_orchestrator.sync_all_linked_issues.return_value = mock_report
        mock_orchestrator_cls.return_value = mock_orchestrator

        result = cli_runner.invoke(
            sync_github,
            ["--milestone", "v1.0", "--dry-run"],
            obj=mock_core,
        )

        assert result.exit_code == 0
        assert "Will sync" in result.output


def test_sync_enhanced_sync_single_issue(cli_runner, mock_core):
    """Test syncing a single issue by ID."""
    issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
    mock_core.issues.get.return_value = issue1

    with (
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls,
        patch(
            "roadmap.adapters.cli.issues.sync.GitHubSyncOrchestrator"
        ) as mock_orchestrator_cls,
    ):
        mock_gh_service = Mock()
        mock_gh_service.get_github_config.return_value = {
            "owner": "user",
            "repo": "repo",
        }
        mock_gh_service_cls.return_value = mock_gh_service

        mock_orchestrator = Mock()
        mock_report = Mock()
        mock_report.has_conflicts.return_value = False
        mock_report.has_changes.return_value = False
        mock_orchestrator.sync_all_linked_issues.return_value = mock_report
        mock_orchestrator_cls.return_value = mock_orchestrator

        result = cli_runner.invoke(
            sync_github,
            ["issue1", "--dry-run"],
            obj=mock_core,
        )

        assert result.exit_code == 0
        assert "Will sync 1 issue(s)" in result.output
        mock_core.issues.get.assert_called_once_with("issue1")
