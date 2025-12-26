"""Fixer for orphaned issues (issues not in correct folder based on milestone)."""

import shutil
from pathlib import Path

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer
from roadmap.core.domain.issue import Status


class OrphanedIssuesFixer(HealthFixer):
    """Moves issues to correct folders based on their milestone assignment.

    Safety: SAFE (moves files based on explicit metadata)

    "Orphaned" = issues in wrong folder (not matching their milestone).
    Fixes by moving issues to correct folder:
    - .roadmap/issues/{milestone}/ for open issues
    - .roadmap/archive/issues/{milestone}/ for closed issues
    """

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "orphaned_issues"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - SAFE because we use explicit metadata."""
        return FixSafety.SAFE

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Move unassigned/misplaced issues to backlog or correct folders based on milestone assignment"

    def scan(self) -> dict:
        """Scan for orphaned issues (in wrong folder).

        Returns:
            Dict with found, count, message, details
        """
        misplaced = self._find_misplaced_issues()

        return {
            "found": len(misplaced) > 0,
            "count": len(misplaced),
            "message": f"Found {len(misplaced)} issue(s) in wrong folder",
            "details": [{"id": iss["id"], "title": iss["title"]} for iss in misplaced],
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
            affected_items=[
                f"{iss['id']} → {iss['target_folder']}" for iss in misplaced
            ],
            items_count=len(misplaced),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Move orphaned issues to correct folders.

        Args:
            force: Ignored (SAFE fixers apply automatically)

        Returns:
            FixResult with move results
        """
        misplaced = self._find_misplaced_issues()
        moved_count = 0
        failed_items = []

        # Ensure backlog folder exists
        backlog_path = Path(".roadmap/issues/backlog").resolve()
        backlog_path.mkdir(parents=True, exist_ok=True)

        issues_dir = Path(".roadmap/issues").resolve()

        for issue_data in misplaced:
            try:
                issue_id = issue_data["id"]
                target_folder = Path(issue_data["target_folder"]).resolve()
                current_folder = Path(issue_data["current_folder"]).resolve()

                # If milestone folder doesn't exist and not already at backlog, move to backlog
                if not target_folder.exists() and current_folder != backlog_path:
                    target_folder = backlog_path

                # Ensure target folder exists
                target_folder.mkdir(parents=True, exist_ok=True)

                # Find the actual issue file
                issue_file = None
                if current_folder == issues_dir:
                    # File is at root level
                    for f in issues_dir.glob(f"{issue_id}*.md"):
                        if f.is_file():
                            issue_file = f
                            break
                else:
                    # File is in a subfolder
                    for f in current_folder.glob(f"{issue_id}*.md"):
                        if f.is_file():
                            issue_file = f
                            break

                if issue_file:
                    # Move file to target folder
                    target_file = target_folder / issue_file.name
                    shutil.move(str(issue_file), str(target_file))
                    moved_count += 1
                else:
                    failed_items.append(issue_id)
            except Exception:
                failed_items.append(issue_data["id"])

        return FixResult(
            fix_type=self.fix_type,
            success=len(failed_items) == 0,
            dry_run=False,
            message=f"Moved {moved_count}/{len(misplaced)} issue(s) to correct folder(s)",
            affected_items=[
                iss["id"] for iss in misplaced if iss["id"] not in failed_items
            ],
            items_count=len(misplaced),
            changes_made=moved_count,
        )

    def _find_misplaced_issues(self) -> list[dict]:
        """Find issues that are in the wrong folder.

        Returns:
            List of dicts with id, title, current_folder, target_folder, milestone
        """
        misplaced = []

        try:
            issues_dir = Path(".roadmap/issues").resolve()
            archive_dir = Path(".roadmap/archive/issues").resolve()

            if not issues_dir.exists():
                return misplaced

            # Scan all issues
            for issue in self.core.issues.list():
                # Determine expected folder
                expected_folder = self._get_expected_folder(issue)

                # Find actual file and its folder
                actual_folder = self._find_issue_folder(
                    issue.id, issues_dir, archive_dir
                )

                # Issue is misplaced if:
                # 1. It's at root level (actual_folder == issues_dir)
                # 2. Or it's in wrong folder (actual_folder != expected_folder)
                if actual_folder:
                    if actual_folder == issues_dir or actual_folder != expected_folder:
                        misplaced.append(
                            {
                                "id": issue.id,
                                "title": issue.title,
                                "milestone": issue.milestone or "(none)",
                                "current_folder": str(actual_folder),
                                "target_folder": str(expected_folder),
                            }
                        )

        except Exception:
            return []

        return misplaced

    def _get_expected_folder(self, issue) -> Path:
        """Determine the expected folder for an issue.

        Args:
            issue: Issue object with milestone and status

        Returns:
            Path to the expected folder
        """
        # Closed issues go to archive
        base_path = (
            Path(".roadmap/archive/issues").resolve()
            if issue.status == Status.CLOSED
            else Path(".roadmap/issues").resolve()
        )

        # If no milestone, assign to backlog
        milestone = issue.milestone or "backlog"

        return base_path / milestone

    def _find_issue_folder(
        self, issue_id: str, issues_dir: Path, archive_dir: Path
    ) -> Path | None:
        """Find the actual folder containing an issue.

        Args:
            issue_id: Issue ID to find
            issues_dir: Path to .roadmap/issues
            archive_dir: Path to .roadmap/archive/issues

        Returns:
            Path to the folder containing the issue, or None
        """
        # Check if file is at root level (loose file)
        for file in issues_dir.glob(f"{issue_id}*.md"):
            if file.is_file():
                return issues_dir  # Return root to indicate it's loose

        # Check main issues directory subfolders
        for folder in issues_dir.iterdir():
            if folder.is_dir():
                for _file in folder.glob(f"{issue_id}*.md"):
                    return folder

        # Check archive directory
        archive_dir = Path(".roadmap/archive/issues").resolve()
        if archive_dir.exists():
            for folder in archive_dir.iterdir():
                if folder.is_dir():
                    for _file in folder.glob(f"{issue_id}*.md"):
                        return folder

        return None
