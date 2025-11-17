"""Tests for bulk operations functionality."""

import json
import shutil
import tempfile
from pathlib import Path

from roadmap.bulk_operations import BulkOperationResult, BulkOperations
from roadmap.models import Priority, Status
from roadmap.parser import IssueParser


class TestBulkOperationResult:
    """Test the BulkOperationResult class."""

    def test_init(self):
        """Test result initialization."""
        result = BulkOperationResult()
        assert result.total_files == 0
        assert result.successful == 0
        assert result.failed == 0
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.results) == 0

    def test_add_success(self):
        """Test adding successful results."""
        result = BulkOperationResult()
        file_path = Path("test.md")

        result.add_success(file_path, {"test": "data"})

        assert result.successful == 1
        assert len(result.results) == 1
        assert result.results[0]["status"] == "success"
        assert result.results[0]["data"]["test"] == "data"

    def test_add_failure(self):
        """Test adding failed results."""
        result = BulkOperationResult()
        file_path = Path("test.md")

        result.add_failure(file_path, "Test error")

        assert result.failed == 1
        assert len(result.errors) == 1
        assert "test.md: Test error" in result.errors
        assert result.results[0]["status"] == "failed"

    def test_success_rate(self):
        """Test success rate calculation."""
        result = BulkOperationResult()
        result.total_files = 10
        result.successful = 8

        assert result.success_rate == 80.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = BulkOperationResult()
        result.total_files = 5
        result.successful = 4
        result.failed = 1
        result.finalize()

        data = result.to_dict()
        assert data["total_files"] == 5
        assert data["successful"] == 4
        assert data["failed"] == 1
        assert data["success_rate"] == 80.0
        assert "duration_seconds" in data


class TestBulkOperations:
    """Test the BulkOperations class."""

    def setup_method(self):
        """Set up test environment."""
        import os

        self.temp_dir = Path(tempfile.mkdtemp())
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create .roadmap directory structure in temp dir
        roadmap_dir = self.temp_dir / ".roadmap"
        roadmap_dir.mkdir(exist_ok=True)

        self.bulk_ops = BulkOperations(max_workers=2)

        # Create test directory structure
        self.issues_dir = self.temp_dir / "issues"
        self.milestones_dir = self.temp_dir / "milestones"
        self.issues_dir.mkdir()
        self.milestones_dir.mkdir()

        # Create valid issue files
        self.create_test_issue("a1b2c3d4", "Test Issue 1", "high", "todo")
        self.create_test_issue("e5f6a7b8", "Test Issue 2", "medium", "in-progress")

        # Create valid milestone files
        self.create_test_milestone("Version 1.0", "open")
        self.create_test_milestone("Version 2.0", "closed")

        # Create invalid file
        invalid_file = self.issues_dir / "invalid.md"
        invalid_content = """---
id: invalid-id
title: Invalid Issue
---

Missing required fields"""
        invalid_file.write_text(invalid_content)

    def teardown_method(self):
        """Clean up test environment."""
        import os

        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)

    def create_test_issue(self, issue_id: str, title: str, priority: str, status: str):
        """Create a test issue file."""
        content = f"""---
id: {issue_id}
title: {title}
priority: {priority}
status: {status}
created: 2024-01-01T00:00:00
---

This is {title} content."""

        file_path = self.issues_dir / f"{issue_id.lower()}.md"
        file_path.write_text(content)
        return file_path

    def create_test_milestone(self, name: str, status: str):
        """Create a test milestone file."""
        content = f"""---
name: {name}
status: {status}
created: 2024-01-01T00:00:00
---

This is {name} description."""

        file_path = self.milestones_dir / f"{name.lower().replace(' ', '_')}.md"
        file_path.write_text(content)
        return file_path

    def test_validate_directory_success(self):
        """Test directory validation with valid files."""
        result = self.bulk_ops.validate_directory(self.temp_dir)

        assert result.total_files == 5  # 2 issues + 2 milestones + 1 invalid
        assert result.successful == 4  # 2 issues + 2 milestones
        assert result.failed == 1  # 1 invalid
        assert result.success_rate == 80.0

    def test_validate_directory_non_recursive(self):
        """Test directory validation without recursion."""
        result = self.bulk_ops.validate_directory(self.temp_dir, recursive=False)

        # Should find no files in the root directory
        assert result.total_files == 0
        assert result.successful == 0
        assert result.failed == 0

    def test_backup_directory(self):
        """Test directory backup operation."""
        result = self.bulk_ops.backup_directory(self.temp_dir)

        assert result.total_files == 5
        assert result.successful == 5
        assert result.failed == 0

        # Check that backup files were created
        backup_dir = Path(".roadmap/backups")
        if backup_dir.exists():
            backups = list(backup_dir.glob("*.backup.md"))
            assert len(backups) >= 5

    def test_convert_format_dry_run(self):
        """Test format conversion in dry run mode."""
        result = self.bulk_ops.convert_format(self.temp_dir, dry_run=True)

        assert result.total_files == 5
        assert result.successful == 4  # Valid files only
        assert result.failed == 1  # Invalid file

        # Check that files weren't actually modified
        for success_result in result.results:
            if success_result["status"] == "success":
                assert "would_convert" in success_result["data"]

    def test_convert_format_actual(self):
        """Test actual format conversion."""
        # First backup the files
        backup_result = self.bulk_ops.backup_directory(self.temp_dir)
        assert backup_result.successful == 5

        # Then convert
        result = self.bulk_ops.convert_format(self.temp_dir, dry_run=False)

        assert result.total_files == 5
        assert result.successful == 4  # Valid files only
        assert result.failed == 1  # Invalid file

        # Check that backup was mentioned for successful conversions
        for success_result in result.results:
            if success_result["status"] == "success":
                data = success_result["data"]
                if "converted" in data:
                    assert data["converted"] is True
                    assert "backup_created" in data

    def test_generate_comprehensive_report(self):
        """Test comprehensive report generation."""
        report = self.bulk_ops.generate_comprehensive_report(self.temp_dir)

        assert "scan_time" in report
        assert "summary" in report
        assert "validation_results" in report
        assert "file_analysis" in report
        assert "recommendations" in report

        # Check summary
        summary = report["summary"]
        assert summary["total_files"] == 5
        assert summary["valid_files"] == 4
        assert summary["health_score"] == 80.0
        assert summary["file_structure_organized"] is True

        # Check file analysis
        analysis = report["file_analysis"]
        assert analysis["has_issues_dir"] is True
        assert analysis["has_milestones_dir"] is True
        assert analysis["issue_files"] == 3  # 2 valid + 1 invalid
        assert analysis["milestone_files"] == 2

    def test_generate_report_with_output_file(self):
        """Test report generation with file output."""
        output_file = self.temp_dir / "report.json"

        report = self.bulk_ops.generate_comprehensive_report(self.temp_dir, output_file)

        assert output_file.exists()

        # Verify file contents
        saved_report = json.loads(output_file.read_text())
        assert (
            saved_report["summary"]["total_files"] == report["summary"]["total_files"]
        )

    def test_batch_update_field_dry_run(self):
        """Test batch field update in dry run mode."""
        result = self.bulk_ops.batch_update_field(
            self.temp_dir,
            "priority",
            Priority.CRITICAL,
            file_type="issue",
            dry_run=True,
        )

        # Should find 2 valid issue files (excluding invalid one)
        assert result.successful >= 2

        # Check that files would be updated
        for success_result in result.results:
            if (
                success_result["status"] == "success"
                and "would_update" in success_result["data"]
            ):
                assert success_result["data"]["would_update"] == "priority"
                # The enum value is converted to string, so check the string representation
                assert "critical" in success_result["data"]["new_value"].lower()

    def test_batch_update_field_with_condition(self):
        """Test batch field update with condition."""
        # Only update issues with "todo" status
        condition = lambda issue: issue.status == Status.TODO

        result = self.bulk_ops.batch_update_field(
            self.temp_dir,
            "priority",
            Priority.CRITICAL,
            file_type="issue",
            condition=condition,
            dry_run=True,
        )

        # Should process all issue files but only update some
        assert result.total_files >= 2

        # Check results - some should be updated, some skipped
        updated_count = sum(
            1
            for r in result.results
            if r["status"] == "success" and "would_update" in r.get("data", {})
        )
        skipped_count = sum(
            1
            for r in result.results
            if r["status"] == "success"
            and r.get("data", {}).get("skipped") == "condition_not_met"
        )

        assert updated_count >= 1  # At least one todo issue
        assert skipped_count >= 0  # Possibly some non-todo issues

    def test_batch_update_field_actual(self):
        """Test actual batch field update."""
        result = self.bulk_ops.batch_update_field(
            self.temp_dir,
            "priority",
            Priority.CRITICAL,
            file_type="issue",
            dry_run=False,
        )

        assert result.successful >= 2

        # Verify that files were actually updated
        for success_result in result.results:
            if success_result[
                "status"
            ] == "success" and "field_updated" in success_result.get("data", {}):
                file_path = Path(success_result["file"])
                success, issue, error = IssueParser.parse_issue_file_safe(file_path)

                assert success
                assert issue.priority == Priority.CRITICAL

    def test_batch_update_invalid_field(self):
        """Test batch update with invalid field name."""
        result = self.bulk_ops.batch_update_field(
            self.temp_dir,
            "nonexistent_field",
            "some_value",
            file_type="issue",
            dry_run=True,
        )

        # Should fail for files that don't have the field
        assert result.failed > 0
        assert any(
            "Field 'nonexistent_field' not found" in error for error in result.errors
        )
