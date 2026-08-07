"""Validation utilities for roadmap domain logic."""

from pathlib import Path
from typing import Any

from roadmap.core.services.validators import (
    DataIntegrityValidator,
    DuplicateIssuesValidator,
    FolderStructureValidator,
)

# Example utility: validate folder structure


def validate_folder_structure(issues_dir: Path, core: Any) -> dict:
    """Validate folder structure and return issues found."""
    return FolderStructureValidator.scan_for_folder_structure_issues(issues_dir, core)


def find_duplicate_issues(issues_dir: Path) -> dict:
    """Find duplicate issues by issue ID."""
    return DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)


def find_malformed_issue_files(issues_dir: Path) -> dict:
    """Find malformed issue files (unparseable YAML, etc)."""
    return DataIntegrityValidator.scan_for_data_integrity_issues(issues_dir)


# Add more validation utilities as needed
