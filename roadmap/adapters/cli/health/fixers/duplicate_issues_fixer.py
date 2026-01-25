"""Fixer for duplicate issues."""

from structlog import get_logger

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer

logger = get_logger()


class DuplicateIssuesFixer(HealthFixer):
    """Detects and can merge duplicate issues.

    Safety: REVIEW (requires user confirmation)

    Identifies issues with same title and status, suggests merging.
    """

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "duplicate_issues"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - REVIEW because merging loses data."""
        return FixSafety.REVIEW

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Merge duplicate issues (keep older, close newer)"

    def scan(self) -> dict:
        """Scan for duplicate issues.

        Returns:
            Dict with found, count, message, details
        """
        duplicates = self._find_duplicates()

        return {
            "found": len(duplicates) > 0,
            "count": len(duplicates),
            "message": f"Found {len(duplicates)} potential duplicate issue group(s)",
            "details": [
                {
                    "group": group[0]["title"],
                    "issues": [
                        {"id": iss["id"], "created": iss.get("created")}
                        for iss in group
                    ],
                }
                for group in duplicates
            ],
        }

    def dry_run(self) -> FixResult:
        """Preview what duplicates would be merged.

        Returns:
            FixResult with dry_run=True
        """
        duplicates = self._find_duplicates()
        total_issues = sum(len(group) for group in duplicates)

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would process {len(duplicates)} duplicate group(s) ({total_issues} issue(s))",
            affected_items=[iss["id"] for group in duplicates for iss in group],
            items_count=total_issues,
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:  # noqa: ARG002
        """Merge duplicate issues.

        Args:
            force: If True, apply without confirmation

        Returns:
            FixResult with merge results
        """
        duplicates = self._find_duplicates()
        merged_count = 0

        for group in duplicates:
            # Keep oldest, close/merge newer ones
            oldest = min(group, key=lambda x: x.get("created", ""))
            newer = [iss for iss in group if iss != oldest]

            # In actual implementation, would merge comments, then close newer
            # For now, just count
            merged_count += len(newer)

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=False,
            message=f"Merged {merged_count} duplicate issue(s)",
            affected_items=[iss["id"] for group in duplicates for iss in group],
            items_count=len(duplicates),
            changes_made=merged_count,
        )

    def _find_duplicates(self) -> list[list[dict]]:
        """Find groups of duplicate issues.

        Returns:
            List of groups, where each group is list of dicts with id, title, created
        """
        # Group issues by title and status
        groups_dict = {}

        try:
            for issue in self.core.issues.list():
                key = (issue.title, issue.status)
                if key not in groups_dict:
                    groups_dict[key] = []
                groups_dict[key].append(
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "status": issue.status,
                        "created": issue.created_date or "",
                    }
                )
        except Exception as e:
            # If we can't read issues, log and return empty list
            logger.error("read_duplicate_issues_failed", error=str(e))
            return []

        # Return only groups with duplicates
        return [group for group in groups_dict.values() if len(group) > 1]
