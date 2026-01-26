"""Conflict detection and resolution for file synchronization.

This module handles detection and management of conflicts that arise during
file synchronization operations.
"""

from pathlib import Path
from typing import Any

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class ConflictResolver:
    """Handles detection and resolution of synchronization conflicts."""

    def __init__(self, data_dir: Path):
        """Initialize the conflict resolver.

        Args:
            data_dir: Root directory for data files
        """
        self.data_dir = data_dir

    def detect_conflicts(self) -> list[str]:
        """Detect files with git merge conflict markers.

        Returns:
            List of file paths containing conflict markers
        """
        conflict_files = []

        try:
            for file_path in self.data_dir.rglob("*.md"):
                if self._has_conflict_markers(file_path):
                    conflict_files.append(str(file_path))
        except Exception as e:
            logger.warning(
                "error_detecting_conflicts",
                error=str(e),
                severity="operational",
            )

        return conflict_files

    def _has_conflict_markers(self, file_path: Path) -> bool:
        """Check if a file contains git conflict markers.

        Args:
            file_path: Path to file to check

        Returns:
            True if file contains conflict markers
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                # Check for standard git conflict markers
                return (
                    "<<<<<<< HEAD" in content
                    or "<<<<<<<" in content
                    or "=======" in content
                    or ">>>>>>>" in content
                )
        except Exception as e:
            logger.debug("conflict_marker_check_failed", error=str(e))
            return False

    def resolve_conflict(self, file_path: Path, resolution: str) -> bool:
        """Resolve a file conflict by removing markers.

        Args:
            file_path: Path to file with conflict
            resolution: Which version to keep - "ours" or "theirs"

        Returns:
            True if resolution was successful
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Remove conflict markers and keep appropriate version
            resolved = self._remove_conflict_markers(content, resolution)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(resolved)

            logger.info(f"Resolved conflict in {file_path.name} (kept {resolution})")
            return True
        except Exception as e:
            logger.error(f"Error resolving conflict in {file_path}: {e}")
            return False

    def _remove_conflict_markers(self, content: str, resolution: str) -> str:
        """Remove conflict markers from content, keeping specified version.

        Args:
            content: File content with conflict markers
            resolution: Which version to keep - "ours" or "theirs"

        Returns:
            Content with conflict markers removed
        """
        lines = content.split("\n")
        resolved_lines = []
        in_conflict = False
        ours_section = []
        theirs_section = []
        current_section = None

        for line in lines:
            if line.startswith("<<<<<<< HEAD"):
                in_conflict = True
                current_section = "ours"
                ours_section = []
                theirs_section = []
            elif line.startswith("======="):
                if in_conflict:
                    current_section = "theirs"
            elif line.startswith(">>>>>>>"):
                in_conflict = False
                if resolution == "ours":
                    resolved_lines.extend(ours_section)
                else:
                    resolved_lines.extend(theirs_section)
                ours_section = []
                theirs_section = []
            elif in_conflict:
                if current_section == "ours":
                    ours_section.append(line)
                else:
                    theirs_section.append(line)
            else:
                resolved_lines.append(line)

        return "\n".join(resolved_lines)

    def auto_resolve_conflicts(
        self, sync_state_tracker, resolution: str = "ours"
    ) -> bool:
        """Automatically resolve all detected conflicts.

        Args:
            sync_state_tracker: SyncStateTracker instance for updating state
            resolution: Which version to keep for all conflicts

        Returns:
            True if all conflicts resolved successfully
        """
        conflict_files = self.detect_conflicts()

        if not conflict_files:
            return True

        all_resolved = True
        for file_path in conflict_files:
            if not self.resolve_conflict(Path(file_path), resolution):
                all_resolved = False

        if all_resolved:
            sync_state_tracker.clear_conflicts()
        else:
            sync_state_tracker.mark_conflicts_detected(conflict_files)

        return all_resolved

    def get_conflict_summary(self) -> dict[str, Any]:
        """Get summary of detected conflicts.

        Returns:
            Dictionary with conflict information
        """
        conflict_files = self.detect_conflicts()

        return {
            "has_conflicts": len(conflict_files) > 0,
            "conflict_count": len(conflict_files),
            "files": conflict_files,
        }
