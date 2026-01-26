"""Git conflict detection and handling service."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

from roadmap.common.logging import get_logger

if TYPE_CHECKING:
    from .state_manager import StateManager

logger = get_logger(__name__)


class ConflictService:
    """Service for detecting and managing git conflicts in .roadmap directory."""

    def __init__(self, state_manager: "StateManager"):
        """Initialize with reference to state manager.

        Args:
            state_manager: StateManager instance for accessing sync state
        """
        self.state_manager = state_manager

    def check_git_conflicts(self, roadmap_dir: Path | None = None) -> list[str]:
        """Check for git conflicts in .roadmap directory."""
        if roadmap_dir is None:
            roadmap_dir = Path.cwd() / ".roadmap"

        conflict_files = []

        try:
            if not roadmap_dir.exists():
                return conflict_files

            # Check for conflict markers in .roadmap files
            for pattern in ["**/*.md", "**/*.yaml", "**/*.yml"]:
                for file_path in roadmap_dir.glob(pattern):
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()

                        # Look for git conflict markers
                        conflict_markers = ["<<<<<<<", "=======", ">>>>>>>"]
                        if any(marker in content for marker in conflict_markers):
                            conflict_files.append(
                                str(file_path.relative_to(Path.cwd()))
                            )

                    except Exception as e:
                        logger.warning(
                            "failed_to_check_conflicts",
                            error=str(e),
                            file_path=str(file_path),
                        )

            if conflict_files:
                logger.warning(
                    "git_conflicts_detected",
                    conflict_count=len(conflict_files),
                    conflicts=conflict_files,
                )
                self.state_manager.set_sync_state("git_conflicts_detected", "true")
                self.state_manager.set_sync_state(
                    "conflict_files", json.dumps(conflict_files)
                )
            else:
                self.state_manager.set_sync_state("git_conflicts_detected", "false")
                self.state_manager.set_sync_state("conflict_files", "[]")

            return conflict_files

        except Exception as e:
            logger.error("Failed to check git conflicts", error=str(e), severity="data_error")
            return conflict_files

    def has_git_conflicts(self) -> bool:
        """Check if there are unresolved git conflicts."""
        try:
            conflicts_detected = self.state_manager.get_sync_state(
                "git_conflicts_detected"
            )
            return conflicts_detected == "true"
        except Exception as e:
            logger.debug("git_conflict_check_failed", error=str(e))
            # If we can't check, assume no conflicts to avoid blocking operations
            return False

    def get_conflict_files(self) -> list[str]:
        """Get list of files with git conflicts."""
        try:
            conflict_files_json = self.state_manager.get_sync_state("conflict_files")
            if conflict_files_json:
                return json.loads(conflict_files_json)
            return []
        except Exception as e:
            logger.debug("conflict_files_retrieval_failed", error=str(e))
            return []
