"""Bulk operations for YAML roadmap files."""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Issue, Milestone
from .parser import IssueParser, MilestoneParser
from .persistence import YAMLRecoveryManager, enhanced_persistence


class BulkOperationResult:
    """Results from a bulk operation."""

    def __init__(self):
        self.total_files = 0
        self.successful = 0
        self.failed = 0
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.results: list[dict[str, Any]] = []
        self.start_time = datetime.now()
        self.end_time = None

    def add_success(self, file_path: Path, result_data: dict[str, Any] | None = None):
        """Add a successful operation result."""
        self.successful += 1
        self.results.append(
            {
                "file": str(file_path),
                "status": "success",
                "data": result_data,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_failure(self, file_path: Path, error: str):
        """Add a failed operation result."""
        self.failed += 1
        self.errors.append(f"{file_path.name}: {error}")
        self.results.append(
            {
                "file": str(file_path),
                "status": "failed",
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_warning(self, file_path: Path, warning: str):
        """Add a warning for this operation."""
        self.warnings.append(f"{file_path.name}: {warning}")

    def finalize(self):
        """Mark the operation as complete."""
        self.end_time = datetime.now()

    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.successful / self.total_files) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "total_files": self.total_files,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": self.success_rate,
            "duration_seconds": self.duration,
            "errors": self.errors,
            "warnings": self.warnings,
            "results": self.results,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


class BulkOperations:
    """Manager for bulk operations on roadmap files."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.recovery_manager = YAMLRecoveryManager()

    def validate_directory(
        self, directory: Path, file_type: str = "auto", recursive: bool = True
    ) -> BulkOperationResult:
        """Validate all roadmap files in a directory."""
        result = BulkOperationResult()

        try:
            # Find all markdown files
            if recursive:
                files = list(directory.rglob("*.md"))
            else:
                files = list(directory.glob("*.md"))

            result.total_files = len(files)

            # Process files
            for file_path in files:
                try:
                    # Determine file type
                    expected_type = file_type
                    if file_type == "auto":
                        expected_type = (
                            "issue" if "issues" in str(file_path) else "milestone"
                        )
                        if "milestone" in str(file_path):
                            expected_type = "milestone"

                    # Validate the file
                    is_valid, validation_result = (
                        enhanced_persistence.safe_load_with_validation(
                            file_path, expected_type
                        )
                    )

                    if is_valid:
                        result.add_success(
                            file_path,
                            {
                                "type": expected_type,
                                "fields": (
                                    list(validation_result.keys())
                                    if isinstance(validation_result, dict)
                                    else None
                                ),
                            },
                        )
                    else:
                        result.add_failure(file_path, validation_result)

                except Exception as e:
                    result.add_failure(file_path, f"Exception during validation: {e}")

        except Exception as e:
            result.errors.append(f"Directory operation failed: {e}")

        result.finalize()
        return result

    def backup_directory(
        self, directory: Path, recursive: bool = True
    ) -> BulkOperationResult:
        """Create backups for all roadmap files in a directory."""
        result = BulkOperationResult()

        try:
            # Find all markdown files
            if recursive:
                files = list(directory.rglob("*.md"))
            else:
                files = list(directory.glob("*.md"))

            result.total_files = len(files)

            # Process files
            for file_path in files:
                try:
                    if file_path.exists() and file_path.stat().st_size > 0:
                        backup_path = self.recovery_manager.create_backup(file_path)
                        result.add_success(
                            file_path,
                            {
                                "backup_path": str(backup_path),
                                "backup_size": backup_path.stat().st_size,
                            },
                        )
                    else:
                        result.add_warning(file_path, "File is empty or does not exist")
                        result.add_success(file_path, {"skipped": "empty_file"})

                except Exception as e:
                    result.add_failure(file_path, f"Backup failed: {e}")

        except Exception as e:
            result.errors.append(f"Directory backup failed: {e}")

        result.finalize()
        return result

    def convert_format(
        self,
        directory: Path,
        target_format: str = "enhanced",
        recursive: bool = True,
        dry_run: bool = False,
    ) -> BulkOperationResult:
        """Convert roadmap files to enhanced format with better validation."""
        result = BulkOperationResult()

        try:
            # Find all markdown files, excluding backup files
            if recursive:
                all_files = list(directory.rglob("*.md"))
            else:
                all_files = list(directory.glob("*.md"))

            # Filter out backup files (*.backup.md) and files in backup directories
            files = [
                f
                for f in all_files
                if not f.name.endswith(".backup.md")
                and ".roadmap/backups" not in str(f)
                and "backup" not in f.name
            ]

            result.total_files = len(files)

            # Process files
            for file_path in files:
                try:
                    # Determine file type
                    expected_type = (
                        "issue" if "issues" in str(file_path) else "milestone"
                    )
                    if "milestone" in str(file_path):
                        expected_type = "milestone"

                    # Load and validate
                    is_valid, data = enhanced_persistence.safe_load_with_validation(
                        file_path, expected_type
                    )

                    if is_valid:
                        if not dry_run:
                            # Create backup first
                            backup_path = self.recovery_manager.create_backup(file_path)

                            # Convert to enhanced format by re-saving
                            if expected_type == "issue":
                                issue = Issue(
                                    **{k: v for k, v in data.items() if k != "content"}
                                )
                                issue.content = data.get("content", "")
                                success, message = (
                                    enhanced_persistence.safe_save_with_backup(
                                        issue, file_path
                                    )
                                )
                            else:
                                milestone = Milestone(
                                    **{k: v for k, v in data.items() if k != "content"}
                                )
                                milestone.content = data.get("content", "")
                                success, message = (
                                    enhanced_persistence.safe_save_with_backup(
                                        milestone, file_path
                                    )
                                )

                            if success:
                                result.add_success(
                                    file_path,
                                    {
                                        "converted": True,
                                        "backup_created": str(backup_path),
                                        "message": message,
                                    },
                                )
                            else:
                                result.add_failure(file_path, f"Save failed: {message}")
                        else:
                            result.add_success(
                                file_path,
                                {"would_convert": True, "type": expected_type},
                            )
                    else:
                        result.add_failure(file_path, f"Validation failed: {data}")

                except Exception as e:
                    result.add_failure(file_path, f"Conversion failed: {e}")

        except Exception as e:
            result.errors.append(f"Directory conversion failed: {e}")

        result.finalize()
        return result

    def generate_comprehensive_report(
        self, directory: Path, output_file: Path | None = None
    ) -> dict[str, Any]:
        """Generate a comprehensive health and analytics report."""
        report = {
            "scan_time": datetime.now().isoformat(),
            "directory": str(directory),
            "summary": {},
            "validation_results": {},
            "file_analysis": {},
            "recommendations": [],
        }

        try:
            # Run validation
            validation_result = self.validate_directory(directory)
            report["validation_results"] = validation_result.to_dict()

            # Analyze file structure
            issues_dir = directory / "issues"
            milestones_dir = directory / "milestones"

            analysis = {
                "has_issues_dir": issues_dir.exists(),
                "has_milestones_dir": milestones_dir.exists(),
                "total_md_files": len(list(directory.rglob("*.md"))),
                "issue_files": (
                    len(list(issues_dir.glob("*.md"))) if issues_dir.exists() else 0
                ),
                "milestone_files": (
                    len(list(milestones_dir.glob("*.md")))
                    if milestones_dir.exists()
                    else 0
                ),
            }

            report["file_analysis"] = analysis

            # Generate recommendations
            recommendations = []
            if validation_result.failed > 0:
                recommendations.append("Fix validation errors in failed files")
            if analysis["total_md_files"] > 0 and not analysis["has_issues_dir"]:
                recommendations.append(
                    "Consider organizing files into 'issues' and 'milestones' directories"
                )
            if validation_result.success_rate < 100:
                recommendations.append("Run bulk validation and fix any schema issues")

            report["recommendations"] = recommendations

            # Summary
            report["summary"] = {
                "health_score": validation_result.success_rate,
                "total_files": analysis["total_md_files"],
                "valid_files": validation_result.successful,
                "file_structure_organized": analysis["has_issues_dir"]
                and analysis["has_milestones_dir"],
            }

            # Save report if requested
            if output_file:
                output_file.write_text(json.dumps(report, indent=2))

        except Exception as e:
            report["error"] = str(e)

        return report

    def batch_update_field(
        self,
        directory: Path,
        field_name: str,
        field_value: Any,
        file_type: str = "issue",
        condition: Callable | None = None,
        dry_run: bool = False,
    ) -> BulkOperationResult:
        """Update a specific field across multiple files."""
        result = BulkOperationResult()

        try:
            # Find all markdown files
            files = list(directory.rglob("*.md"))

            # Filter by type if specified
            if file_type == "issue":
                files = [
                    f for f in files if "issues" in str(f) or "milestone" not in str(f)
                ]
            elif file_type == "milestone":
                files = [f for f in files if "milestone" in str(f)]

            result.total_files = len(files)

            # Process files
            for file_path in files:
                try:
                    # Parse the file
                    if file_type == "issue":
                        success, item, error = IssueParser.parse_issue_file_safe(
                            file_path
                        )
                    else:
                        success, item, error = (
                            MilestoneParser.parse_milestone_file_safe(file_path)
                        )

                    if not success:
                        result.add_failure(file_path, f"Parse failed: {error}")
                        continue

                    # Check condition if provided
                    if condition and not condition(item):
                        result.add_success(file_path, {"skipped": "condition_not_met"})
                        continue

                    # Update the field
                    if hasattr(item, field_name):
                        old_value = getattr(item, field_name)

                        if not dry_run:
                            setattr(item, field_name, field_value)

                            # Save the updated item
                            if file_type == "issue":
                                save_success, message = (
                                    IssueParser.save_issue_file_safe(item, file_path)
                                )
                            else:
                                save_success, message = (
                                    MilestoneParser.save_milestone_file_safe(
                                        item, file_path
                                    )
                                )

                            if save_success:
                                result.add_success(
                                    file_path,
                                    {
                                        "field_updated": field_name,
                                        "old_value": str(old_value),
                                        "new_value": str(field_value),
                                        "message": message,
                                    },
                                )
                            else:
                                result.add_failure(file_path, f"Save failed: {message}")
                        else:
                            result.add_success(
                                file_path,
                                {
                                    "would_update": field_name,
                                    "old_value": str(old_value),
                                    "new_value": str(field_value),
                                },
                            )
                    else:
                        result.add_failure(
                            file_path, f"Field '{field_name}' not found on {file_type}"
                        )

                except Exception as e:
                    result.add_failure(file_path, f"Update failed: {e}")

        except Exception as e:
            result.errors.append(f"Batch update failed: {e}")

        result.finalize()
        return result


# Global instance for easy access
bulk_operations = BulkOperations()
