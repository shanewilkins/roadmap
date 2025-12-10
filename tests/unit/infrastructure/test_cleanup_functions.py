"""Comprehensive unit tests for cleanup command module.

Tests cover cleanup logic including backup deletion, folder structure fixes,
duplicate resolution, and malformed file repair.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from roadmap.infrastructure.maintenance.cleanup import (
    _build_move_list,
    _confirm_folder_moves,
    _fix_malformed_files,
    _handle_check_duplicates,
    _handle_check_folders,
    _handle_check_malformed,
    _perform_folder_moves,
    _resolve_duplicates,
    _resolve_folder_issues,
    _run_backup_cleanup,
)


class TestBuildMoveList:
    """Test _build_move_list function."""

    def test_build_move_list_empty(self):
        """Test with no issues to move."""
        issues_dir = Path("/issues")
        issues = {}

        result = _build_move_list(issues_dir, issues)

        assert result == []

    def test_build_move_list_misplaced_only(self):
        """Test with only misplaced issues."""
        issues_dir = Path("/issues")
        issues = {
            "misplaced": [
                {
                    "issue_id": "issue-1",
                    "current_location": "/issues/v1.0/issue-1.md",
                    "expected_location": "/issues/v2.0/issue-1.md",
                },
                {
                    "issue_id": "issue-2",
                    "current_location": "/issues/backlog/issue-2.md",
                    "expected_location": "/issues/v1.0/issue-2.md",
                },
            ]
        }

        result = _build_move_list(issues_dir, issues)

        assert len(result) == 2
        assert result[0]["issue_id"] == "issue-1"
        assert result[0]["from"] == Path("/issues/v1.0/issue-1.md")
        assert result[0]["to"] == Path("/issues/v2.0/issue-1.md")
        assert result[1]["issue_id"] == "issue-2"

    def test_build_move_list_orphaned_only(self):
        """Test with only orphaned issues."""
        issues_dir = Path("/issues")
        issues = {
            "orphaned": [
                {
                    "issue_id": "issue-3",
                    "location": "/issues/orphan/issue-3.md",
                },
                {
                    "issue_id": "issue-4",
                    "location": "/issues/unknown/issue-4.md",
                },
            ]
        }

        result = _build_move_list(issues_dir, issues)

        assert len(result) == 2
        assert result[0]["issue_id"] == "issue-3"
        assert result[0]["to"] == Path("/issues/backlog/issue-3.md")
        assert result[1]["issue_id"] == "issue-4"
        assert result[1]["to"] == Path("/issues/backlog/issue-4.md")

    def test_build_move_list_mixed(self):
        """Test with both misplaced and orphaned issues."""
        issues_dir = Path("/issues")
        issues = {
            "misplaced": [
                {
                    "issue_id": "issue-1",
                    "current_location": "/issues/v1.0/issue-1.md",
                    "expected_location": "/issues/v2.0/issue-1.md",
                }
            ],
            "orphaned": [
                {
                    "issue_id": "issue-2",
                    "location": "/issues/orphan/issue-2.md",
                }
            ],
        }

        result = _build_move_list(issues_dir, issues)

        assert len(result) == 2
        assert result[0]["issue_id"] == "issue-1"
        assert result[1]["issue_id"] == "issue-2"

    def test_build_move_list_preserves_issue_ids(self):
        """Test that issue IDs are correctly preserved."""
        issues_dir = Path("/issues")
        issues = {
            "misplaced": [
                {
                    "issue_id": "complex-id-123",
                    "current_location": "/issues/old/complex-id-123.md",
                    "expected_location": "/issues/new/complex-id-123.md",
                }
            ]
        }

        result = _build_move_list(issues_dir, issues)

        assert result[0]["issue_id"] == "complex-id-123"


class TestConfirmFolderMoves:
    """Test _confirm_folder_moves function."""

    def test_confirm_folder_moves_with_force(self):
        """Test that force flag skips confirmation."""
        result = _confirm_folder_moves(force=True)
        assert result is True

    @patch("roadmap.infrastructure.maintenance.cleanup.click.confirm")
    def test_confirm_folder_moves_user_accepts(self, mock_confirm):
        """Test when user confirms the moves."""
        mock_confirm.return_value = True

        result = _confirm_folder_moves(force=False)

        assert result is True
        mock_confirm.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.click.confirm")
    def test_confirm_folder_moves_user_rejects(self, mock_confirm):
        """Test when user rejects the moves."""
        mock_confirm.return_value = False

        result = _confirm_folder_moves(force=False)

        assert result is False
        mock_confirm.assert_called_once()


class TestPerformFolderMoves:
    """Test _perform_folder_moves function."""

    def test_perform_folder_moves_empty_list(self):
        """Test with no moves to perform."""
        moves = []

        moved_count, failed_count = _perform_folder_moves(moves)

        assert moved_count == 0
        assert failed_count == 0

    def test_perform_folder_moves_successful(self, tmp_path):
        """Test successful file moves."""
        # Create source files
        from_file = tmp_path / "from" / "test.md"
        from_file.parent.mkdir()
        from_file.write_text("test")

        to_file = tmp_path / "to" / "test.md"

        moves = [{"from": from_file, "to": to_file, "issue_id": "issue-1"}]

        moved_count, failed_count = _perform_folder_moves(moves)

        assert moved_count == 1
        assert failed_count == 0
        assert to_file.exists()
        assert not from_file.exists()

    def test_perform_folder_moves_multiple(self, tmp_path):
        """Test multiple successful file moves."""
        moves = []
        for i in range(3):
            from_file = tmp_path / "from" / f"file{i}.md"
            from_file.parent.mkdir(exist_ok=True)
            from_file.write_text(f"content{i}")

            to_file = tmp_path / "to" / f"file{i}.md"
            moves.append({"from": from_file, "to": to_file, "issue_id": f"issue-{i}"})

        moved_count, failed_count = _perform_folder_moves(moves)

        assert moved_count == 3
        assert failed_count == 0

    def test_perform_folder_moves_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created."""
        from_file = tmp_path / "source.md"
        from_file.write_text("test")

        to_file = tmp_path / "deep" / "nested" / "path" / "dest.md"

        moves = [{"from": from_file, "to": to_file, "issue_id": "issue-1"}]

        moved_count, failed_count = _perform_folder_moves(moves)

        assert moved_count == 1
        assert to_file.exists()
        assert to_file.parent.exists()

    def test_perform_folder_moves_handles_failures(self, tmp_path):
        """Test handling of move failures."""
        # Create a valid file
        valid_from = tmp_path / "valid.md"
        valid_from.write_text("test")
        valid_to = tmp_path / "valid_moved.md"

        # Create an invalid move (source doesn't exist)
        invalid_from = tmp_path / "nonexistent.md"
        invalid_to = tmp_path / "dest.md"

        moves = [
            {"from": valid_from, "to": valid_to, "issue_id": "issue-1"},
            {"from": invalid_from, "to": invalid_to, "issue_id": "issue-2"},
        ]

        moved_count, failed_count = _perform_folder_moves(moves)

        assert moved_count == 1
        assert failed_count == 1
        assert valid_to.exists()

    def test_perform_folder_moves_reports_correct_counts(self, tmp_path):
        """Test that counts are accurate."""
        # Create 4 files, 2 will succeed, 2 will fail
        moves = []

        for i in range(2):
            from_file = tmp_path / f"valid{i}.md"
            from_file.write_text("test")
            to_file = tmp_path / f"moved{i}.md"
            moves.append({"from": from_file, "to": to_file, "issue_id": f"issue-{i}"})

        for i in range(2):
            from_file = tmp_path / f"invalid{i}.md"  # Doesn't exist
            to_file = tmp_path / f"failed{i}.md"
            moves.append({"from": from_file, "to": to_file, "issue_id": f"issue-{i+2}"})

        moved_count, failed_count = _perform_folder_moves(moves)

        assert moved_count == 2
        assert failed_count == 2
        assert moved_count + failed_count == 4


class TestHandleCheckFolders:
    """Test _handle_check_folders function."""

    @patch("roadmap.infrastructure.maintenance.cleanup.FolderStructureValidator")
    def test_handle_check_folders_no_dir(self, mock_validator, tmp_path):
        """Test when issues directory doesn't exist."""
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "nonexistent"

        _handle_check_folders(issues_dir, tmp_path, MagicMock(), mock_presenter)

        mock_presenter.present_no_issues_dir.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.FolderStructureValidator")
    def test_handle_check_folders_no_issues(self, mock_validator, tmp_path):
        """Test when no folder issues found."""
        mock_validator.scan_for_folder_structure_issues.return_value = None
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _handle_check_folders(issues_dir, tmp_path, MagicMock(), mock_presenter)

        mock_presenter.present_folder_check_clean.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.FolderStructureValidator")
    def test_handle_check_folders_with_issues(self, mock_validator, tmp_path):
        """Test when folder issues are found."""
        issues_data = {
            "misplaced": [{"issue_id": "issue-1", "current_location": "/old"}]
        }
        mock_validator.scan_for_folder_structure_issues.return_value = issues_data
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _handle_check_folders(issues_dir, tmp_path, MagicMock(), mock_presenter)

        mock_presenter.present_folder_issues.assert_called_once_with(issues_data)


class TestHandleCheckDuplicates:
    """Test _handle_check_duplicates function."""

    @patch("roadmap.infrastructure.maintenance.cleanup.DuplicateIssuesValidator")
    def test_handle_check_duplicates_no_dir(self, mock_validator, tmp_path):
        """Test when issues directory doesn't exist."""
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "nonexistent"

        _handle_check_duplicates(issues_dir, tmp_path, mock_presenter)

        mock_presenter.present_no_issues_dir.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.DuplicateIssuesValidator")
    def test_handle_check_duplicates_no_duplicates(self, mock_validator, tmp_path):
        """Test when no duplicates found."""
        mock_validator.scan_for_duplicate_issues.return_value = None
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _handle_check_duplicates(issues_dir, tmp_path, mock_presenter)

        mock_presenter.present_duplicates_check_clean.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.DuplicateIssuesValidator")
    def test_handle_check_duplicates_with_duplicates(self, mock_validator, tmp_path):
        """Test when duplicates are found."""
        duplicates_data = {"issue-1": [Path("/file1.md"), Path("/file2.md")]}
        mock_validator.scan_for_duplicate_issues.return_value = duplicates_data
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _handle_check_duplicates(issues_dir, tmp_path, mock_presenter)

        mock_presenter.present_duplicate_issues.assert_called_once()


class TestHandleCheckMalformed:
    """Test _handle_check_malformed function."""

    @patch("roadmap.infrastructure.maintenance.cleanup.DataIntegrityValidator")
    def test_handle_check_malformed_no_dir(self, mock_validator, tmp_path):
        """Test when issues directory doesn't exist."""
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "nonexistent"

        _handle_check_malformed(
            issues_dir, tmp_path, dry_run=False, force=False, presenter=mock_presenter
        )

        mock_presenter.present_no_issues_dir.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.DataIntegrityValidator")
    def test_handle_check_malformed_no_issues(self, mock_validator, tmp_path):
        """Test when no malformed files found."""
        mock_validator.scan_for_data_integrity_issues.return_value = {
            "malformed_files": []
        }
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _handle_check_malformed(
            issues_dir, tmp_path, dry_run=False, force=False, presenter=mock_presenter
        )

        mock_presenter.present_malformed_check_clean.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.FileRepairService")
    @patch("roadmap.infrastructure.maintenance.cleanup.DataIntegrityValidator")
    @patch("roadmap.infrastructure.maintenance.cleanup.click.confirm")
    def test_handle_check_malformed_with_repair(
        self, mock_confirm, mock_validator, mock_repair_service, tmp_path
    ):
        """Test malformed file repair with user confirmation."""
        mock_confirm.return_value = True
        malformed_data = {"malformed_files": ["file1.md", "file2.md"]}
        mock_validator.scan_for_data_integrity_issues.return_value = malformed_data
        mock_repair_instance = MagicMock()
        mock_repair_service.return_value = mock_repair_instance
        mock_repair_instance.repair_files.return_value = {"fixed": 2}

        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _handle_check_malformed(
            issues_dir, tmp_path, dry_run=False, force=False, presenter=mock_presenter
        )

        mock_repair_instance.repair_files.assert_called_once()
        mock_presenter.present_malformed_repair_result.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.DataIntegrityValidator")
    def test_handle_check_malformed_dry_run(self, mock_validator, tmp_path):
        """Test dry run mode doesn't repair files."""
        malformed_data = {"malformed_files": ["file1.md"]}
        mock_validator.scan_for_data_integrity_issues.return_value = malformed_data
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _handle_check_malformed(
            issues_dir, tmp_path, dry_run=True, force=False, presenter=mock_presenter
        )

        # Should not try to repair in dry-run mode
        mock_presenter.present_malformed_files.assert_called_once()


class TestRunBackupCleanup:
    """Test _run_backup_cleanup function."""

    @patch("roadmap.infrastructure.maintenance.cleanup.BackupCleanupService")
    def test_run_backup_cleanup_no_backups(self, mock_service, tmp_path):
        """Test when no backups directory exists."""
        mock_presenter = MagicMock()
        roadmap_dir = tmp_path

        _run_backup_cleanup(
            roadmap_dir,
            keep=10,
            days=None,
            dry_run=False,
            force=True,
            presenter=mock_presenter,
        )

        mock_presenter.present_no_backups.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.BackupCleanupService")
    def test_run_backup_cleanup_no_files_to_delete(self, mock_service, tmp_path):
        """Test when no files need cleanup."""
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()

        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance._select_backups_for_deletion.return_value = []

        mock_presenter = MagicMock()

        _run_backup_cleanup(
            tmp_path,
            keep=10,
            days=None,
            dry_run=False,
            force=True,
            presenter=mock_presenter,
        )

        mock_presenter.present_no_cleanup_needed.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.BackupCleanupService")
    def test_run_backup_cleanup_dry_run(self, mock_service, tmp_path):
        """Test dry-run mode shows what would be deleted."""
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()

        files_to_delete = [
            {"name": "backup1.md", "size": 1024},
            {"name": "backup2.md", "size": 2048},
        ]

        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance._select_backups_for_deletion.return_value = files_to_delete

        mock_presenter = MagicMock()

        _run_backup_cleanup(
            tmp_path,
            keep=10,
            days=None,
            dry_run=True,
            force=True,
            presenter=mock_presenter,
        )

        mock_presenter.present_backup_cleanup_dry_run.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.BackupCleanupService")
    @patch("roadmap.infrastructure.maintenance.cleanup.click.confirm")
    def test_run_backup_cleanup_with_confirmation(
        self, mock_confirm, mock_service, tmp_path
    ):
        """Test cleanup with user confirmation."""
        mock_confirm.return_value = True
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()

        files_to_delete = [
            {"name": "backup1.md", "size": 1024},
        ]

        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance._select_backups_for_deletion.return_value = files_to_delete
        mock_instance.cleanup_backups.return_value = {"deleted": 1}

        mock_presenter = MagicMock()

        _run_backup_cleanup(
            tmp_path,
            keep=10,
            days=None,
            dry_run=False,
            force=False,
            presenter=mock_presenter,
        )

        mock_confirm.assert_called_once()
        mock_instance.cleanup_backups.assert_called_once()

    @patch("roadmap.infrastructure.maintenance.cleanup.BackupCleanupService")
    @patch("roadmap.infrastructure.maintenance.cleanup.click.confirm")
    def test_run_backup_cleanup_user_cancels(
        self, mock_confirm, mock_service, tmp_path
    ):
        """Test when user cancels cleanup."""
        mock_confirm.return_value = False
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()

        files_to_delete = [
            {"name": "backup1.md", "size": 1024},
        ]

        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance._select_backups_for_deletion.return_value = files_to_delete

        mock_presenter = MagicMock()

        _run_backup_cleanup(
            tmp_path,
            keep=10,
            days=None,
            dry_run=False,
            force=False,
            presenter=mock_presenter,
        )

        mock_instance.cleanup_backups.assert_not_called()


class TestResolveFolderIssues:
    """Test _resolve_folder_issues function."""

    @patch("roadmap.infrastructure.maintenance.cleanup.FolderStructureValidator")
    def test_resolve_folder_issues_no_dir(self, mock_validator, tmp_path):
        """Test when issues directory doesn't exist."""
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "nonexistent"

        _resolve_folder_issues(
            issues_dir, tmp_path, MagicMock(), force=True, presenter=mock_presenter
        )

        # Should just return without error
        assert True

    @patch("roadmap.infrastructure.maintenance.cleanup.FolderStructureValidator")
    def test_resolve_folder_issues_no_issues(self, mock_validator, tmp_path):
        """Test when no folder issues found."""
        mock_validator.scan_for_folder_structure_issues.return_value = None
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _resolve_folder_issues(
            issues_dir, tmp_path, MagicMock(), force=True, presenter=mock_presenter
        )

        # Should return without performing moves
        mock_presenter.present_folder_moves.assert_not_called()

    @patch("roadmap.infrastructure.maintenance.cleanup.FolderStructureValidator")
    def test_resolve_folder_issues_with_moves(self, mock_validator, tmp_path):
        """Test folder issue resolution with moves."""
        # Create source files
        v1_dir = tmp_path / "v1.0"
        v1_dir.mkdir()
        source_file = v1_dir / "issue-1.md"
        source_file.write_text("test")

        issues_data = {
            "misplaced": [
                {
                    "issue_id": "issue-1",
                    "current_location": str(source_file),
                    "expected_location": str(tmp_path / "v2.0" / "issue-1.md"),
                }
            ]
        }
        mock_validator.scan_for_folder_structure_issues.return_value = issues_data

        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _resolve_folder_issues(
            issues_dir, tmp_path, MagicMock(), force=True, presenter=mock_presenter
        )

        mock_presenter.present_folder_moves.assert_called_once()


class TestResolveDuplicates:
    """Test _resolve_duplicates function."""

    @patch("roadmap.infrastructure.maintenance.cleanup.DuplicateIssuesValidator")
    def test_resolve_duplicates_no_dir(self, mock_validator, tmp_path):
        """Test when issues directory doesn't exist."""
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "nonexistent"

        _resolve_duplicates(issues_dir, tmp_path, force=True, presenter=mock_presenter)

        # Should return without error
        assert True

    @patch("roadmap.infrastructure.maintenance.cleanup.DuplicateIssuesValidator")
    def test_resolve_duplicates_no_duplicates(self, mock_validator, tmp_path):
        """Test when no duplicates found."""
        mock_validator.scan_for_duplicate_issues.return_value = None
        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _resolve_duplicates(issues_dir, tmp_path, force=True, presenter=mock_presenter)

        mock_presenter.present_duplicate_resolution.assert_not_called()

    @patch("roadmap.infrastructure.maintenance.cleanup.DuplicateIssuesValidator")
    def test_resolve_duplicates_with_duplicates(self, mock_validator, tmp_path):
        """Test duplicate resolution."""
        # Create duplicate files
        file1 = tmp_path / "issue-1_v1.md"
        file2 = tmp_path / "issue-1_v2.md"
        file1.write_text("old")
        file2.write_text("new")
        file2.touch()  # Make newer

        duplicates_data = {"issue-1": [file1, file2]}
        mock_validator.scan_for_duplicate_issues.return_value = duplicates_data

        mock_presenter = MagicMock()
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()

        _resolve_duplicates(issues_dir, tmp_path, force=True, presenter=mock_presenter)

        mock_presenter.present_duplicate_resolution.assert_called_once()
        mock_presenter.present_duplicate_resolution_result.assert_called_once()


class TestFixMalformedFiles:
    """Test _fix_malformed_files function."""

    @patch("roadmap.infrastructure.maintenance.cleanup.DataIntegrityValidator")
    def test_fix_malformed_files_no_issues(self, mock_validator, tmp_path):
        """Test when no malformed files found."""
        mock_validator.scan_for_data_integrity_issues.return_value = {
            "malformed_files": []
        }
        mock_presenter = MagicMock()

        _fix_malformed_files(tmp_path, mock_presenter)

        # Should return without attempting repair
        mock_presenter.present_malformed_repair_result.assert_not_called()

    @patch("roadmap.infrastructure.maintenance.cleanup.FileRepairService")
    @patch("roadmap.infrastructure.maintenance.cleanup.DataIntegrityValidator")
    def test_fix_malformed_files_with_repair(
        self, mock_validator, mock_repair_service, tmp_path
    ):
        """Test malformed file repair."""
        malformed_data = {"malformed_files": ["file1.md", "file2.md"]}
        mock_validator.scan_for_data_integrity_issues.return_value = malformed_data

        mock_repair_instance = MagicMock()
        mock_repair_service.return_value = mock_repair_instance
        mock_repair_instance.repair_files.return_value = {"fixed": 2}

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
        # Setup
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

        # Create source file
        old_dir = tmp_path / "old"
        old_dir.mkdir()
        (old_dir / "issue-1.md").write_text("test")

        issues_dir = tmp_path / "issues"
        issues_dir.mkdir()
        mock_presenter = MagicMock()

        # Execute
        _resolve_folder_issues(
            issues_dir, tmp_path, MagicMock(), force=True, presenter=mock_presenter
        )

        # Verify
        mock_presenter.present_folder_moves.assert_called_once()

    def test_build_and_perform_moves_integration(self, tmp_path):
        """Integration test for building and performing moves."""
        # Create source files
        source1 = tmp_path / "source1" / "file1.md"
        source2 = tmp_path / "source2" / "file2.md"
        source1.parent.mkdir()
        source2.parent.mkdir()
        source1.write_text("content1")
        source2.write_text("content2")

        # Build move list
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

        # Perform moves
        moved, failed = _perform_folder_moves(moves)

        assert moved == 2
        assert failed == 0
        assert (tmp_path / "dest1" / "file1.md").exists()
        assert (tmp_path / "dest2" / "file2.md").exists()
