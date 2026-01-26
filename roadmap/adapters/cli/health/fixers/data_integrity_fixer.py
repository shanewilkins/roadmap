"""Fixer for data integrity issues (malformed files)."""

from pathlib import Path

from structlog import get_logger

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer
from roadmap.adapters.persistence.parser import IssueParser

logger = get_logger()


class DataIntegrityFixer(HealthFixer):
    """Fixes data integrity issues by removing or repairing malformed files.

    Safety: REVIEW (removes files that can't be parsed)

    Attempts to identify and remove malformed issue files.
    """

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "data_integrity"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - REVIEW because removes files."""
        return FixSafety.REVIEW

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Remove or repair malformed issue files"

    def scan(self) -> dict:
        """Scan for malformed files.

        Returns:
            Dict with found, count, message, details
        """
        malformed = self._find_malformed_files()

        return {
            "found": len(malformed) > 0,
            "count": len(malformed),
            "message": f"Found {len(malformed)} malformed file(s)",
            "details": [{"file": f} for f in malformed],
        }

    def dry_run(self) -> FixResult:
        """Preview which files would be removed.

        Returns:
            FixResult with dry_run=True
        """
        malformed = self._find_malformed_files()

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would remove {len(malformed)} malformed file(s)",
            affected_items=malformed,
            items_count=len(malformed),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Remove malformed files.

        Args:
            force: If True, remove without confirmation

        Returns:
            FixResult with removal results
        """
        malformed = self._find_malformed_files()
        removed_count = 0

        for file_path in malformed:
            try:
                full_path = Path(".roadmap/issues") / file_path
                if full_path.exists():
                    full_path.unlink()
                    removed_count += 1
            except Exception as e:
                logger.error(
                    "remove_malformed_file_failed",
                    file_path=file_path,
                    error=str(e),
                    severity="system_error",
                )

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=False,
            message=f"Removed {removed_count}/{len(malformed)} malformed file(s)",
            affected_items=malformed,
            items_count=len(malformed),
            changes_made=removed_count,
        )

    def _find_malformed_files(self) -> list[str]:
        """Find malformed issue files.

        Returns:
            List of file paths relative to .roadmap/issues
        """
        malformed = []
        issues_dir = Path(".roadmap/issues")

        if not issues_dir.exists():
            return malformed

        try:
            for issue_file in issues_dir.rglob("*.md"):
                # Skip backup files
                if ".backup" in issue_file.name:
                    continue

                try:
                    IssueParser.parse_issue_file(issue_file)
                except Exception as e:
                    logger.debug(
                        "issue_file_parse_failed", file=str(issue_file), error=str(e)
                    )
                    # File couldn't be parsed
                    malformed.append(str(issue_file.relative_to(issues_dir)))
        except Exception as e:
            logger.error(
                "malformed_files_check_failed", error=str(e), severity="system_error"
            )
            return []

        return malformed
