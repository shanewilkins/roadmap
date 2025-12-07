"""Shared utilities for validators."""

import re
from typing import TypedDict


class BackupScanResult(TypedDict):
    """Type definition for backup scan results."""

    files_to_delete: list[dict]
    total_size_bytes: int


def extract_issue_id(filename: str) -> str | None:
    """Extract issue ID from filename (first part before the dashes and title).

    Issue IDs are 8 hex characters.
    """
    match = re.match(r"^([a-f0-9]{8})", filename)
    return match.group(1) if match else None
