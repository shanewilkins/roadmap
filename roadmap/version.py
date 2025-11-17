"""Version management utilities for the roadmap CLI tool.

This module provides utilities for semantic version validation, version consistency
checking, and automated version bumping with changelog integration.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import toml

from .models import Issue, Milestone


class SemanticVersion:
    """Represents a semantic version with major.minor.patch format."""

    def __init__(self, version_string: str):
        """Initialize from version string like '1.2.3' or 'v1.2.3'."""
        self.raw = version_string.strip()
        # Remove 'v' prefix if present
        clean_version = self.raw.lstrip("v")

        if not self.is_valid_semantic_version(clean_version):
            raise ValueError(f"Invalid semantic version format: {version_string}")

        self.major, self.minor, self.patch = self._parse_version(clean_version)

    @staticmethod
    def is_valid_semantic_version(version: str) -> bool:
        """Check if version string follows semantic versioning format."""
        pattern = r"^(\d+)\.(\d+)\.(\d+)$"
        return bool(re.match(pattern, version))

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        """Parse version string into major, minor, patch integers."""
        parts = version.split(".")
        return int(parts[0]), int(parts[1]), int(parts[2])

    def bump_major(self) -> "SemanticVersion":
        """Return new version with major incremented, minor and patch reset to 0."""
        return SemanticVersion(f"{self.major + 1}.0.0")

    def bump_minor(self) -> "SemanticVersion":
        """Return new version with minor incremented, patch reset to 0."""
        return SemanticVersion(f"{self.major}.{self.minor + 1}.0")

    def bump_patch(self) -> "SemanticVersion":
        """Return new version with patch incremented."""
        return SemanticVersion(f"{self.major}.{self.minor}.{self.patch + 1}")

    def __str__(self) -> str:
        """Return clean version string without 'v' prefix."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"SemanticVersion('{self}')"

    def __eq__(self, other) -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return (self.major, self.minor, self.patch) == (
            other.major,
            other.minor,
            other.patch,
        )

    def __lt__(self, other) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __le__(self, other) -> bool:
        return self < other or self == other

    def __gt__(self, other) -> bool:
        return not self <= other

    def __ge__(self, other) -> bool:
        return not self < other


class VersionManager:
    """Manages version consistency and automated version bumping."""

    def __init__(self, project_root: Path):
        """Initialize with project root directory."""
        self.project_root = Path(project_root)
        self.pyproject_path = self.project_root / "pyproject.toml"
        self.init_path = self.project_root / "roadmap" / "__init__.py"
        self.changelog_path = self.project_root / "CHANGELOG.md"

    def get_current_version(self) -> SemanticVersion | None:
        """Get current version from pyproject.toml."""
        try:
            with open(self.pyproject_path) as f:
                data = toml.load(f)
            version_str = data.get("tool", {}).get("poetry", {}).get("version")
            if version_str:
                return SemanticVersion(version_str)
        except Exception:
            pass
        return None

    def get_init_version(self) -> SemanticVersion | None:
        """Get version from __init__.py file."""
        try:
            with open(self.init_path) as f:
                content = f.read()
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return SemanticVersion(match.group(1))
        except Exception:
            pass
        return None

    def check_version_consistency(self) -> dict[str, Any]:
        """Check version consistency across all files."""
        result = {
            "consistent": True,
            "pyproject_version": None,
            "init_version": None,
            "issues": [],
        }

        # Get versions from different sources
        pyproject_version = self.get_current_version()
        init_version = self.get_init_version()

        result["pyproject_version"] = (
            str(pyproject_version) if pyproject_version else None
        )
        result["init_version"] = str(init_version) if init_version else None

        # Check consistency
        if not pyproject_version:
            result["issues"].append("No version found in pyproject.toml")
            result["consistent"] = False

        if not init_version:
            result["issues"].append("No version found in __init__.py")
            result["consistent"] = False

        if pyproject_version and init_version and pyproject_version != init_version:
            result["issues"].append(
                f"Version mismatch: pyproject.toml has {pyproject_version}, "
                f"__init__.py has {init_version}"
            )
            result["consistent"] = False

        return result

    def update_version(self, new_version: SemanticVersion) -> bool:
        """Update version in all relevant files."""
        success = True

        # Update pyproject.toml
        try:
            with open(self.pyproject_path) as f:
                data = toml.load(f)

            data["tool"]["poetry"]["version"] = str(new_version)

            with open(self.pyproject_path, "w") as f:
                toml.dump(data, f)
        except Exception as e:
            print(f"Failed to update pyproject.toml: {e}")
            success = False

        # Update __init__.py
        try:
            with open(self.init_path) as f:
                content = f.read()

            updated_content = re.sub(
                r'__version__\s*=\s*["\'][^"\']+["\']',
                f'__version__ = "{new_version}"',
                content,
            )

            with open(self.init_path, "w") as f:
                f.write(updated_content)
        except Exception as e:
            print(f"Failed to update __init__.py: {e}")
            success = False

        return success

    def get_git_status(self) -> dict[str, Any]:
        """Get git repository status."""
        try:
            # Check if we're in a git repo
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                check=True,
            )

            # Get status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            uncommitted_files = (
                result.stdout.strip().split("\n") if result.stdout.strip() else []
            )

            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            current_branch = branch_result.stdout.strip()

            return {
                "is_git_repo": True,
                "current_branch": current_branch,
                "uncommitted_files": uncommitted_files,
                "is_clean": len(uncommitted_files) == 0,
            }
        except subprocess.CalledProcessError:
            return {
                "is_git_repo": False,
                "current_branch": None,
                "uncommitted_files": [],
                "is_clean": True,
            }

    def generate_changelog_entry(
        self, version: SemanticVersion, issues: list[Issue], milestones: list[Milestone]
    ) -> str:
        """Generate changelog entry for a version."""
        date_str = datetime.now().strftime("%Y-%m-%d")

        entry = f"\n## [{version}] - {date_str}\n\n"

        # Group issues by type
        features = []
        bugfixes = []
        other = []

        for issue in issues:
            if issue.issue_type.value == "feature":
                features.append(issue)
            elif issue.issue_type.value == "bug":
                bugfixes.append(issue)
            else:
                other.append(issue)

        # Add sections
        if features:
            entry += "### Added\n"
            for issue in features:
                entry += f"- {issue.title} (#{issue.id[:8]})\n"
            entry += "\n"

        if bugfixes:
            entry += "### Fixed\n"
            for issue in bugfixes:
                entry += f"- {issue.title} (#{issue.id[:8]})\n"
            entry += "\n"

        if other:
            entry += "### Changed\n"
            for issue in other:
                entry += f"- {issue.title} (#{issue.id[:8]})\n"
            entry += "\n"

        # Add completed milestones
        completed_milestones = [m for m in milestones if m.status.value == "completed"]
        if completed_milestones:
            entry += "### Milestones\n"
            for milestone in completed_milestones:
                entry += f"- {milestone.name}: {milestone.description}\n"
            entry += "\n"

        return entry

    def update_changelog(self, version: SemanticVersion, entry: str) -> bool:
        """Update changelog with new version entry."""
        try:
            if not self.changelog_path.exists():
                # Create new changelog
                content = f"# Changelog\n\nAll notable changes to this project will be documented in this file.\n{entry}"
            else:
                with open(self.changelog_path) as f:
                    content = f.read()

                # Insert new entry after the main heading
                lines = content.split("\n")
                if len(lines) > 0 and lines[0].startswith("# "):
                    # Find the first existing version entry or insert after description
                    insert_index = 1
                    for i, line in enumerate(lines[1:], 1):
                        if line.startswith("## ["):
                            insert_index = i
                            break
                        elif line.strip() == "":
                            continue
                        elif not line.startswith("#"):
                            insert_index = i + 1

                    lines.insert(insert_index, entry.rstrip())
                    content = "\n".join(lines)
                else:
                    content = f"# Changelog\n\nAll notable changes to this project will be documented in this file.\n{entry}{content}"

            with open(self.changelog_path, "w") as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"Failed to update changelog: {e}")
            return False
