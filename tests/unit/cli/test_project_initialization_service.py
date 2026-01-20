"""
Unit tests for ProjectInitializationService.

Tests cover:
- Project context detection (git, package files, directory)
- Existing project detection
- Template generation (all types)
- Project creation and file handling
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.services.project_initialization_service import (
    ProjectContextDetectionService,
    ProjectCreationService,
    ProjectDetectionService,
    ProjectTemplateService,
)
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestProjectDetectionService:
    """Tests for detecting existing projects."""

    def test_detect_existing_projects_empty_directory(self, tmp_path):
        """Test detection with no projects directory."""
        result = ProjectDetectionService.detect_existing_projects(tmp_path)
        assert result == []

    def test_detect_existing_projects_no_projects(self, tmp_path):
        """Test detection when projects directory exists but is empty."""
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()
        result = ProjectDetectionService.detect_existing_projects(projects_dir)
        assert result == []

    @patch("roadmap.core.services.project_init.detection.ProjectParser")
    def test_detect_existing_projects_with_projects(self, mock_parser, tmp_path):
        """Test detection of multiple existing projects."""
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()

        # Create project files
        (projects_dir / "proj1.md").write_text("content1")
        (projects_dir / "proj2.md").write_text("content2")

        # Mock the parser
        mock_project1 = MagicMock()
        mock_project1.name = "Project 1"
        mock_project1.id = "abc123"

        mock_project2 = MagicMock()
        mock_project2.name = "Project 2"
        mock_project2.id = "def456"

        mock_parser.parse_project_file.side_effect = [mock_project1, mock_project2]

        result = ProjectDetectionService.detect_existing_projects(projects_dir)

        assert len(result) == 2
        assert result[0]["name"] == "Project 1"
        assert result[0]["id"] == "abc123"
        assert result[1]["name"] == "Project 2"
        assert result[1]["id"] == "def456"

    @patch("roadmap.core.services.project_init.detection.ProjectParser")
    def test_detect_existing_projects_parse_error(self, mock_parser, tmp_path):
        """Test that projects that fail to parse are skipped."""
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()

        (projects_dir / "bad.md").write_text("bad content")
        (projects_dir / "good.md").write_text("good content")

        mock_good = MagicMock()
        mock_good.name = "Good Project"
        mock_good.id = "goodid"

        mock_parser.parse_project_file.side_effect = [
            Exception("Parse error"),
            mock_good,
        ]

        result = ProjectDetectionService.detect_existing_projects(projects_dir)

        assert len(result) == 1
        assert result[0]["name"] == "Good Project"


class TestProjectContextDetectionService:
    """Tests for detecting project context."""

    @patch("subprocess.run")
    def test_detect_project_context_not_in_git(self, mock_run):
        """Test detection when not in a git repository."""
        mock_run.return_value = MagicMock(returncode=1)

        result = ProjectContextDetectionService.detect_project_context()

        assert not result["has_git"]
        assert result["git_repo"] is None
        assert result["git_user"] is None
        assert result["project_name"] == Path.cwd().name

    @patch("subprocess.run")
    def test_detect_project_context_git_repo_https(self, mock_run):
        """Test detection of HTTPS git repository."""
        responses = [
            MagicMock(returncode=0),  # is_inside_work_tree
            MagicMock(
                returncode=0, stdout="https://github.com/owner/myproject.git\n"
            ),  # get-url
            MagicMock(returncode=0, stdout="John Doe\n"),  # user.name
        ]
        mock_run.side_effect = responses

        result = ProjectContextDetectionService.detect_project_context()

        assert result["has_git"]
        assert result["git_repo"] == "owner/myproject"
        assert result["project_name"] == "myproject"
        assert result["git_user"] == "John Doe"

    @patch("subprocess.run")
    def test_detect_project_context_git_repo_ssh(self, mock_run):
        """Test detection of SSH git repository."""
        responses = [
            MagicMock(returncode=0),  # is_inside_work_tree
            MagicMock(
                returncode=0, stdout="git@github.com:owner/myproject.git\n"
            ),  # get-url
            MagicMock(returncode=0, stdout="Jane Smith\n"),  # user.name
        ]
        mock_run.side_effect = responses

        result = ProjectContextDetectionService.detect_project_context()

        assert result["has_git"]
        assert result["git_repo"] == "owner/myproject"
        assert result["project_name"] == "myproject"
        assert result["git_user"] == "Jane Smith"

    @patch("subprocess.run")
    def test_detect_project_context_non_github(self, mock_run):
        """Test detection with non-GitHub repository."""
        responses = [
            MagicMock(returncode=0),  # is_inside_work_tree
            MagicMock(
                returncode=0, stdout="https://gitlab.com/owner/project.git\n"
            ),  # get-url
        ]
        mock_run.side_effect = responses

        result = ProjectContextDetectionService.detect_project_context()

        assert result["has_git"]
        assert result["git_repo"] is None  # Not a GitHub repo

    @patch("subprocess.run")
    def test_detect_project_context_from_pyproject(self, mock_run, tmp_path):
        """Test detection from pyproject.toml falls back to directory name when not in git."""
        # Create subprocess mock that returns not-in-git
        mock_run.return_value = MagicMock(returncode=1)

        # Create a pyproject.toml file
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('name = "detected-project"\n')

        # Change to temp directory with pyproject.toml
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = ProjectContextDetectionService.detect_project_context()
            # Should have detected context
            assert result["project_name"] is not None
            # Should have git detection attempted
            assert not result["has_git"]
        finally:
            os.chdir(original_cwd)

    @patch("subprocess.run")
    def test_detect_project_context_subprocess_timeout(self, mock_run):
        """Test handling of subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        result = ProjectContextDetectionService.detect_project_context()

        assert not result["has_git"]
        assert result["project_name"] == Path.cwd().name

    @patch("subprocess.run")
    def test_detect_project_context_subprocess_error(self, mock_run):
        """Test handling of subprocess errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = ProjectContextDetectionService.detect_project_context()

        assert not result["has_git"]
        assert result["project_name"] == Path.cwd().name


class TestProjectTemplateService:
    """Tests for template generation."""

    def test_generate_basic_template(self):
        """Test generation of basic template."""
        detected_info = {"git_repo": None, "git_user": "testuser"}
        content = ProjectTemplateService.generate_project_template(
            "TestProject", "A test project", "basic", detected_info
        )

        assert "TestProject" in content
        assert "A test project" in content
        assert "testuser" in content
        assert "Define project scope" in content
        assert "---" in content  # Frontmatter markers

    def test_generate_software_template(self):
        """Test generation of software template."""
        detected_info = {"git_repo": "owner/repo", "git_user": "dev"}
        content = ProjectTemplateService.generate_project_template(
            "MyApp", "My application", "software", detected_info
        )

        assert "MyApp" in content
        assert "My application" in content
        assert "owner/repo" in content
        assert "Develop core functionality" in content
        assert "Technical Stack" in content
        assert "Development Phases" in content

    def test_generate_research_template(self):
        """Test generation of research template."""
        detected_info = {"git_repo": None, "git_user": "researcher"}
        content = ProjectTemplateService.generate_project_template(
            "ResearchProject", "Research on topic X", "research", detected_info
        )

        assert "ResearchProject" in content
        assert "Research on topic X" in content
        assert "Literature review" in content
        assert "Research Questions" in content
        assert "Methodology" in content
        assert "Timeline" in content

    def test_generate_team_template(self):
        """Test generation of team template."""
        detected_info = {"git_repo": None, "git_user": "manager"}
        content = ProjectTemplateService.generate_project_template(
            "TeamProject", "Team collaboration", "team", detected_info
        )

        assert "TeamProject" in content
        assert "Team collaboration" in content
        assert "Team onboarding" in content
        assert "Team Structure" in content
        assert "Communication" in content
        assert "Development Workflow" in content

    def test_template_includes_footer(self):
        """Test that all templates include footer."""
        detected_info = {"git_repo": None, "git_user": "test"}
        for template_type in ["basic", "software", "research", "team"]:
            content = ProjectTemplateService.generate_project_template(
                "Project", "Description", template_type, detected_info
            )
            assert "Resources" in content
            assert "Notes" in content

    def test_load_custom_template_exists(self, tmp_path):
        """Test loading existing custom template."""
        template_file = tmp_path / "custom.md"
        template_file.write_text("# Custom Template\nCustom content")

        content = ProjectTemplateService.load_custom_template(str(template_file))

        assert content == "# Custom Template\nCustom content"

    def test_load_custom_template_not_found(self, tmp_path):
        """Test loading non-existent template."""
        template_path = str(tmp_path / "nonexistent.md")
        content = ProjectTemplateService.load_custom_template(template_path)

        assert content is None

    def test_load_custom_template_is_directory(self, tmp_path):
        """Test loading when path is a directory."""
        content = ProjectTemplateService.load_custom_template(str(tmp_path))

        assert content is None


class TestProjectCreationService:
    """Tests for project creation."""

    @patch("roadmap.core.services.project_init.creation.RoadmapCore")
    def test_create_project_success(self, mock_core_class, mock_roadmap_core_factory):
        """Test successful project creation."""
        # Setup mock - use fixture factory for customized mock_core
        mock_core = mock_roadmap_core_factory()

        # Create projects directory
        (mock_core.roadmap_dir / "projects").mkdir(parents=True, exist_ok=True)

        detected_info = {"git_repo": None, "git_user": "testuser"}

        result = ProjectCreationService.create_project(
            mock_core,
            "Test Project",
            "A test project",
            detected_info,
            "basic",
        )

        assert result is not None
        assert len(result["id"]) == 8  # UUID-like ID (8 chars)
        assert result["name"] == "Test Project"

    @patch("roadmap.core.services.project_init.creation.RoadmapCore")
    def test_create_project_creates_file(
        self, mock_core_class, mock_roadmap_core_factory
    ):
        """Test that project creation creates the project file."""
        # Setup mock - use fixture factory for customized mock_core
        mock_core = mock_roadmap_core_factory()

        # Create projects directory
        (mock_core.roadmap_dir / "projects").mkdir(parents=True, exist_ok=True)

        detected_info = {"git_repo": None, "git_user": "testuser"}

        result = ProjectCreationService.create_project(
            mock_core,
            "Test Project",
            "A test project",
            detected_info,
            "basic",
        )

        assert result is not None
        assert result["filename"] == f"{result['id']}-test-project.md"

        # Verify file was created
        project_file = mock_core.roadmap_dir / "projects" / result["filename"]
        assert project_file.exists()

    @patch("roadmap.core.services.project_init.creation.RoadmapCore")
    def test_create_project_file_content(
        self, mock_core_class, mock_roadmap_core_factory
    ):
        """Test that project file contains correct content."""
        # Setup mock - use fixture factory for customized mock_core
        mock_core = mock_roadmap_core_factory()

        # Create projects directory
        (mock_core.roadmap_dir / "projects").mkdir(parents=True, exist_ok=True)

        detected_info = {"git_repo": None, "git_user": "testuser"}

        result = ProjectCreationService.create_project(
            mock_core,
            "Test Project",
            "A test project",
            detected_info,
            "basic",
        )

        assert result is not None
        # Verify file content
        project_file = mock_core.roadmap_dir / "projects" / result["filename"]
        content = project_file.read_text()
        assert "Test Project" in content
        assert "A test project" in content

    @patch("roadmap.core.services.project_init.creation.RoadmapCore")
    def test_create_project_with_custom_template(
        self, mock_core_class, mock_roadmap_core_factory
    ):
        """Test project creation with custom template."""
        mock_core = mock_roadmap_core_factory()

        (mock_core.roadmap_dir / "projects").mkdir(parents=True, exist_ok=True)

        # Create custom template
        template_file = mock_core.roadmap_dir / "template.md"
        template_file.write_text("# Custom\nCustom content here")

        detected_info = {"git_repo": None, "git_user": "user"}

        result = ProjectCreationService.create_project(
            mock_core,
            "Custom Project",
            "Custom description",
            detected_info,
            "basic",
            template_path=str(template_file),
        )

        assert result is not None
        project_file = mock_core.roadmap_dir / "projects" / result["filename"]
        content = project_file.read_text()
        assert "Custom" in content
        assert "Custom content here" in content

    @patch("roadmap.core.services.project_init.creation.RoadmapCore")
    def test_create_project_with_invalid_template_fallback(
        self, mock_core_class, mock_roadmap_core_factory
    ):
        """Test that invalid custom template falls back to standard template."""
        mock_core = mock_roadmap_core_factory()

        (mock_core.roadmap_dir / "projects").mkdir(parents=True, exist_ok=True)

        detected_info = {"git_repo": None, "git_user": "user"}

        result = ProjectCreationService.create_project(
            mock_core,
            "Fallback Project",
            "Description",
            detected_info,
            "software",
            template_path="/nonexistent/path.md",
        )

        assert result is not None
        assert len(result["id"]) == 8  # UUID-like ID
        project_file = mock_core.roadmap_dir / "projects" / result["filename"]
        content = project_file.read_text()
        # Should have software template content since custom template doesn't exist
        assert "Develop core functionality" in content

    @patch("roadmap.core.services.project_init.creation.RoadmapCore")
    def test_create_project_creates_directory(self, mock_core_class, tmp_path):
        """Test that project creation creates projects directory if missing."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.roadmap_dir = tmp_path / ".roadmap"

        # Don't create projects directory
        assert not (mock_core.roadmap_dir / "projects").exists()

        detected_info = {"git_repo": None, "git_user": "user"}

        result = ProjectCreationService.create_project(
            mock_core,
            "Directory Test",
            "Test",
            detected_info,
            "basic",
        )

        assert result is not None
        # Directory should be created
        assert (mock_core.roadmap_dir / "projects").exists()

    @patch("roadmap.core.services.project_init.creation.RoadmapCore")
    def test_create_project_handles_file_write_error(self, mock_core_class, tmp_path):
        """Test graceful handling of file write errors."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.roadmap_dir = tmp_path / ".roadmap"

        # Setup directory but make it read-only to trigger error
        projects_dir = mock_core.roadmap_dir / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)

        detected_info = {"git_repo": None, "git_user": "user"}

        # Make directory read-only
        projects_dir.chmod(0o444)

        try:
            result = ProjectCreationService.create_project(
                mock_core,
                "Error Project",
                "Test",
                detected_info,
                "basic",
            )
            # Should return None on error
            assert result is None
        finally:
            # Restore permissions for cleanup
            projects_dir.chmod(0o755)
