"""Enhanced YAML validation and recovery utilities for roadmap persistence."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .datetime_parser import parse_datetime
from .file_utils import ensure_directory_exists
from .domain import Issue, Milestone
from .shared.validation import validate_frontmatter_structure


class YAMLValidationError(Exception):
    """Exception raised for YAML validation errors."""

    def __init__(
        self,
        message: str,
        file_path: Path | None = None,
        line_number: int | None = None,
    ):
        self.file_path = file_path
        self.line_number = line_number
        super().__init__(message)


class YAMLRecoveryManager:
    """Manages YAML file recovery and validation."""

    def __init__(self, backup_dir: Path | None = None):
        self.backup_dir = backup_dir or Path(".roadmap/backups")
        ensure_directory_exists(self.backup_dir)

    def create_backup(self, file_path: Path) -> Path:
        """Create a backup of a YAML file before modification."""
        if not file_path.exists():
            raise FileNotFoundError(f"Cannot backup non-existent file: {file_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}.backup{file_path.suffix}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(file_path, backup_path)
        return backup_path

    def list_backups(self, file_path: Path) -> list[Path]:
        """List all backups for a specific file."""
        pattern = f"{file_path.stem}_*.backup{file_path.suffix}"
        return sorted(self.backup_dir.glob(pattern), reverse=True)

    def restore_from_backup(
        self, file_path: Path, backup_path: Path | None = None
    ) -> bool:
        """Restore a file from its most recent backup."""
        if backup_path is None:
            backups = self.list_backups(file_path)
            if not backups:
                return False
            backup_path = backups[0]  # Most recent

        if not backup_path.exists():
            return False

        shutil.copy2(backup_path, file_path)
        return True

    def validate_yaml_syntax(
        self, content: str, file_path: Path | None = None
    ) -> tuple[bool, str | None]:
        """Validate YAML syntax and return error details if invalid."""
        try:
            yaml.safe_load(content)
            return True, None
        except yaml.YAMLError as e:
            error_msg = f"YAML syntax error: {e}"
            if hasattr(e, "problem_mark") and e.problem_mark:  # type: ignore
                line_num = e.problem_mark.line + 1  # type: ignore
                col_num = e.problem_mark.column + 1  # type: ignore
                error_msg += f" at line {line_num}, column {col_num}"
            return False, error_msg

    def validate_frontmatter_structure(
        self, frontmatter: dict[str, Any], expected_type: str
    ) -> tuple[bool, list[str]]:
        """Validate frontmatter structure for issues or milestones."""
        # Use unified validation framework
        is_valid, errors = validate_frontmatter_structure(frontmatter, expected_type)

        # Add datetime validation (specific to persistence layer)
        datetime_fields = ["created", "updated", "due_date"]
        for field in datetime_fields:
            if field in frontmatter and frontmatter[field] is not None:
                if isinstance(frontmatter[field], str):
                    try:
                        parse_datetime(frontmatter[field], "file")
                    except ValueError:
                        errors.append(
                            f"Invalid datetime format for {field}: {frontmatter[field]}"
                        )
                        is_valid = False

        return is_valid, errors

    def attempt_recovery(self, file_path: Path) -> tuple[bool, str | None]:
        """Attempt to recover a corrupted YAML file."""
        try:
            # Try to read the file
            content = file_path.read_text(encoding="utf-8")

            # Check if it's a frontmatter issue
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_content = parts[1]
                    markdown_content = parts[2].strip() if len(parts) > 2 else ""

                    # Try to fix common YAML issues
                    fixed_frontmatter = self._fix_common_yaml_issues(
                        frontmatter_content
                    )

                    # Validate the fixed YAML
                    is_valid, error = self.validate_yaml_syntax(fixed_frontmatter)
                    if is_valid:
                        # Create backup before fixing
                        self.create_backup(file_path)

                        # Write the fixed content
                        fixed_content = (
                            f"---\n{fixed_frontmatter}\n---\n\n{markdown_content}"
                        )
                        file_path.write_text(fixed_content, encoding="utf-8")
                        return True, "File recovered with YAML fixes applied"

            return False, "Could not automatically recover the file"

        except Exception as e:
            return False, f"Recovery failed: {e}"

    def _fix_common_yaml_issues(self, yaml_content: str) -> str:
        """Fix common YAML formatting issues."""
        lines = yaml_content.split("\n")
        fixed_lines = []

        for line in lines:
            # Skip empty lines
            if not line.strip():
                fixed_lines.append(line)
                continue

            # Fix unquoted strings that contain special characters
            if ":" in line and not line.strip().startswith("#"):
                key, _, value = line.partition(":")
                value = value.strip()

                # Quote strings that might need quoting
                if value and not (
                    value.startswith('"')
                    and value.endswith('"')
                    or value.startswith("'")
                    and value.endswith("'")
                    or value in ["true", "false", "null"]
                    or value.isdigit()
                    or value.startswith("[")
                    or value.startswith("{")
                ):
                    # Check if it needs quoting
                    if any(
                        char in value
                        for char in [
                            ":",
                            "#",
                            "@",
                            "`",
                            "|",
                            ">",
                            "*",
                            "&",
                            "!",
                            "%",
                            "{",
                            "}",
                            "[",
                            "]",
                        ]
                    ):
                        value = f'"{value}"'

                fixed_lines.append(f"{key}: {value}")
            else:
                fixed_lines.append(line)

        return "\n".join(fixed_lines)


class EnhancedYAMLPersistence:
    """Enhanced YAML persistence with validation and recovery."""

    def __init__(self, recovery_manager: YAMLRecoveryManager | None = None):
        self.recovery_manager = recovery_manager or YAMLRecoveryManager()

    def safe_load_with_validation(
        self, file_path: Path, expected_type: str
    ) -> tuple[bool, dict[str, Any] | str]:
        """Safely load and validate a YAML file with recovery options."""
        try:
            if not file_path.exists():
                return False, f"File does not exist: {file_path}"

            content = file_path.read_text(encoding="utf-8")

            # Parse frontmatter
            if not content.startswith("---"):
                return False, "File does not contain YAML frontmatter"

            parts = content.split("---", 2)
            if len(parts) < 3:
                return False, "Invalid frontmatter format"

            frontmatter_content = parts[1]
            markdown_content = parts[2].strip()

            # Validate YAML syntax
            is_valid, error = self.recovery_manager.validate_yaml_syntax(
                frontmatter_content, file_path
            )
            if not is_valid:
                # Attempt recovery
                recovered, recovery_msg = self.recovery_manager.attempt_recovery(
                    file_path
                )
                if recovered:
                    # Retry loading after recovery
                    return self.safe_load_with_validation(file_path, expected_type)
                else:
                    return (
                        False,
                        f"YAML validation failed: {error}. Recovery failed: {recovery_msg}",
                    )

            # Parse YAML
            frontmatter = yaml.safe_load(frontmatter_content) or {}

            # Validate structure
            is_valid, errors = self.recovery_manager.validate_frontmatter_structure(
                frontmatter, expected_type
            )
            if not is_valid:
                return False, f"Validation errors: {'; '.join(errors)}"

            # Add content to frontmatter
            frontmatter["content"] = markdown_content

            return True, frontmatter

        except Exception as e:
            return False, f"Failed to load file: {e}"

    def safe_save_with_backup(
        self, data: Issue | Milestone, file_path: Path
    ) -> tuple[bool, str]:
        """Safely save data with automatic backup."""
        try:
            # Create backup if file exists
            if file_path.exists():
                backup_path = self.recovery_manager.create_backup(file_path)
                backup_msg = f"Backup created: {backup_path.name}"
            else:
                backup_msg = "New file created"

            # Prepare data for serialization
            if isinstance(data, Issue):
                frontmatter = data.model_dump(exclude={"content"})
                content = data.content
            elif isinstance(data, Milestone):
                frontmatter = data.model_dump(exclude={"content"})
                content = data.content
            else:
                return False, "Unsupported data type"

            # Convert datetime and enum objects for YAML
            prepared_frontmatter = self._prepare_for_yaml(frontmatter)

            # Generate YAML content
            yaml_content = yaml.dump(
                prepared_frontmatter, default_flow_style=False, sort_keys=False
            )
            full_content = f"---\n{yaml_content}---\n\n{content}"

            # Validate generated YAML
            is_valid, error = self.recovery_manager.validate_yaml_syntax(yaml_content)
            if not is_valid:
                return False, f"Generated YAML is invalid: {error}"

            # Ensure directory exists
            ensure_directory_exists(file_path.parent)

            # Write file
            file_path.write_text(full_content, encoding="utf-8")

            return True, backup_msg

        except Exception as e:
            return False, f"Failed to save file: {e}"

    def _prepare_for_yaml(self, data: dict[str, Any]) -> dict[str, Any]:
        """Prepare data for YAML serialization."""
        prepared = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                prepared[key] = value.isoformat()
            elif hasattr(value, "value"):  # Handle enum values
                prepared[key] = value.value
            elif isinstance(value, list):
                prepared[key] = value
            elif value is None:
                prepared[key] = None
            else:
                prepared[key] = value
        return prepared

    def get_file_health_report(
        self, directory: Path, expected_type: str = "issue"
    ) -> dict[str, Any]:
        """Generate a health report for all YAML files in a directory."""
        report = {
            "total_files": 0,
            "valid_files": 0,
            "invalid_files": 0,
            "recoverable_files": 0,
            "errors": [],
            "warnings": [],
        }

        for file_path in directory.glob("*.md"):
            report["total_files"] += 1

            try:
                # Use provided expected_type, or determine from directory
                file_type = expected_type
                if expected_type == "auto":
                    file_type = "issue" if "issues" in str(file_path) else "milestone"

                is_valid, result = self.safe_load_with_validation(file_path, file_type)

                if is_valid:
                    report["valid_files"] += 1
                else:
                    report["invalid_files"] += 1
                    report["errors"].append(f"{file_path.name}: {result}")

                    # Check if recoverable
                    can_recover, _ = self.recovery_manager.attempt_recovery(file_path)
                    if can_recover:
                        report["recoverable_files"] += 1

            except Exception as e:
                report["invalid_files"] += 1
                report["errors"].append(f"{file_path.name}: {e}")

        return report


# Global instances for easy access
recovery_manager = YAMLRecoveryManager()
enhanced_persistence = EnhancedYAMLPersistence(recovery_manager)
