"""Comprehensive unit tests for cleanup command module.

Tests cover cleanup logic including backup deletion, folder structure fixes,
duplicate resolution, and malformed file repair.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.infrastructure.maintenance.cleanup import (
    _build_move_list,
    _fix_malformed_files,
    _handle_check_duplicates,
    _handle_check_folders,
    _handle_check_malformed,
    _perform_folder_moves,
    _resolve_duplicates,
    _resolve_folder_issues,
    _run_backup_cleanup,
)


class TestHandleCheckFolders:
    """Test _handle_check_folders function."""

    @pytest.mark.parametrize(
        "dir_exists,has_issues,expected_method",
        [
            (False, False, "present_no_issues_dir"),
            (True, False, "present_folder_check_clean"),
            (True, True, "present_folder_issues"),
        ],
    )
    @patch("roadmap.infrastructure.maintenance.cleanup.FolderStructureValidator")
    def test_handle_check_folders_variants(
        self, mock_validator, dir_exists, has_issues, expected_method, tmp_path
    ):
        """Test folder check with directory existence and issue state combinations."""
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues" if dir_exists else tmp_path / "nonexistent"

        if dir_exists:
            issues_dir.mkdir()

        if dir_exists and has_issues:
            issues_data = {
                "misplaced": [{"issue_id": "issue-1", "current_location": "/old"}]
            }
            mock_validator.scan_for_folder_structure_issues.return_value = issues_data
        elif dir_exists:
            mock_validator.scan_for_folder_structure_issues.return_value = None

        _handle_check_folders(issues_dir, tmp_path, MagicMock(), mock_presenter)

        expected_method_obj = getattr(mock_presenter, expected_method)
        if expected_method == "present_folder_issues":
            expected_method_obj.assert_called_once()
        else:
            expected_method_obj.assert_called_once()


class TestHandleCheckDuplicates:
    """Test _handle_check_duplicates function."""

    @pytest.mark.parametrize(
        "dir_exists,has_duplicates",
        [
            (False, False),
            (True, False),
            (True, True),
        ],
    )
    @patch("roadmap.infrastructure.maintenance.cleanup.DuplicateIssuesValidator")
    def test_handle_check_duplicates_variants(
        self, mock_validator, dir_exists, has_duplicates, tmp_path
    ):
        """Test duplicate check with directory and duplicates state combinations."""
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues" if dir_exists else tmp_path / "nonexistent"

        if dir_exists:
            issues_dir.mkdir()

        if dir_exists and has_duplicates:
            duplicates_data = {"issue-1": [Path("/file1.md"), Path("/file2.md")]}
            mock_validator.scan_for_duplicate_issues.return_value = duplicates_data
        elif dir_exists:
            mock_validator.scan_for_duplicate_issues.return_value = None

        _handle_check_duplicates(issues_dir, tmp_path, mock_presenter)

        if not dir_exists:
            mock_presenter.present_no_issues_dir.assert_called_once()
        elif has_duplicates:
            mock_presenter.present_duplicate_issues.assert_called_once()
        else:
            mock_presenter.present_duplicates_check_clean.assert_called_once()


class TestHandleCheckMalformed:
    """Test _handle_check_malformed function."""

    @pytest.mark.parametrize(
        "dir_exists,has_issues,dry_run",
        [
            (False, False, False),
            (True, False, False),
            (True, True, False),
            (True, True, True),
        ],
    )
    @patch("roadmap.infrastructure.maintenance.cleanup.click.confirm")
    @patch("roadmap.infrastructure.maintenance.cleanup.DataIntegrityValidator")
    def test_handle_check_malformed_variants(
        self, mock_validator, mock_confirm, dir_exists, has_issues, dry_run, tmp_path
    ):
        """Test malformed file check with directory, issue state, and dry-run combinations."""
        mock_confirm.return_value = True
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues" if dir_exists else tmp_path / "nonexistent"

        if dir_exists:
            issues_dir.mkdir()

        if dir_exists and has_issues:
            malformed_data = {"malformed_files": ["file1.md", "file2.md"]}
            mock_validator.scan_for_data_integrity_issues.return_value = malformed_data
        elif dir_exists:
            mock_validator.scan_for_data_integrity_issues.return_value = {
                "malformed_files": []
            }

        _handle_check_malformed(
            issues_dir, tmp_path, dry_run=dry_run, force=False, presenter=mock_presenter
        )

        if not dir_exists:
            mock_presenter.present_no_issues_dir.assert_called_once()
        elif not has_issues:
            mock_presenter.present_malformed_check_clean.assert_called_once()
        elif dry_run:
            mock_presenter.present_malformed_files.assert_called_once()


class TestRunBackupCleanup:
    """Test _run_backup_cleanup function."""

    @pytest.mark.parametrize(
        "backups_exist,files_to_delete_count,dry_run,force,user_confirms",
        [
            (False, 0, False, True, False),
            (True, 0, False, True, False),
            (True, 2, True, True, False),
            (True, 1, False, False, True),
            (True, 1, False, False, False),
        ],
    )
    @patch("roadmap.infrastructure.maintenance.cleanup.BackupCleanupService")
    @patch("roadmap.infrastructure.maintenance.cleanup.click.confirm")
    def test_run_backup_cleanup_variants(
        self,
        mock_confirm,
        mock_service,
        backups_exist,
        files_to_delete_count,
        dry_run,
        force,
        user_confirms,
        tmp_path,
    ):
        """Test backup cleanup with various state and flag combinations."""
        mock_confirm.return_value = user_confirms

        if backups_exist:
            backups_dir = tmp_path / "backups"
            backups_dir.mkdir()

        mock_instance = MagicMock()
        mock_service.return_value = mock_instance

        if backups_exist and files_to_delete_count > 0:
            files_to_delete = [
                {"name": f"backup{i}.md", "size": 1024 * (i + 1)}
                for i in range(files_to_delete_count)
            ]
            mock_instance._select_backups_for_deletion.return_value = files_to_delete
            mock_instance.cleanup_backups.return_value = {
                "deleted": files_to_delete_count
            }
        else:
            mock_instance._select_backups_for_deletion.return_value = []

        mock_presenter = MagicMock()

        _run_backup_cleanup(
            tmp_path,
            keep=10,
            days=None,
            dry_run=dry_run,
            force=force,
            presenter=mock_presenter,
        )

        # Verify appropriate presenter method called
        if not backups_exist:
            mock_presenter.present_no_backups.assert_called_once()
        elif files_to_delete_count == 0:
            mock_presenter.present_no_cleanup_needed.assert_called_once()
        elif dry_run:
            mock_presenter.present_backup_cleanup_dry_run.assert_called_once()
        elif force or user_confirms:
            mock_instance.cleanup_backups.assert_called_once()
        else:
            mock_instance.cleanup_backups.assert_not_called()


class TestResolveFolderIssues:
    """Test _resolve_folder_issues function."""

    @pytest.mark.parametrize(
        "dir_exists,has_issues",
        [
            (False, False),
            (True, False),
            (True, True),
        ],
    )
    @patch("roadmap.infrastructure.maintenance.cleanup.FolderStructureValidator")
    def test_resolve_folder_issues_variants(
        self, mock_validator, dir_exists, has_issues, tmp_path
    ):
        """Test folder issue resolution with directory and issue state combinations."""
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues" if dir_exists else tmp_path / "nonexistent"

        if dir_exists:
            issues_dir.mkdir()

        if dir_exists and has_issues:
            v1_dir = tmp_path / "v1-0"
            v1_dir.mkdir()
            source_file = v1_dir / "issue-1.md"
            source_file.write_text("test")

            issues_data = {
                "misplaced": [
                    {
                        "issue_id": "issue-1",
                        "current_location": str(source_file),
                        "expected_location": str(tmp_path / "v2-0" / "issue-1.md"),
                    }
                ]
            }
            mock_validator.scan_for_folder_structure_issues.return_value = issues_data
        else:
            mock_validator.scan_for_folder_structure_issues.return_value = None

        _resolve_folder_issues(
            issues_dir, tmp_path, MagicMock(), force=True, presenter=mock_presenter
        )

        if dir_exists and has_issues:
            mock_presenter.present_folder_moves.assert_called_once()
        else:
            mock_presenter.present_folder_moves.assert_not_called()


class TestResolveDuplicates:
    """Test _resolve_duplicates function."""

    @pytest.mark.parametrize(
        "dir_exists,has_duplicates",
        [
            (False, False),
            (True, False),
            (True, True),
        ],
    )
    @patch("roadmap.infrastructure.maintenance.cleanup.DuplicateIssuesValidator")
    def test_resolve_duplicates_variants(
        self, mock_validator, dir_exists, has_duplicates, tmp_path
    ):
        """Test duplicate resolution with directory and duplicates state combinations."""
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues" if dir_exists else tmp_path / "nonexistent"

        if dir_exists:
            issues_dir.mkdir()

        if dir_exists and has_duplicates:
            file1 = tmp_path / "issue-1_v1.md"
            file2 = tmp_path / "issue-1_v2.md"
            file1.write_text("old")
            file2.write_text("new")
            file2.touch()

            duplicates_data = {"issue-1": [file1, file2]}
            mock_validator.scan_for_duplicate_issues.return_value = duplicates_data
        else:
            mock_validator.scan_for_duplicate_issues.return_value = None

        _resolve_duplicates(issues_dir, tmp_path, force=True, presenter=mock_presenter)

        if dir_exists and has_duplicates:
            mock_presenter.present_duplicate_resolution.assert_called_once()
            mock_presenter.present_duplicate_resolution_result.assert_called_once()
        else:
            mock_presenter.present_duplicate_resolution.assert_not_called()


class TestFixMalformedFiles:
    """Test _fix_malformed_files function."""

    @pytest.mark.parametrize("has_issues", [False, True])
    @patch("roadmap.infrastructure.maintenance.cleanup.DataIntegrityValidator")
    def test_fix_malformed_files_variants(self, mock_validator, has_issues, tmp_path):
        """Test malformed file fix with and without issues."""
        if has_issues:
            malformed_data = {"malformed_files": ["file1.md", "file2.md"]}
            mock_validator.scan_for_data_integrity_issues.return_value = malformed_data
        else:
            mock_validator.scan_for_data_integrity_issues.return_value = {
                "malformed_files": []
            }

        mock_presenter = MagicMock()

        _fix_malformed_files(tmp_path, mock_presenter)

        if not has_issues:
            mock_presenter.present_malformed_repair_result.assert_not_called()

    @pytest.mark.parametrize("num_fixed", [1, 2])
    @patch("roadmap.infrastructure.maintenance.cleanup.FileRepairService")
    @patch("roadmap.infrastructure.maintenance.cleanup.DataIntegrityValidator")
    def test_fix_malformed_files_with_repair(
        self, mock_validator, mock_repair_service, num_fixed, tmp_path
    ):
        """Test malformed file repair with various fix counts."""
        malformed_data = {"malformed_files": ["file1.md", "file2.md"]}
        mock_validator.scan_for_data_integrity_issues.return_value = malformed_data

        mock_repair_instance = MagicMock()
        mock_repair_service.return_value = mock_repair_instance
        mock_repair_instance.repair_files.return_value = {"fixed": num_fixed}

        mock_presenter = MagicMock()

        _fix_malformed_files(tmp_path, mock_presenter)

        mock_repair_instance.repair_files.assert_called_once_with(
            tmp_path, ["file1.md", "file2.md"], dry_run=False
        )
        mock_presenter.present_malformed_repair_result.assert_called_once()


class TestCleanupIntegration:
    """Integration tests for cleanup functions."""

    @patch("roadmap.infrastructure.maintenance.cleanup.FolderStructureValidator")
    def test_cleanup_workflow_with_issues(self, mock_validator, tmp_path):
        """Test complete cleanup workflow with multiple issues."""
        issues_data = {
            "misplaced": [
                {
                    "issue_id": "issue-1",
                    "current_location": str(tmp_path / "old" / "issue-1.md"),
                    "expected_location": str(tmp_path / "new" / "issue-1.md"),
                }
            ]
        }
        mock_validator.scan_for_folder_structure_issues.return_value = issues_data

        old_dir = tmp_path / "old"
        old_dir.mkdir()
        (old_dir / "issue-1.md").write_text("test")

        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        mock_presenter = MagicMock()

        _resolve_folder_issues(
            issues_dir, tmp_path, MagicMock(), force=True, presenter=mock_presenter
        )

        mock_presenter.present_folder_moves.assert_called_once()

    def test_build_and_perform_moves_integration(self, tmp_path):
        """Integration test for building and performing moves."""
        source1 = tmp_path / "source1" / "file1.md"
        source2 = tmp_path / "source2" / "file2.md"
        source1.parent.mkdir()
        source2.parent.mkdir()
        source1.write_text("content1")
        source2.write_text("content2")

        issues_data = {
            "misplaced": [
                {
                    "issue_id": "issue-1",
                    "current_location": str(source1),
                    "expected_location": str(tmp_path / "dest1" / "file1.md"),
                },
                {
                    "issue_id": "issue-2",
                    "current_location": str(source2),
                    "expected_location": str(tmp_path / "dest2" / "file2.md"),
                },
            ]
        }

        moves = _build_move_list(tmp_path, issues_data)
        assert len(moves) == 2

        moved, failed = _perform_folder_moves(moves)

        assert moved == 2
        assert failed == 0
        assert (tmp_path / "dest1" / "file1.md").exists()
        assert (tmp_path / "dest2" / "file2.md").exists()
