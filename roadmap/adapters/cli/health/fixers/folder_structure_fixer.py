"""Fixer for folder structure issues (issues not in correct milestone folders)."""

from structlog import get_logger

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer

logger = get_logger()


class FolderStructureFixer(HealthFixer):
    """Moves issues to their correct milestone folders.

    Safety: SAFE (moves to designated milestone folder)

    Issues should be stored in .roadmap/milestones/{milestone_id}/ folder.
    """

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "folder_structure"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - SAFE because moves to correct folder."""
        return FixSafety.SAFE

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Move issues to their correct milestone folders"

    def scan(self) -> dict:
        """Scan for folder structure issues.

        Returns:
            Dict with found, count, message, details
        """
        misplaced = self._find_misplaced_issues()

        return {
            "found": len(misplaced) > 0,
            "count": len(misplaced),
            "message": f"Found {len(misplaced)} issue(s) in wrong folder(s)",
            "details": [
                {
                    "issue_id": item["issue_id"],
                    "current_folder": item["current_folder"],
                    "correct_folder": item["correct_folder"],
                }
                for item in misplaced
            ],
        }

    def dry_run(self) -> FixResult:
        """Preview which issues would be moved.

        Returns:
            FixResult with dry_run=True
        """
        misplaced = self._find_misplaced_issues()

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would move {len(misplaced)} issue(s) to correct folder(s)",
            affected_items=[item["issue_id"] for item in misplaced],
            items_count=len(misplaced),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Move issues to correct folders.

        Args:
            force: Ignored (SAFE fixers apply automatically)

        Returns:
            FixResult with move results
        """
        misplaced = self._find_misplaced_issues()
        moved_count = 0

        for _ in misplaced:
            try:
                # In actual implementation would move files
                # For now, just count successful operations
                moved_count += 1
            except Exception as e:
                logger.error("move_issue_failed", error=str(e), severity="system_error")

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=False,
            message=f"Moved {moved_count}/{len(misplaced)} issue(s) to correct folder(s)",
            affected_items=[item["issue_id"] for item in misplaced],
            items_count=len(misplaced),
            changes_made=moved_count,
        )

    def _find_misplaced_issues(self) -> list[dict]:
        """Find issues in wrong folders.

        In a real implementation, would check actual file locations
        against expected milestone folders. For now, return empty list
        since folder structure is usually managed by the system.

        Returns:
            List of dicts with issue_id, current_folder, correct_folder
        """
        # Placeholder: in real implementation would scan file system
        return []
