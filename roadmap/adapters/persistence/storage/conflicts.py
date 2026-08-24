"""Git conflict detection and handling service."""

from pathlib import Path

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class ConflictService:
    """Service for detecting and managing git conflicts in .roadmap directory."""

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
            return conflict_files

        except Exception as e:
            logger.error(
                "Failed to check git conflicts", error=str(e), severity="data_error"
            )
            return conflict_files

    def has_git_conflicts(self) -> bool:
        """Check if there are unresolved git conflicts."""
        return bool(self.check_git_conflicts())

    def get_conflict_files(self) -> list[str]:
        """Get list of files with git conflicts."""
        return self.check_git_conflicts()
