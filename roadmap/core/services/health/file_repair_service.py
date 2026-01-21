"""Service for repairing malformed YAML in issue files."""

from pathlib import Path
from typing import Any

import yaml

from roadmap.common.logging import get_logger
from roadmap.common.logging.error_logging import (
    log_error_with_context,
)
from roadmap.common.observability.instrumentation import traced

logger = get_logger(__name__)


class FileRepairResult:
    """Result of file repair operation."""

    def __init__(self):
        """Initialize FileRepairResult."""
        self.fixed_files: list[str] = []
        self.errors: list[str] = []

    def add_fixed(self, file_rel: str) -> None:
        """Record a fixed file."""
        self.fixed_files.append(file_rel)

    def add_error(self, file_rel: str) -> None:
        """Record a file that couldn't be fixed."""
        self.errors.append(file_rel)


class FileRepairService:
    """Repairs common malformed YAML issues in issue files."""

    @traced("repair_files")
    def repair_files(
        self, issues_dir: Path, malformed_files: list[str], dry_run: bool = False
    ) -> FileRepairResult:
        """Fix common malformed YAML issues in issue files.

        Args:
            issues_dir: Directory containing issue files
            malformed_files: List of relative paths to malformed files
            dry_run: If True, don't write changes to disk

        Returns:
            FileRepairResult with fixed_files and errors lists
        """
        result = FileRepairResult()

        for file_rel in malformed_files:
            file_path = issues_dir / file_rel

            try:
                content = file_path.read_text(encoding="utf-8")

                # Extract frontmatter
                if not content.startswith("---"):
                    result.add_error(file_rel)
                    continue

                parts = content.split("---", 2)
                if len(parts) < 3:
                    result.add_error(file_rel)
                    continue

                frontmatter_str, markdown_content = parts[1], parts[2]

                # Parse and fix common issues
                try:
                    frontmatter = yaml.safe_load(frontmatter_str)
                    if not isinstance(frontmatter, dict):
                        result.add_error(file_rel)
                        continue
                except yaml.YAMLError:
                    result.add_error(file_rel)
                    continue

                # Fix git_commits and git_branches
                self._normalize_git_data(frontmatter)

                # Reconstruct the file
                fixed_frontmatter = yaml.dump(
                    frontmatter, default_flow_style=False, sort_keys=False
                )
                fixed_content = f"---\n{fixed_frontmatter}---\n{markdown_content}"

                if not dry_run:
                    try:
                        file_path.write_text(fixed_content, encoding="utf-8")
                    except Exception as write_error:
                        log_error_with_context(
                            write_error,
                            operation="write_repaired_file",
                            entity_type="File",
                            entity_id=file_rel,
                        )
                        result.add_error(file_rel)
                        logger.warning(
                            "Failed to write repaired file",
                            file=file_rel,
                            error=str(write_error),
                        )
                        continue

                result.add_fixed(file_rel)
                logger.info("Fixed malformed file", file=file_rel)

            except Exception as e:
                log_error_with_context(
                    e,
                    operation="repair_file",
                    entity_type="File",
                    entity_id=file_rel,
                )
                result.add_error(file_rel)
                logger.warning("Failed to fix file", file=file_rel, error=str(e))

        return result

    @staticmethod
    @staticmethod
    def _fix_git_commits(frontmatter: dict[str, Any]) -> None:
        """Fix git_commits list format.

        Converts list of strings to list of dicts with 'hash' key.

        Args:
            frontmatter: Frontmatter dict to fix
        """
        if "git_commits" not in frontmatter or not isinstance(
            frontmatter["git_commits"], list
        ):
            return

        fixed_commits = []
        for commit in frontmatter["git_commits"]:
            if isinstance(commit, str):
                # Convert string commit hash to dict
                fixed_commits.append({"hash": commit})
            else:
                fixed_commits.append(commit)
        frontmatter["git_commits"] = fixed_commits

    @staticmethod
    def _fix_git_branches(frontmatter: dict[str, Any]) -> None:
        """Fix git_branches list format.

        Converts list of dicts to list of strings.

        Args:
            frontmatter: Frontmatter dict to fix
        """
        if "git_branches" not in frontmatter or not isinstance(
            frontmatter["git_branches"], list
        ):
            return

        fixed_branches = []
        for branch in frontmatter["git_branches"]:
            if isinstance(branch, dict):
                # Convert dict to string - prefer 'name' field
                if "name" in branch:
                    fixed_branches.append(branch["name"])
                elif isinstance(branch, str):
                    fixed_branches.append(branch)
                else:
                    fixed_branches.append(str(branch))
            elif isinstance(branch, str):
                fixed_branches.append(branch)
            else:
                # Convert any other type to string
                fixed_branches.append(str(branch))
        frontmatter["git_branches"] = fixed_branches

    @staticmethod
    def _normalize_git_data(frontmatter: dict[str, Any]) -> None:
        """Normalize git_commits and git_branches in frontmatter.

        Fixes:
        - git_commits: list of strings → list of dicts with 'hash' key
        - git_branches: list of dicts → list of strings
        """
        FileRepairService._fix_git_commits(frontmatter)
        FileRepairService._fix_git_branches(frontmatter)
