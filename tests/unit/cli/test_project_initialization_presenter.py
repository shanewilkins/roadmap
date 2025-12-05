"""
Unit tests for ProjectInitializationPresenter.

Tests cover:
- Displaying detected context
- Prompting for user input
- Showing project creation status and results
- Summary and next steps display
"""

from unittest.mock import patch

from roadmap.presentation.cli.presentation.project_initialization_presenter import (
    ProjectInitializationPresenter,
)


class TestProjectInitializationPresenter:
    """Tests for project initialization presenter."""

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_detected_context_with_git_repo(self, mock_console):
        """Test display of detected context with git repository."""
        detected_info = {
            "git_repo": "owner/repo",
            "project_name": "MyProject",
            "has_git": True,
            "directory": "/home/user/project",
        }

        ProjectInitializationPresenter.show_detected_context(
            detected_info, interactive=False
        )

        # Verify console was called with expected output
        calls = mock_console.print.call_args_list
        assert any("owner/repo" in str(call) for call in calls)
        assert any("MyProject" in str(call) for call in calls)

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_detected_context_without_git_repo_interactive(self, mock_console):
        """Test display of detected context without git repo in interactive mode."""
        detected_info = {
            "git_repo": None,
            "project_name": "MyProject",
            "has_git": False,
            "directory": "/home/user/project",
        }

        ProjectInitializationPresenter.show_detected_context(
            detected_info, interactive=True
        )

        # Should show recommendation to run 'git init'
        calls = mock_console.print.call_args_list
        assert any("git init" in str(call) for call in calls)

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_detected_context_without_git_repo_non_interactive(self, mock_console):
        """Test display of detected context without git repo in non-interactive mode."""
        detected_info = {
            "git_repo": None,
            "project_name": "MyProject",
            "has_git": False,
            "directory": "/home/user/project",
        }

        ProjectInitializationPresenter.show_detected_context(
            detected_info, interactive=False
        )

        # Should not show git init recommendation
        calls = mock_console.print.call_args_list
        git_init_calls = [call for call in calls if "git init" in str(call)]
        assert len(git_init_calls) == 0

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.click.prompt"
    )
    def test_prompt_project_name_interactive(self, mock_prompt):
        """Test prompting for project name in interactive mode."""
        mock_prompt.return_value = "UserEnteredName"

        result = ProjectInitializationPresenter.prompt_project_name(
            suggested_name="DefaultName", interactive=True, yes=False
        )

        assert result == "UserEnteredName"
        mock_prompt.assert_called_once()

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.click.prompt"
    )
    def test_prompt_project_name_with_yes_flag(self, mock_prompt):
        """Test that --yes flag skips prompting."""
        result = ProjectInitializationPresenter.prompt_project_name(
            suggested_name="DefaultName", interactive=True, yes=True
        )

        assert result == "DefaultName"
        mock_prompt.assert_not_called()

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.click.prompt"
    )
    def test_prompt_project_name_non_interactive(self, mock_prompt):
        """Test that non-interactive mode uses suggested name."""
        result = ProjectInitializationPresenter.prompt_project_name(
            suggested_name="DefaultName", interactive=False, yes=False
        )

        assert result == "DefaultName"
        mock_prompt.assert_not_called()

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.click.prompt"
    )
    def test_prompt_project_description_interactive(self, mock_prompt):
        """Test prompting for project description."""
        mock_prompt.return_value = "User description"

        result = ProjectInitializationPresenter.prompt_project_description(
            suggested_description="Default description", interactive=True, yes=False
        )

        assert result == "User description"
        mock_prompt.assert_called_once()

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.click.prompt"
    )
    def test_prompt_project_description_with_yes_flag(self, mock_prompt):
        """Test that --yes flag skips description prompt."""
        result = ProjectInitializationPresenter.prompt_project_description(
            suggested_description="Default", interactive=True, yes=True
        )

        assert result == "Default"
        mock_prompt.assert_not_called()

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_project_creation_status(self, mock_console):
        """Test display of project creation status."""
        ProjectInitializationPresenter.show_project_creation_status()

        calls = mock_console.print.call_args_list
        assert any("Creating main project" in str(call) for call in calls)

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_project_created(self, mock_console):
        """Test display of successful project creation."""
        project_info = {"name": "MyProject", "id": "abc123xyz"}

        ProjectInitializationPresenter.show_project_created(project_info)

        calls = mock_console.print.call_args_list
        assert any("MyProject" in str(call) for call in calls)
        assert any("abc12" in str(call) for call in calls)  # Truncated ID

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_existing_projects_single(self, mock_console):
        """Test display of single existing project."""
        projects = [{"name": "ExistingProject", "id": "existing123"}]

        ProjectInitializationPresenter.show_existing_projects(projects)

        calls = mock_console.print.call_args_list
        assert any("ExistingProject" in str(call) for call in calls)

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_existing_projects_multiple(self, mock_console):
        """Test display of multiple existing projects."""
        projects = [
            {"name": "Project1", "id": "id1123xyz"},
            {"name": "Project2", "id": "id2456uvw"},
            {"name": "Project3", "id": "id3789abc"},
        ]

        ProjectInitializationPresenter.show_existing_projects(projects)

        calls = mock_console.print.call_args_list
        assert any("Project1" in str(call) for call in calls)
        assert any("Project2" in str(call) for call in calls)
        assert any("Project3" in str(call) for call in calls)
        assert any("3 projects" in str(call) for call in calls)

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_success_summary_with_github(self, mock_console):
        """Test success summary with GitHub integration."""
        project_info = {"name": "MyProject", "id": "abc123xyz"}
        detected_info = {"has_git": True, "git_repo": "owner/repo"}

        ProjectInitializationPresenter.show_success_summary(
            ".roadmap",
            github_configured=True,
            project_info=project_info,
            detected_info=detected_info,
        )

        calls = mock_console.print.call_args_list
        call_str = str(calls)
        assert "Setup Complete" in call_str
        assert ".roadmap" in call_str
        assert "MyProject" in call_str
        assert "GitHub" in call_str

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_success_summary_without_github(self, mock_console):
        """Test success summary without GitHub integration."""
        project_info = {"name": "MyProject", "id": "abc123xyz"}
        detected_info = {"has_git": False}

        ProjectInitializationPresenter.show_success_summary(
            ".roadmap",
            github_configured=False,
            project_info=project_info,
            detected_info=detected_info,
        )

        calls = mock_console.print.call_args_list
        call_str = str(calls)
        assert "Setup Complete" in call_str
        assert "git init" in call_str

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_success_summary_no_project(self, mock_console):
        """Test success summary when no project was created."""
        detected_info = {"has_git": True}

        ProjectInitializationPresenter.show_success_summary(
            ".roadmap",
            github_configured=False,
            project_info=None,
            detected_info=detected_info,
        )

        calls = mock_console.print.call_args_list
        call_str = str(calls)
        assert "Setup Complete" in call_str

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_warning(self, mock_console):
        """Test display of warning message."""
        ProjectInitializationPresenter.show_warning(
            "Test warning", "Additional context"
        )

        calls = mock_console.print.call_args_list
        assert any("Test warning" in str(call) for call in calls)
        assert any("Additional context" in str(call) for call in calls)

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_warning_no_context(self, mock_console):
        """Test display of warning without context."""
        ProjectInitializationPresenter.show_warning("Simple warning")

        calls = mock_console.print.call_args_list
        assert any("Simple warning" in str(call) for call in calls)

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_error(self, mock_console):
        """Test display of error message."""
        ProjectInitializationPresenter.show_error("Test error message")

        calls = mock_console.print.call_args_list
        assert any("Test error message" in str(call) for call in calls)

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_success_summary_output_structure(self, mock_console):
        """Test that success summary has expected output sections."""
        project_info = {"name": "TestProj", "id": "test123xyz"}
        detected_info = {"has_git": True}

        ProjectInitializationPresenter.show_success_summary(
            ".roadmap",
            github_configured=True,
            project_info=project_info,
            detected_info=detected_info,
        )

        calls = mock_console.print.call_args_list
        call_str = str(calls)

        # Check for main sections
        assert "Created" in call_str
        assert "Next Steps" in call_str
        assert "Learn More" in call_str
        assert "Pro Tips" in call_str

    @patch(
        "roadmap.presentation.cli.presentation.project_initialization_presenter.console"
    )
    def test_show_success_summary_git_disabled_shows_tips(self, mock_console):
        """Test that git initialization tips shown when git not available."""
        detected_info = {"has_git": False}

        ProjectInitializationPresenter.show_success_summary(
            ".roadmap",
            github_configured=False,
            project_info=None,
            detected_info=detected_info,
        )

        calls = mock_console.print.call_args_list
        call_str = str(calls)

        # Should recommend git initialization
        assert "git init" in call_str
        assert "advanced features" in call_str
