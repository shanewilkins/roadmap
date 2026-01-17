"""Tests for data integrity validator."""

from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.core.services.validator_base import HealthStatus
from roadmap.core.services.validators.data_integrity_validator import (
    DataIntegrityValidator,
)


class TestDataIntegrityValidator:
    """Tests for DataIntegrityValidator."""

    def test_get_check_name(self):
        """Test validator identifier."""
        # DataIntegrityValidator doesn't have get_check_name, but test check methods exist
        assert hasattr(DataIntegrityValidator, "scan_for_data_integrity_issues")
        assert hasattr(DataIntegrityValidator, "check_data_integrity")

    def test_scan_nonexistent_directory(self, temp_dir_context):
        """Test scanning when issues directory doesn't exist."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir) / "nonexistent"

            result = DataIntegrityValidator.scan_for_data_integrity_issues(issues_dir)

            assert result == {"malformed_files": []}

    def test_scan_empty_directory(self, temp_dir_context):
        """Test scanning empty directory."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)

            result = DataIntegrityValidator.scan_for_data_integrity_issues(issues_dir)

            assert result == {"malformed_files": []}

    def test_scan_skips_backup_files(self, temp_dir_context):
        """Test that backup files are skipped."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)
            backup_file = issues_dir / "issue.md.backup"
            backup_file.write_text("backup content")

            result = DataIntegrityValidator.scan_for_data_integrity_issues(issues_dir)

            assert result == {"malformed_files": []}

    def test_scan_detects_malformed_files(self, temp_dir_context):
        """Test detection of malformed files."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create a file that will fail parsing
            malformed_file = issues_dir / "a1b2c3d4-Bad.md"
            malformed_file.write_text("invalid content that won't parse")

            with patch(
                "roadmap.adapters.persistence.parser.IssueParser.parse_issue_file",
                side_effect=Exception("Parse error"),
            ):
                result = DataIntegrityValidator.scan_for_data_integrity_issues(
                    issues_dir
                )

            assert len(result["malformed_files"]) == 1
            assert "a1b2c3d4-Bad.md" in result["malformed_files"][0]

    def test_scan_handles_parsing_errors_gracefully(self, temp_dir_context):
        """Test that parsing errors don't stop scanning."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create multiple files
            for i in range(3):
                file = issues_dir / f"a1b2c3d{i}-Issue.md"
                file.write_text(f"content {i}")

            def parse_side_effect(path):
                if "a1b2c3d1" in str(path):
                    raise Exception("Parse error")
                return None

            with patch(
                "roadmap.adapters.persistence.parser.IssueParser.parse_issue_file",
                side_effect=parse_side_effect,
            ):
                result = DataIntegrityValidator.scan_for_data_integrity_issues(
                    issues_dir
                )

            # Only one file should be malformed
            assert len(result["malformed_files"]) == 1

    def test_scan_nested_directories(self, temp_dir_context):
        """Test scanning nested directory structure."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create nested structure
            v1_dir = issues_dir / "v1.0"
            v1_dir.mkdir()
            (v1_dir / "a1b2c3d4-Issue.md").write_text("content")

            v2_dir = issues_dir / "v2.0"
            v2_dir.mkdir()
            (v2_dir / "e5f6g7h8-Issue.md").write_text("content")

            with patch(
                "roadmap.adapters.persistence.parser.IssueParser.parse_issue_file"
            ):
                result = DataIntegrityValidator.scan_for_data_integrity_issues(
                    issues_dir
                )

            # Should find files in nested directories
            assert result == {"malformed_files": []}

    def test_scan_returns_relative_paths(self, temp_dir_context):
        """Test that malformed file paths are relative."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)
            subdir = issues_dir / "v1.0"
            subdir.mkdir()
            malformed = subdir / "a1b2c3d4-Bad.md"
            malformed.write_text("content")

            with patch(
                "roadmap.adapters.persistence.parser.IssueParser.parse_issue_file",
                side_effect=Exception("Parse error"),
            ):
                result = DataIntegrityValidator.scan_for_data_integrity_issues(
                    issues_dir
                )

            # Path should be relative to issues_dir
            assert len(result["malformed_files"]) == 1
            assert "v1.0" in result["malformed_files"][0]
            assert str(issues_dir) not in result["malformed_files"][0]

    def test_scan_multiple_malformed_files(self, temp_dir_context):
        """Test detection of multiple malformed files."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)

            # Create multiple malformed files
            for i in range(3):
                file = issues_dir / f"file{i}.md"
                file.write_text("content")

            with patch(
                "roadmap.adapters.persistence.parser.IssueParser.parse_issue_file",
                side_effect=Exception("Parse error"),
            ):
                result = DataIntegrityValidator.scan_for_data_integrity_issues(
                    issues_dir
                )

            assert len(result["malformed_files"]) == 3

    def test_check_data_integrity_nonexistent_directory(self):
        """Test health check when directory doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            status, message = DataIntegrityValidator.check_data_integrity()

            assert status == HealthStatus.HEALTHY
            assert "not initialized" in message.lower()

    def test_check_data_integrity_no_issues(self, temp_dir_context):
        """Test health check when no issues found."""
        with temp_dir_context() as tmpdir:
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch(
                    "pathlib.Path.__truediv__",
                    return_value=Path(tmpdir),
                ),
                patch(
                    "roadmap.core.services.validators.data_integrity_validator.DataIntegrityValidator.scan_for_data_integrity_issues",
                    return_value={"malformed_files": []},
                ),
            ):
                status, message = DataIntegrityValidator.check_data_integrity()

                assert status == HealthStatus.HEALTHY
                assert "no data integrity issues" in message.lower()

    def test_check_data_integrity_with_issues(self):
        """Test health check when issues are found."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pathlib.Path.__truediv__",
                return_value=Path(".roadmap/issues"),
            ),
            patch(
                "roadmap.core.services.validators.data_integrity_validator.DataIntegrityValidator.scan_for_data_integrity_issues",
                return_value={"malformed_files": ["file1.md", "file2.md"]},
            ),
        ):
            status, message = DataIntegrityValidator.check_data_integrity()

            assert status == HealthStatus.DEGRADED
            assert "2" in message
            assert "malformed" in message.lower()

    def test_check_data_integrity_exception_handling(self):
        """Test health check handles exceptions."""
        with patch("pathlib.Path.exists", side_effect=Exception("FS error")):
            status, message = DataIntegrityValidator.check_data_integrity()

            assert status == HealthStatus.UNHEALTHY
            assert "error" in message.lower()

    def test_scan_result_structure(self, temp_dir_context):
        """Test that scan result has expected structure."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)

            result = DataIntegrityValidator.scan_for_data_integrity_issues(issues_dir)

            assert isinstance(result, dict)
            assert "malformed_files" in result
            assert isinstance(result["malformed_files"], list)

    @pytest.mark.parametrize(
        "filename",
        [
            "a1b2c3d4-Issue.md",
            "f0e1d2c3-Long Title With Spaces.md",
            "issue-with-dashes.md",
        ],
    )
    def test_scan_various_filenames(self, filename, temp_dir_context):
        """Test scanning files with various names."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)
            issue_file = issues_dir / filename
            issue_file.write_text("content")

            with patch(
                "roadmap.adapters.persistence.parser.IssueParser.parse_issue_file"
            ):
                result = DataIntegrityValidator.scan_for_data_integrity_issues(
                    issues_dir
                )

            assert result == {"malformed_files": []}

    def test_scan_empty_files(self, temp_dir_context):
        """Test scanning empty files."""
        with temp_dir_context() as tmpdir:
            issues_dir = Path(tmpdir)
            empty_file = issues_dir / "a1b2c3d4-Empty.md"
            empty_file.write_text("")

            with patch(
                "roadmap.adapters.persistence.parser.IssueParser.parse_issue_file",
                side_effect=Exception("Empty file error"),
            ):
                result = DataIntegrityValidator.scan_for_data_integrity_issues(
                    issues_dir
                )

            assert len(result["malformed_files"]) == 1

    def test_check_data_integrity_logs_success(self):
        """Test that successful health check logs debug message."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pathlib.Path.__truediv__",
                return_value=Path(".roadmap/issues"),
            ),
            patch(
                "roadmap.core.services.validators.data_integrity_validator.DataIntegrityValidator.scan_for_data_integrity_issues",
                return_value={"malformed_files": []},
            ),
            patch(
                "roadmap.core.services.validators.data_integrity_validator.logger"
            ) as mock_logger,
        ):
            DataIntegrityValidator.check_data_integrity()

            # Should have logged success
            assert mock_logger.debug.called

    def test_check_data_integrity_logs_warning(self):
        """Test that issues health check logs warning."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pathlib.Path.__truediv__",
                return_value=Path(".roadmap/issues"),
            ),
            patch(
                "roadmap.core.services.validators.data_integrity_validator.DataIntegrityValidator.scan_for_data_integrity_issues",
                return_value={"malformed_files": ["file1.md"]},
            ),
            patch(
                "roadmap.core.services.validators.data_integrity_validator.logger"
            ) as mock_logger,
        ):
            DataIntegrityValidator.check_data_integrity()

            # Should have logged warning
            assert mock_logger.warning.called
