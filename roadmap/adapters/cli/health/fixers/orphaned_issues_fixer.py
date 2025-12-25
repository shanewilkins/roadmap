"""Fixer for orphaned issues (not assigned to any milestone)."""

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer


class OrphanedIssuesFixer(HealthFixer):
    """Assigns unassigned issues to Backlog milestone.

    Safety: SAFE (assigns to standard Backlog)

    Issues without a milestone are assigned to 'Backlog'.
    """

    BACKLOG_NAME = "Backlog"

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "orphaned_issues"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - SAFE because Backlog is default location."""
        return FixSafety.SAFE

    @property
    def description(self) -> str:
        """Return fixer description."""
        return f"Assign unassigned issues to '{self.BACKLOG_NAME}' milestone"

    def scan(self) -> dict:
        """Scan for orphaned issues.

        Returns:
            Dict with found, count, message, details
        """
        orphaned = self._find_orphaned_issues()

        return {
            "found": len(orphaned) > 0,
            "count": len(orphaned),
            "message": f"Found {len(orphaned)} issue(s) not assigned to any milestone",
            "details": [{"id": iss["id"], "title": iss["title"]} for iss in orphaned],
        }

    def dry_run(self) -> FixResult:
        """Preview which issues would be assigned.

        Returns:
            FixResult with dry_run=True
        """
        orphaned = self._find_orphaned_issues()

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would assign {len(orphaned)} issue(s) to '{self.BACKLOG_NAME}'",
            affected_items=[iss["id"] for iss in orphaned],
            items_count=len(orphaned),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Assign orphaned issues to Backlog.

        Args:
            force: Ignored (SAFE fixers apply automatically)

        Returns:
            FixResult with assignment results
        """
        orphaned = self._find_orphaned_issues()
        assigned_count = 0

        # Get or create Backlog milestone
        backlog = self._get_or_create_backlog()

        if not backlog:
            return FixResult(
                fix_type=self.fix_type,
                success=False,
                dry_run=False,
                message=f"Failed to find or create '{self.BACKLOG_NAME}' milestone",
                items_count=len(orphaned),
                changes_made=0,
            )

        # Assign issues
        for issue_data in orphaned:
            try:
                issue = self.core.issues.get(issue_data["id"])
                if issue:
                    issue.milestone_id = backlog.id
                    self.core.issues.update(issue)
                    assigned_count += 1
            except Exception:
                pass

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=False,
            message=f"Assigned {assigned_count}/{len(orphaned)} issue(s) to '{self.BACKLOG_NAME}'",
            affected_items=[iss["id"] for iss in orphaned],
            items_count=len(orphaned),
            changes_made=assigned_count,
        )

    def _find_orphaned_issues(self) -> list[dict]:
        """Find issues not assigned to any milestone.

        Returns:
            List of dicts with id and title
        """
        orphaned = []

        try:
            for issue in self.core.issues.list():
                if not issue.milestone_id:
                    orphaned.append(
                        {
                            "id": issue.id,
                            "title": issue.title,
                        }
                    )
        except Exception:
            return []

        return orphaned

    def _get_or_create_backlog(self):
        """Get Backlog milestone or create if doesn't exist.

        Returns:
            Milestone object or None
        """
        try:
            # Try to find existing Backlog
            for milestone in self.core.milestones.list():
                if milestone.name.lower() == self.BACKLOG_NAME.lower():
                    return milestone

            # Create Backlog if not found
            backlog = self.core.milestones.create(
                name=self.BACKLOG_NAME,
                description="Backlog of unscheduled work",
                status="open",
            )
            return backlog
        except Exception:
            return None
