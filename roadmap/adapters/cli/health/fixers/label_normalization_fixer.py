"""Fixer for normalizing issue labels to alphabetically sorted order."""

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer


class LabelNormalizationFixer(HealthFixer):
    """Normalizes issue labels to alphabetically sorted order.

    Safety: SAFE (just reorders labels, no data loss)

    GitHub may return labels in different order than local storage, causing false
    "needs push" detection during sync. This fixer ensures labels are always
    stored in alphabetical order for consistency.
    """

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "label_normalization"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - SAFE because we're just reordering labels."""
        return FixSafety.SAFE

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Normalize issue labels to alphabetical order"

    def scan(self) -> dict:
        """Scan for issues with unsorted labels.

        Returns:
            Dict with found, count, message, details
        """
        unsorted_issues = self._find_unsorted_labels()

        return {
            "found": len(unsorted_issues) > 0,
            "count": len(unsorted_issues),
            "message": f"Found {len(unsorted_issues)} issue(s) with unsorted labels",
            "details": [
                {
                    "id": iss["id"],
                    "title": iss["title"],
                    "current": iss["current_labels"],
                    "sorted": iss["sorted_labels"],
                }
                for iss in unsorted_issues
            ],
        }

    def dry_run(self) -> FixResult:
        """Preview which issues would have labels sorted.

        Returns:
            FixResult with dry_run=True
        """
        unsorted_issues = self._find_unsorted_labels()

        affected = [
            f"{iss['id']}: {iss['current_labels']} → {iss['sorted_labels']}"
            for iss in unsorted_issues
        ]

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would normalize {len(unsorted_issues)} issue label(s)",
            affected_items=affected,
            items_count=len(unsorted_issues),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Sort labels in all issues to alphabetical order.

        Args:
            force: If True, skip confirmation prompt

        Returns:
            FixResult with results of applying fixes
        """
        unsorted_issues = self._find_unsorted_labels()

        if not unsorted_issues:
            return FixResult(
                fix_type=self.fix_type,
                success=True,
                dry_run=False,
                message="No issues found with unsorted labels",
                affected_items=[],
                items_count=0,
                changes_made=0,
            )

        affected = []
        changes = 0

        try:
            for issue_data in unsorted_issues:
                issue = issue_data["issue"]
                sorted_labels = issue_data["sorted_labels"]

                # Update the issue with sorted labels
                issue.labels = sorted_labels

                # Save the issue
                self.core.issues.update(issue)

                affected.append(f"{issue.id} ({len(sorted_labels)} labels sorted)")
                changes += 1

            return FixResult(
                fix_type=self.fix_type,
                success=True,
                dry_run=False,
                message=f"Normalized labels in {changes} issue(s)",
                affected_items=affected,
                items_count=len(unsorted_issues),
                changes_made=changes,
            )

        except Exception as e:
            return FixResult(
                fix_type=self.fix_type,
                success=False,
                dry_run=False,
                message=f"Failed to normalize labels: {str(e)}",
                affected_items=affected,
                items_count=len(unsorted_issues),
                changes_made=changes,
            )

    def _find_unsorted_labels(self) -> list[dict]:
        """Find all issues with unsorted labels.

        Returns:
            List of dicts with issue data and label info
        """
        unsorted_issues = []

        # Get all local issues including archived
        all_issues = self.core.issues.list_all_including_archived()

        for issue in all_issues:
            if not issue.labels:
                continue

            # Check if labels are sorted
            sorted_labels = sorted(issue.labels)
            if issue.labels != sorted_labels:
                unsorted_issues.append(
                    {
                        "id": issue.id,
                        "issue": issue,
                        "title": issue.title,
                        "current_labels": issue.labels,
                        "sorted_labels": sorted_labels,
                    }
                )

        return unsorted_issues
