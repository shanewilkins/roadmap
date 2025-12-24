"""Error path tests for projects/restore.py - Phase 10a Tier 1 coverage expansion.

This module tests error handling and exception paths in the restore project command,
focusing on scenarios like missing files, permission errors, parsing failures, etc.

Currently restore.py has 32% coverage (75% uncovered).
Target after Phase 10a: 85%+ coverage
"""

from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.cli.projects.restore import (
    _check_archive_exists,
    _find_archived_project,
    _get_archived_projects,
    _restore_multiple_projects,
    _restore_project_file,
    _restore_single_project,
    _validate_restore_arguments,
)

# ========== Unit Tests: Validation & Argument Checking ==========


class TestValidateRestoreArguments:
    """Test argument validation for restore project command."""

    @patch("roadmap.adapters.cli.projects.restore.console")
    def test_validation_fails_when_no_project_name_and_no_all_flag(self, mock_console):
        """Test that validation fails when neither project name nor --all is provided."""
        result = _validate_restore_arguments(None, False)
        assert result is False
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Specify a project name or use --all" in call_args

    @patch("roadmap.adapters.cli.projects.restore.console")
    def test_validation_fails_when_both_project_name_and_all_flag(self, mock_console):
        """Test that validation fails when both project name and --all flag are provided."""
        result = _validate_restore_arguments("test-project", True)
        assert result is False
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Cannot specify project name with --all" in call_args

    def test_validation_succeeds_with_project_name_only(self):
        """Test that validation succeeds with just a project name."""
        result = _validate_restore_arguments("test-project", False)
        assert result is True

    def test_validation_succeeds_with_all_flag_only(self):
        """Test that validation succeeds with just the --all flag."""
        result = _validate_restore_arguments(None, True)
        assert result is True


# ========== Unit Tests: Archive Directory Checks ==========


class TestCheckArchiveExists:
    """Test archive directory existence checking."""

    @patch("roadmap.adapters.cli.projects.restore.console")
    def test_returns_false_when_archive_dir_does_not_exist(
        self, mock_console, tmp_path
    ):
        """Test that check returns False when archive directory doesn't exist."""
        non_existent_dir = tmp_path / "non_existent"
        result = _check_archive_exists(non_existent_dir)
        assert result is False
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "No archived projects found" in call_args

    def test_returns_true_when_archive_dir_exists(self, tmp_path):
        """Test that check returns True when archive directory exists."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        result = _check_archive_exists(archive_dir)
        assert result is True


# ========== Unit Tests: Get Archived Projects ==========


class TestGetArchivedProjects:
    """Test retrieval of archived projects."""

    @patch("roadmap.adapters.cli.projects.restore.console")
    def test_returns_none_when_no_archived_files(self, mock_console, tmp_path):
        """Test that None is returned when archive directory is empty."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        result = _get_archived_projects(archive_dir)
        assert result is None
        # Should print message about no projects
        assert mock_console.print.called

    def test_parses_all_valid_archived_projects(self, tmp_path):
        """Test that all valid archived project files are parsed."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        # Create mock project files
        project_file1 = archive_dir / "project1.md"
        project_file2 = archive_dir / "project2.md"
        project_file1.write_text("id: p1\nname: Project 1")
        project_file2.write_text("id: p2\nname: Project 2")

        with patch(
            "roadmap.adapters.cli.projects.restore.ProjectParser"
        ) as mock_parser:
            mock_project1 = Mock()
            mock_project1.id = "p1"
            mock_project1.name = "Project 1"

            mock_project2 = Mock()
            mock_project2.id = "p2"
            mock_project2.name = "Project 2"

            mock_parser.parse_project_file.side_effect = [
                mock_project1,
                mock_project2,
            ]

            result = _get_archived_projects(archive_dir)

            assert result is not None
            assert len(result) == 2
            assert result[0][1] == "p1"
            assert result[0][2] == "Project 1"
            assert result[1][1] == "p2"
            assert result[1][2] == "Project 2"

    @patch("roadmap.adapters.cli.projects.restore.handle_restore_parse_error")
    def test_handles_parse_errors_gracefully(self, mock_error_handler, tmp_path):
        """Test that parse errors are handled without stopping enumeration."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        # Create files
        project_file1 = archive_dir / "project1.md"
        project_file2 = archive_dir / "project2.md"
        project_file1.write_text("id: p1\nname: Project 1")
        project_file2.write_text("id: p2\nname: Project 2")

        with patch(
            "roadmap.adapters.cli.projects.restore.ProjectParser"
        ) as mock_parser:
            mock_project2 = Mock()
            mock_project2.id = "p2"
            mock_project2.name = "Project 2"

            # First parse fails, second succeeds
            mock_parser.parse_project_file.side_effect = [
                Exception("Parse error on p1"),
                mock_project2,
            ]

            result = _get_archived_projects(archive_dir)

            # Should only return the successfully parsed project
            assert result is not None
            assert len(result) == 1
            assert result[0][1] == "p2"
            # Error handler should have been called
            mock_error_handler.assert_called_once()

    @patch("roadmap.adapters.cli.projects.restore.handle_restore_parse_error")
    def test_returns_none_when_all_projects_fail_to_parse(
        self, mock_error_handler, tmp_path
    ):
        """Test that None is returned when all projects fail to parse."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        project_file = archive_dir / "project1.md"
        project_file.write_text("invalid")

        with patch(
            "roadmap.adapters.cli.projects.restore.ProjectParser"
        ) as mock_parser:
            mock_parser.parse_project_file.side_effect = Exception("Parse error")

            result = _get_archived_projects(archive_dir)

            assert result is None


# ========== Unit Tests: Find Archived Project ==========


class TestFindArchivedProject:
    """Test finding a specific archived project by name."""

    def test_finds_project_by_name(self, tmp_path):
        """Test that project is found by name."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        project_file = archive_dir / "project1.md"
        project_file.write_text("id: p1\nname: Target Project")

        with patch(
            "roadmap.adapters.cli.projects.restore.ProjectParser"
        ) as mock_parser:
            mock_project = Mock()
            mock_project.name = "Target Project"
            mock_parser.parse_project_file.return_value = mock_project

            result = _find_archived_project(archive_dir, "Target Project")

            assert result == project_file

    def test_returns_none_when_project_not_found(self, tmp_path):
        """Test that None is returned when project doesn't exist."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        project_file = archive_dir / "project1.md"
        project_file.write_text("id: p1\nname: Other Project")

        with patch(
            "roadmap.adapters.cli.projects.restore.ProjectParser"
        ) as mock_parser:
            mock_project = Mock()
            mock_project.name = "Other Project"
            mock_parser.parse_project_file.return_value = mock_project

            result = _find_archived_project(archive_dir, "Target Project")

            assert result is None

    @patch("roadmap.adapters.cli.projects.restore.handle_cli_error")
    def test_handles_parse_errors_and_continues_searching(
        self, mock_error_handler, tmp_path
    ):
        """Test that parse errors don't stop searching for other projects."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        file1 = archive_dir / "aproject1.md"  # Alphabetically first
        file2 = archive_dir / "bproject2.md"  # Alphabetically second
        file1.write_text("id: p1")
        file2.write_text("id: p2\nname: Target Project")

        with patch(
            "roadmap.adapters.cli.projects.restore.ProjectParser"
        ) as mock_parser:

            def parse_side_effect(filepath):
                if filepath == file1:
                    raise Exception("Parse error on file1")
                mock_proj = Mock()
                mock_proj.name = "Target Project"
                return mock_proj

            mock_parser.parse_project_file.side_effect = parse_side_effect

            result = _find_archived_project(archive_dir, "Target Project")

            assert result == file2
            # Error handler should have been called once
            mock_error_handler.assert_called_once()


# ========== Unit Tests: Restore Project File ==========


class TestRestoreProjectFile:
    """Test individual project file restoration."""

    def test_moves_file_from_archive_to_active(self, tmp_path):
        """Test that file is moved from archive to active directory."""
        archive_dir = tmp_path / "archive"
        active_dir = tmp_path / "active"
        archive_dir.mkdir()
        active_dir.mkdir()

        archive_file = archive_dir / "project.md"
        archive_file.write_text("project data")

        mock_core = Mock()
        mock_core.db.mark_project_archived = Mock()

        _restore_project_file(mock_core, archive_file, active_dir, "p1")

        # File should be moved to active
        assert not archive_file.exists()
        assert (active_dir / "project.md").exists()
        # Database should be updated
        mock_core.db.mark_project_archived.assert_called_once_with("p1", archived=False)

    @patch("roadmap.adapters.cli.projects.restore.console")
    def test_handles_database_error_gracefully(self, mock_console, tmp_path):
        """Test that database errors are handled with warning."""
        archive_dir = tmp_path / "archive"
        active_dir = tmp_path / "active"
        archive_dir.mkdir()
        active_dir.mkdir()

        archive_file = archive_dir / "project.md"
        archive_file.write_text("project data")

        mock_core = Mock()
        mock_core.db.mark_project_archived.side_effect = Exception("DB error")

        _restore_project_file(mock_core, archive_file, active_dir, "p1")

        # File should still be moved
        assert not archive_file.exists()
        assert (active_dir / "project.md").exists()
        # Warning should be printed
        assert mock_console.print.called
        call_args = mock_console.print.call_args[0][0]
        assert "Failed to mark project as restored" in call_args


# ========== Integration Tests: Single Project Restore ==========


class TestRestoreSingleProject:
    """Test restoring a single archived project."""

    @patch("roadmap.adapters.cli.projects.restore.console")
    def test_returns_false_when_archived_project_not_found(
        self, mock_console, tmp_path
    ):
        """Test that restore fails when archived project doesn't exist."""
        archive_dir = tmp_path / "archive"
        active_dir = tmp_path / "active"
        archive_dir.mkdir()
        active_dir.mkdir()

        mock_core = Mock()

        result = _restore_single_project(
            mock_core,
            archive_dir,
            active_dir,
            "Missing Project",
            dry_run=False,
            force=True,
        )

        assert result is False
        assert mock_console.print.called
        call_args = mock_console.print.call_args[0][0]
        assert "not found" in call_args

    @patch("roadmap.adapters.cli.projects.restore.console")
    def test_returns_false_when_project_already_exists_in_active(
        self, mock_console, tmp_path
    ):
        """Test that restore fails when project already exists in active."""
        archive_dir = tmp_path / "archive"
        active_dir = tmp_path / "active"
        archive_dir.mkdir()
        active_dir.mkdir()

        archive_file = archive_dir / "project.md"
        archive_file.write_text("archived")
        active_file = active_dir / "project.md"
        active_file.write_text("active")

        mock_core = Mock()

        with patch(
            "roadmap.adapters.cli.projects.restore.ProjectParser"
        ) as mock_parser:
            mock_project = Mock()
            mock_project.name = "Test Project"
            mock_parser.parse_project_file.return_value = mock_project

            with patch(
                "roadmap.adapters.cli.projects.restore._find_archived_project",
                return_value=archive_file,
            ):
                result = _restore_single_project(
                    mock_core,
                    archive_dir,
                    active_dir,
                    "Test Project",
                    dry_run=False,
                    force=True,
                )

                assert result is False
                assert mock_console.print.called

    @patch("roadmap.adapters.cli.projects.restore.console")
    def test_returns_false_when_project_parse_fails(self, mock_console, tmp_path):
        """Test that restore fails when project file parsing fails."""
        archive_dir = tmp_path / "archive"
        active_dir = tmp_path / "active"
        archive_dir.mkdir()
        active_dir.mkdir()

        archive_file = archive_dir / "project.md"
        archive_file.write_text("invalid")

        mock_core = Mock()

        with patch(
            "roadmap.adapters.cli.projects.restore.ProjectParser"
        ) as mock_parser:
            mock_parser.parse_project_file.side_effect = Exception("Parse failed")

            with patch(
                "roadmap.adapters.cli.projects.restore._find_archived_project",
                return_value=archive_file,
            ):
                result = _restore_single_project(
                    mock_core,
                    archive_dir,
                    active_dir,
                    "Test Project",
                    dry_run=False,
                    force=True,
                )

                assert result is False
                assert mock_console.print.called
                call_args = mock_console.print.call_args[0][0]
                assert "Failed to parse" in call_args

    @patch("roadmap.adapters.cli.projects.restore.console")
    @patch("roadmap.adapters.cli.projects.restore._restore_project_file")
    def test_succeeds_restoring_single_project_with_force(
        self, mock_restore_file, mock_console, tmp_path
    ):
        """Test successful restore of single project with force flag."""
        archive_dir = tmp_path / "archive"
        active_dir = tmp_path / "active"
        archive_dir.mkdir()
        active_dir.mkdir()

        archive_file = archive_dir / "project.md"
        archive_file.write_text("project data")

        mock_core = Mock()

        with patch(
            "roadmap.adapters.cli.projects.restore.ProjectParser"
        ) as mock_parser:
            mock_project = Mock()
            mock_project.id = "p1"
            mock_project.name = "Test Project"
            mock_parser.parse_project_file.return_value = mock_project

            with patch(
                "roadmap.adapters.cli.projects.restore._find_archived_project",
                return_value=archive_file,
            ):
                result = _restore_single_project(
                    mock_core,
                    archive_dir,
                    active_dir,
                    "Test Project",
                    dry_run=False,
                    force=True,
                )

                assert result is True
                mock_restore_file.assert_called_once()
                assert mock_console.print.called


# ========== Integration Tests: Multiple Projects Restore ==========


class TestRestoreMultipleProjects:
    """Test restoring multiple archived projects."""

    @patch("roadmap.adapters.cli.projects.restore.console")
    @patch("roadmap.adapters.cli.projects.restore._restore_project_file")
    def test_succeeds_restoring_all_projects_with_force(
        self, mock_restore_file, mock_console, tmp_path
    ):
        """Test successful restore of all projects with force flag."""
        archive_dir = tmp_path / "archive"
        active_dir = tmp_path / "active"
        archive_dir.mkdir()
        active_dir.mkdir()

        file1 = archive_dir / "project1.md"
        file2 = archive_dir / "project2.md"
        file1.write_text("p1")
        file2.write_text("p2")

        projects_info = [
            (file1, "p1", "Project 1"),
            (file2, "p2", "Project 2"),
        ]

        mock_core = Mock()

        result = _restore_multiple_projects(
            mock_core,
            archive_dir,
            active_dir,
            projects_info,
            dry_run=False,
            force=True,
        )

        assert result is True
        assert mock_restore_file.call_count == 2
        assert mock_console.print.called

    @patch("roadmap.adapters.cli.projects.restore.console")
    @patch("roadmap.adapters.cli.projects.restore._restore_project_file")
    def test_skips_projects_that_already_exist_in_active(
        self, mock_restore_file, mock_console, tmp_path
    ):
        """Test that projects already in active are skipped."""
        archive_dir = tmp_path / "archive"
        active_dir = tmp_path / "active"
        archive_dir.mkdir()
        active_dir.mkdir()

        file1 = archive_dir / "project1.md"
        file2 = archive_dir / "project2.md"
        file1.write_text("p1")
        file2.write_text("p2")

        # project1 already exists in active
        (active_dir / "project1.md").write_text("existing")

        projects_info = [
            (file1, "p1", "Project 1"),
            (file2, "p2", "Project 2"),
        ]

        mock_core = Mock()

        result = _restore_multiple_projects(
            mock_core,
            archive_dir,
            active_dir,
            projects_info,
            dry_run=False,
            force=True,
        )

        assert result is True
        # Only project2 should be restored
        assert mock_restore_file.call_count == 1

    @patch("roadmap.adapters.cli.projects.restore.console")
    def test_dry_run_shows_projects_without_modifying(self, mock_console, tmp_path):
        """Test that dry-run mode shows what would happen without changes."""
        archive_dir = tmp_path / "archive"
        active_dir = tmp_path / "active"
        archive_dir.mkdir()
        active_dir.mkdir()

        file1 = archive_dir / "project1.md"
        file1.write_text("p1")

        projects_info = [
            (file1, "p1", "Project 1"),
        ]

        mock_core = Mock()

        result = _restore_multiple_projects(
            mock_core,
            archive_dir,
            active_dir,
            projects_info,
            dry_run=True,
            force=True,
        )

        assert result is True
        # File should NOT be moved in dry-run
        assert file1.exists()
        assert not (active_dir / "project1.md").exists()
        # Should show DRY RUN message
        assert mock_console.print.called
        call_args_list = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("DRY RUN" in str(arg) for arg in call_args_list)


pytestmark = pytest.mark.unit
