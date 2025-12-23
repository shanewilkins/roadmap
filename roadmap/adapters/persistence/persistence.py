"""Enhanced YAML validation utilities for roadmap persistence."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from roadmap.common.datetime_parser import parse_datetime
from roadmap.common.file_utils import ensure_directory_exists
from roadmap.common.validation import validate_frontmatter_structure


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
                    is_valid, _ = self.validate_yaml_syntax(fixed_frontmatter)
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

    def _is_already_quoted(self, value: str) -> bool:
        """Check if value is already properly quoted.

        Args:
            value: Value to check

        Returns:
            True if value is already quoted
        """
        return (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        )

    def _is_yaml_literal(self, value: str) -> bool:
        """Check if value is a YAML literal (bool, null, number, collection).

        Args:
            value: Value to check

        Returns:
            True if value is a YAML literal
        """
        return (
            value in ["true", "false", "null"]
            or value.isdigit()
            or value.startswith("[")
            or value.startswith("{")
        )

    def _needs_quoting(self, value: str) -> bool:
        """Check if value contains special YAML characters requiring quoting.

        Args:
            value: Value to check

        Returns:
            True if value needs quoting
        """
        special_chars = [
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
        return any(char in value for char in special_chars)

    def _quote_if_needed(self, value: str) -> str:
        """Quote value if it needs quoting and isn't already quoted.

        Args:
            value: Value to potentially quote

        Returns:
            Quoted value if needed, otherwise original value
        """
        if value and not (
            self._is_already_quoted(value) or self._is_yaml_literal(value)
        ):
            if self._needs_quoting(value):
                return f'"{value}"'
        return value

    def _fix_yaml_line(self, line: str) -> str:
        """Fix a single YAML line.

        Args:
            line: Single line of YAML to fix

        Returns:
            Fixed line
        """
        if not line.strip() or line.strip().startswith("#"):
            return line

        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            fixed_value = self._quote_if_needed(value)
            return f"{key}: {fixed_value}"

        return line

    def _fix_common_yaml_issues(self, yaml_content: str) -> str:
        """Fix common YAML formatting issues."""
        lines = yaml_content.split("\n")
        fixed_lines = [self._fix_yaml_line(line) for line in lines]
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
            loaded = yaml.safe_load(frontmatter_content)
            frontmatter: dict = loaded if isinstance(loaded, dict) else {}

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


# Global instances for easy access
recovery_manager = YAMLRecoveryManager()
enhanced_persistence = EnhancedYAMLPersistence(recovery_manager)
