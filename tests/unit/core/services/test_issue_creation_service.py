"""Tests for issue creation service."""

from unittest.mock import MagicMock, patch

import click
import pytest

from roadmap.common.constants import IssueType, Priority
from roadmap.core.services.issue_creation_service import IssueCreationService
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestIssueCreationService:
    """Test IssueCreationService class."""

    @pytest.fixture
    def mock_core(self, mock_core_initialized):
        """Create mock RoadmapCore with git and team services.

        Uses centralized mock_core_initialized and adds service-specific setup.
        """
        mock_core_initialized.git = TestDataFactory.create_mock_core(
            is_initialized=True
        )
        mock_core_initialized.team = TestDataFactory.create_mock_core(
            is_initialized=True
        )
        return mock_core_initialized

    @pytest.fixture
    def service(self, mock_core):
        """Create a service instance."""
        return IssueCreationService(mock_core)

    @pytest.fixture
    def mock_issue(self):
        """Create a mock issue object."""
        issue = TestDataFactory.create_mock_core(is_initialized=True)
        issue.id = "issue-1"
        issue.title = "Test Issue"
        issue.issue_type = IssueType.FEATURE
        issue.priority = Priority.MEDIUM
        issue.assignee = "test-user"
        issue.estimated_hours = 5
        issue.estimated_time_display = "5 hours"
        issue.filename = "issue-1.md"
        issue.depends_on = []
        issue.blocks = []
        return issue

    def test_service_init(self, service, mock_core):
        """Test service initialization."""
        assert service.core == mock_core
        assert service._console is not None

    def test_resolve_and_validate_assignee_provided(self, service, mock_core):
        """Test resolving assignee when provided."""
        mock_core.team.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "test-user"

        result = service.resolve_and_validate_assignee("test-user")

        assert result == "test-user"
        mock_core.team.validate_assignee.assert_called_once_with("test-user")

    def test_resolve_and_validate_assignee_auto_detect(self, service, mock_core):
        """Test auto-detecting assignee from git."""
        mock_core.git.get_current_user.return_value = "git-user"
        mock_core.team.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "git-user"

        result = service.resolve_and_validate_assignee(None, auto_detect=True)

        assert result == "git-user"
        mock_core.git.get_current_user.assert_called_once()

    def test_resolve_and_validate_assignee_no_detection(self, service, mock_core):
        """Test when assignee not provided and auto_detect is False."""
        result = service.resolve_and_validate_assignee(None, auto_detect=False)

        assert result is None

    def test_resolve_and_validate_assignee_invalid(self, service, mock_core):
        """Test assignee validation failure."""
        mock_core.team.validate_assignee.return_value = (False, "User not found")

        with pytest.raises(click.Abort):
            service.resolve_and_validate_assignee("invalid-user")

    def test_resolve_and_validate_assignee_with_warning(self, service, mock_core):
        """Test assignee validation with warning."""
        mock_core.team.validate_assignee.return_value = (True, "Warning: User inactive")
        mock_core.team.get_canonical_assignee.return_value = "test-user"

        result = service.resolve_and_validate_assignee("test-user")

        assert result == "test-user"

    def test_resolve_and_validate_assignee_canonical_conversion(
        self, service, mock_core
    ):
        """Test canonical name conversion."""
        mock_core.team.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "canonical-user"

        result = service.resolve_and_validate_assignee("alias-user")

        assert result == "canonical-user"

    def test_create_branch_for_issue_not_git_repo(self, service, mock_core, mock_issue):
        """Test branch creation when not in git repo."""
        mock_core.git.is_git_repository.return_value = False

        success, branch_name = service.create_branch_for_issue(mock_issue)

        assert not success
        assert branch_name is None

    def test_create_branch_for_issue_safe_create_success(
        self, service, mock_core, mock_issue
    ):
        """Test successful safe branch creation."""
        mock_core.git.is_git_repository.return_value = True
        mock_core.git.suggest_branch_name.return_value = "issue-1-test"
        mock_core.git.create_branch_for_issue.return_value = True

        success, branch_name = service.create_branch_for_issue(
            mock_issue, checkout=True
        )

        assert success
        assert branch_name == "issue-1-test"

    def test_create_branch_for_issue_explicit_name(
        self, service, mock_core, mock_issue
    ):
        """Test branch creation with explicit name."""
        mock_core.git.is_git_repository.return_value = True
        mock_core.git.create_branch_for_issue.return_value = True

        success, branch_name = service.create_branch_for_issue(
            mock_issue, branch_name="custom-branch"
        )

        assert branch_name == "custom-branch"

    def test_create_branch_for_issue_with_uncommitted_changes(
        self, service, mock_core, mock_issue
    ):
        """Test branch creation fails with uncommitted changes."""
        mock_core.git.is_git_repository.return_value = True
        mock_core.git.suggest_branch_name.return_value = "issue-1-test"
        mock_core.git.create_branch_for_issue.return_value = False
        mock_core.git._run_git_command.return_value = "M  file.py\n"

        success, branch_name = service.create_branch_for_issue(mock_issue)

        assert not success

    def test_create_branch_for_issue_no_checkout(self, service, mock_core, mock_issue):
        """Test branch creation without checkout."""
        mock_core.git.is_git_repository.return_value = True
        mock_core.git.suggest_branch_name.return_value = "issue-1-test"
        mock_core.git.create_branch_for_issue.return_value = True

        success, branch_name = service.create_branch_for_issue(
            mock_issue, checkout=False
        )

        assert success
        assert branch_name == "issue-1-test"

    def test_has_uncommitted_changes_true(self, service, mock_core):
        """Test detecting uncommitted changes."""
        mock_core.git._run_git_command.return_value = "M  file.py\nA  newfile.py"

        result = service._has_uncommitted_changes()

        assert result

    def test_has_uncommitted_changes_false(self, service, mock_core):
        """Test no uncommitted changes."""
        mock_core.git._run_git_command.return_value = ""

        result = service._has_uncommitted_changes()

        assert not result

    def test_has_uncommitted_changes_exception(self, service, mock_core):
        """Test exception handling in uncommitted changes check."""
        mock_core.git._run_git_command.side_effect = Exception("Git error")

        result = service._has_uncommitted_changes()

        assert not result

    def test_try_safe_create_branch_success(self, service, mock_core, mock_issue):
        """Test safe branch creation success."""
        mock_core.git.create_branch_for_issue.return_value = True

        result = service._try_safe_create_branch(mock_issue, True, False)

        assert result

    def test_try_safe_create_branch_type_error_fallback(
        self, service, mock_core, mock_issue
    ):
        """Test type error fallback in safe branch creation."""
        # First call raises TypeError, second succeeds
        mock_core.git.create_branch_for_issue.side_effect = [
            TypeError("force not supported"),
            True,
        ]

        result = service._try_safe_create_branch(mock_issue, True, True)

        assert result

    def test_try_safe_create_branch_all_failures(self, service, mock_core, mock_issue):
        """Test all attempts fail in safe branch creation."""
        mock_core.git.create_branch_for_issue.side_effect = TypeError("Not supported")

        result = service._try_safe_create_branch(mock_issue, True, False)

        assert not result

    def test_try_direct_git_command_success(self, service, mock_core):
        """Test direct git command success."""
        mock_core.git._run_git_command.return_value = "Already on 'branch-name'"

        result = service._try_direct_git_command("test-branch", True)

        assert result

    def test_try_direct_git_command_branch_exists(self, service, mock_core):
        """Test branch already exists."""
        mock_core.git._run_git_command.side_effect = [
            None,
            "ref: refs/heads/test-branch",
        ]

        result = service._try_direct_git_command("test-branch", True)

        assert result

    def test_try_direct_git_command_exception(self, service, mock_core):
        """Test exception in direct git command."""
        mock_core.git._run_git_command.side_effect = Exception("Git error")

        result = service._try_direct_git_command("test-branch", True)

        assert not result

    @patch("subprocess.run")
    def test_try_subprocess_git_success(self, mock_subprocess, service, mock_core):
        """Test subprocess git success."""
        mock_subprocess.return_value = MagicMock()
        mock_core.root_path = "/repo"

        result = service._try_subprocess_git("test-branch", True)

        assert result
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    def test_try_subprocess_git_failure(self, mock_subprocess, service, mock_core):
        """Test subprocess git failure."""
        mock_subprocess.side_effect = Exception("Git command failed")

        result = service._try_subprocess_git("test-branch", True)

        assert not result

    def test_show_branch_success_message(self, service):
        """Test branch success message display."""
        # This tests that the method runs without error
        service._show_branch_success_message("test-branch", True)
        service._show_branch_success_message("test-branch", False)
        # Display methods don't return values, just verify no exception
        assert True

    def test_format_created_issue_display_basic(self, service, mock_issue):
        """Test basic issue display formatting."""
        # Verify method runs without error and doesn't crash
        service.format_created_issue_display(mock_issue)
        assert True

    def test_format_created_issue_display_with_milestone(self, service, mock_issue):
        """Test issue display with milestone."""
        service.format_created_issue_display(mock_issue, milestone="v1.0")
        assert True

    def test_format_created_issue_display_with_dependencies(self, service, mock_issue):
        """Test issue display with dependencies."""
        mock_issue.depends_on = ["issue-2", "issue-3"]
        mock_issue.blocks = ["issue-4"]

        service.format_created_issue_display(mock_issue)
        assert True

    def test_format_created_issue_display_no_assignee(self, service, mock_issue):
        """Test issue display without assignee."""
        mock_issue.assignee = None

        service.format_created_issue_display(mock_issue)
        assert True

    def test_format_created_issue_display_no_estimate(self, service, mock_issue):
        """Test issue display without estimate."""
        mock_issue.estimated_hours = None

        service.format_created_issue_display(mock_issue)
        assert True


class TestIssueCreationServiceIntegration:
    """Integration tests for issue creation service."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = TestDataFactory.create_mock_core(is_initialized=True)
        core.git = TestDataFactory.create_mock_core(is_initialized=True)
        core.team = TestDataFactory.create_mock_core(is_initialized=True)
        core.root_path = "/repo"
        return core

    def test_full_issue_creation_workflow(self, mock_core):
        """Test complete issue creation workflow."""
        service = IssueCreationService(mock_core)

        # Setup
        mock_core.git.get_current_user.return_value = "test-user"
        mock_core.team.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "test-user"
        mock_core.git.is_git_repository.return_value = True
        mock_core.git.suggest_branch_name.return_value = "issue-1-feature"
        mock_core.git.create_branch_for_issue.return_value = True

        # Create mock issue
        issue = MagicMock()
        issue.id = "issue-1"
        issue.title = "New Feature"
        issue.issue_type = IssueType.FEATURE
        issue.priority = Priority.HIGH
        issue.assignee = "test-user"
        issue.estimated_hours = 8
        issue.estimated_time_display = "8 hours"
        issue.filename = "issue-1.md"
        issue.depends_on = []
        issue.blocks = []

        # Test assignee resolution
        assignee = service.resolve_and_validate_assignee(None, auto_detect=True)
        assert assignee == "test-user"

        # Test branch creation
        success, branch_name = service.create_branch_for_issue(issue)
        assert success
        assert branch_name == "issue-1-feature"

        # Test display
        service.format_created_issue_display(issue, milestone="v1.0")

    def test_assignee_resolution_with_canonical_mapping(self, mock_core):
        """Test assignee resolution with canonical mapping."""
        service = IssueCreationService(mock_core)

        mock_core.team.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "john-doe"

        result = service.resolve_and_validate_assignee("jdoe")

        assert result == "john-doe"
        mock_core.team.validate_assignee.assert_called_once_with("jdoe")

    def test_branch_creation_fallback_strategies(self, mock_core):
        """Test branch creation with fallback strategies."""
        service = IssueCreationService(mock_core)

        issue = MagicMock()
        issue.id = "issue-1"

        # First attempt fails, second succeeds
        mock_core.git.is_git_repository.return_value = True
        mock_core.git.suggest_branch_name.return_value = "issue-1"
        mock_core.git.create_branch_for_issue.return_value = False
        mock_core.git._run_git_command.return_value = ""  # No uncommitted changes

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock()
            success, branch_name = service.create_branch_for_issue(issue)

            # Should succeed via subprocess fallback
            assert branch_name is not None

    def test_multiple_issues_creation_sequence(self, mock_core):
        """Test creating multiple issues in sequence."""
        service = IssueCreationService(mock_core)

        mock_core.git.is_git_repository.return_value = True
        mock_core.git.create_branch_for_issue.return_value = True
        mock_core.team.validate_assignee.return_value = (True, None)
        mock_core.team.get_canonical_assignee.return_value = "user"

        for i in range(1, 4):
            issue = MagicMock()
            issue.id = f"issue-{i}"
            issue.title = f"Feature {i}"
            issue.issue_type = IssueType.FEATURE
            issue.priority = Priority.MEDIUM
            issue.assignee = f"user-{i}"
            issue.estimated_hours = 5
            issue.estimated_time_display = "5 hours"
            issue.filename = f"issue-{i}.md"
            issue.depends_on = []
            issue.blocks = []

            mock_core.git.suggest_branch_name.return_value = f"issue-{i}"

            assignee = service.resolve_and_validate_assignee(f"user-{i}")
            success, branch = service.create_branch_for_issue(issue)

            assert assignee is not None
            assert success

    def test_issue_with_dependencies_display(self, mock_core):
        """Test displaying issue with complex dependencies."""
        service = IssueCreationService(mock_core)

        issue = MagicMock()
        issue.id = "issue-1"
        issue.title = "Complex Task"
        issue.issue_type = IssueType.BUG
        issue.priority = Priority.HIGH
        issue.assignee = "lead"
        issue.estimated_hours = 12
        issue.estimated_time_display = "12 hours"
        issue.filename = "issue-1.md"
        issue.depends_on = ["issue-2", "issue-3", "issue-4"]
        issue.blocks = ["issue-5", "issue-6"]

        service.format_created_issue_display(issue, milestone="v2.0")
        assert True
