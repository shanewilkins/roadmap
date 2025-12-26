"""Unit tests for Phase 2A-Part1: Enhanced sync command with dry-run and conflict resolution."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.issues.sync import sync_github

# mock_core fixture provided by tests.fixtures.mocks module
# Uses centralized mock_core_simple


@pytest.fixture
def mock_gh_service():
    """Provide a mock GitHub service with config."""
    service = Mock()
    service.get_github_config.return_value = {
        "owner": "user",
        "repo": "repo",
    }
    return service


@pytest.fixture
def mock_sync_report():
    """Provide a mock sync report."""
    report = Mock()
    report.has_conflicts.return_value = False
    report.has_changes.return_value = False
    return report


class TestSyncGitHubEnhancedHelp:
    """Test sync command help and basic functionality."""

    def test_help_shows_new_options(self):
        """Test that enhanced sync command help shows new options."""
        runner = CliRunner()
        result = runner.invoke(sync_github, ["--help"])

        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--verbose" in result.output
        assert "--force-local" in result.output
        assert "--force-github" in result.output
        assert "--validate-only" in result.output

    def test_no_config(self, cli_runner, mock_core):
        """Test sync when GitHub is not configured."""
        with patch(
            "roadmap.adapters.cli.issues.sync.GitHubIntegrationService"
        ) as mock_gh_service_cls:
            mock_gh_service = Mock()
            mock_gh_service.get_github_config.return_value = None
            mock_gh_service_cls.return_value = mock_gh_service

            result = cli_runner.invoke(sync_github, ["--all"], obj=mock_core)

            assert result.exit_code == 1

    def test_no_issues_specified(self, cli_runner, mock_core):
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

            result = cli_runner.invoke(sync_github, [], obj=mock_core)

            assert result.exit_code == 1
            assert (
                "Must specify issue_id, --all, --milestone, or --status"
                in result.output
            )

    def test_all_flag_no_linked_issues(self, cli_runner, mock_core):
        """Test sync --all when there are no linked issues."""
        mock_core.issues.all.return_value = [
            Mock(id="issue1", github_issue=None),
            Mock(id="issue2", github_issue=None),
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

            result = cli_runner.invoke(sync_github, ["--all"], obj=mock_core)

            assert result.exit_code == 0
            assert "No issues to sync" in result.output


class TestSyncGitHubFlags:
    """Test various sync command flags and options."""

    def _invoke_sync_with_patches(
        self,
        cli_runner,
        mock_core,
        args,
        has_conflicts=False,
        has_changes=False,
        return_issue=None,
    ):
        """Helper to invoke sync_github with standard patches."""
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
            mock_report.has_conflicts.return_value = has_conflicts
            mock_report.has_changes.return_value = has_changes
            mock_orchestrator.sync_all_linked_issues.return_value = mock_report
            mock_orchestrator_cls.return_value = mock_orchestrator

            result = cli_runner.invoke(sync_github, args, obj=mock_core)
            return result, mock_report

    def test_dry_run_flag(self, cli_runner, mock_core):
        """Test that --dry-run stops after displaying report."""
        issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
        mock_core.issues.all.return_value = [issue1]

        result, mock_report = self._invoke_sync_with_patches(
            cli_runner, mock_core, ["--all", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "Dry-run mode: No changes applied" in result.output
        assert mock_report.display_brief.called

    def test_dry_run_with_verbose(self, cli_runner, mock_core):
        """Test that --verbose calls display_verbose instead of display_brief."""
        issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
        mock_core.issues.all.return_value = [issue1]

        result, mock_report = self._invoke_sync_with_patches(
            cli_runner, mock_core, ["--all", "--dry-run", "--verbose"]
        )

        assert result.exit_code == 0
        assert mock_report.display_verbose.called
        assert not mock_report.display_brief.called

    def test_conflict_without_force_flag(self, cli_runner, mock_core):
        """Test that conflicts without --force flag exits with error."""
        issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
        mock_core.issues.all.return_value = [issue1]

        result, _ = self._invoke_sync_with_patches(
            cli_runner,
            mock_core,
            ["--all"],
            has_conflicts=True,
            has_changes=True,
        )

        assert result.exit_code == 1
        assert "Conflicts detected" in result.output
        assert "--force-local or --force-github" in result.output

    def test_conflict_with_force_local_and_dry_run(self, cli_runner, mock_core):
        """Test that --dry-run stops before checking conflicts."""
        issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
        mock_core.issues.all.return_value = [issue1]

        result, _ = self._invoke_sync_with_patches(
            cli_runner,
            mock_core,
            ["--all", "--force-local", "--dry-run"],
            has_conflicts=True,
            has_changes=True,
        )

        assert result.exit_code == 0
        assert "Dry-run mode" in result.output

    def test_validate_only_mode(self, cli_runner, mock_core):
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


class TestSyncGitHubFilters:
    """Test sync command with different filter options."""

    def _invoke_sync_with_patches(
        self,
        cli_runner,
        mock_core,
        args,
        has_conflicts=False,
        has_changes=False,
    ):
        """Helper to invoke sync_github with standard patches."""
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
            mock_report.has_conflicts.return_value = has_conflicts
            mock_report.has_changes.return_value = has_changes
            mock_orchestrator.sync_all_linked_issues.return_value = mock_report
            mock_orchestrator_cls.return_value = mock_orchestrator

            result = cli_runner.invoke(sync_github, args, obj=mock_core)
            return result, mock_report

    def test_sync_by_milestone(self, cli_runner, mock_core):
        """Test syncing issues filtered by milestone."""
        issue1 = Mock(id="issue1", github_issue=123, title="Test 1", milestone="v1.0")
        issue2 = Mock(id="issue2", github_issue=124, title="Test 2", milestone="v1.1")
        mock_core.issues.all.return_value = [issue1, issue2]

        result, _ = self._invoke_sync_with_patches(
            cli_runner,
            mock_core,
            ["--milestone", "v1.0", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "Will sync" in result.output

    def test_sync_single_issue(self, cli_runner, mock_core):
        """Test syncing a single issue by ID."""
        issue1 = Mock(id="issue1", github_issue=123, title="Test Issue")
        mock_core.issues.get.return_value = issue1

        result, _ = self._invoke_sync_with_patches(
            cli_runner,
            mock_core,
            ["issue1", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "Will sync 1 issue(s)" in result.output
        mock_core.issues.get.assert_called_once_with("issue1")
