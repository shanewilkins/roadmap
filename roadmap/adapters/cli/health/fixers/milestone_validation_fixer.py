"""Fixer for issues with invalid milestone references."""

from difflib import get_close_matches
from pathlib import Path

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer


class MilestoneValidationFixer(HealthFixer):
    """Validates that all issue milestones point to existing milestones.

    Safety: REVIEW (may reassign issues to different milestones)

    Issues with invalid milestone references are either:
    1. Moved to backlog if no similar milestone found
    2. Updated to closest matching milestone if found
    """

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "milestone_validation"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - REVIEW because we may reassign milestones."""
        return FixSafety.REVIEW

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Validate and fix invalid milestone references in issues"

    def scan(self) -> dict:
        """Scan for issues with invalid milestone references.

        Returns:
            Dict with found, count, message, details
        """
        invalid = self._find_invalid_milestones()

        return {
            "found": len(invalid) > 0,
            "count": len(invalid),
            "message": f"Found {len(invalid)} issue(s) with invalid milestone(s)",
            "details": [
                {
                    "id": iss["id"],
                    "title": iss["title"],
                    "invalid_milestone": iss["milestone"],
                }
                for iss in invalid
            ],
        }

    def dry_run(self) -> FixResult:
        """Preview which issues would be fixed.

        Returns:
            FixResult with dry_run=True
        """
        invalid = self._find_invalid_milestones()

        affected = []
        for iss in invalid:
            suggestion = self._get_suggestion(iss["milestone"])
            if suggestion:
                affected.append(f"{iss['id']} ({iss['milestone']} → {suggestion})")
            else:
                affected.append(f"{iss['id']} ({iss['milestone']} → backlog)")

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would fix {len(invalid)} issue(s) with invalid milestone(s)",
            affected_items=affected,
            items_count=len(invalid),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Fix issues with invalid milestone references.

        Args:
            force: Ignored (MODERATE fixers apply automatically)

        Returns:
            FixResult with fix results
        """
        invalid = self._find_invalid_milestones()
        fixed_count = 0
        failed_items = []

        for issue_data in invalid:
            try:
                issue_id = issue_data["id"]
                old_milestone = issue_data["milestone"]

                # Try to find a suggestion
                suggestion = self._get_suggestion(old_milestone)
                if not suggestion:
                    # No similar milestone, move to backlog
                    suggestion = "backlog"

                # Assign to suggested milestone
                if self.core.issues.assign_to_milestone(issue_id, suggestion):
                    fixed_count += 1
                else:
                    failed_items.append(issue_id)
            except Exception:
                failed_items.append(issue_data["id"])

        return FixResult(
            fix_type=self.fix_type,
            success=len(failed_items) == 0,
            dry_run=False,
            message=f"Fixed {fixed_count}/{len(invalid)} issue(s) with invalid milestone(s)",
            affected_items=[
                iss["id"] for iss in invalid if iss["id"] not in failed_items
            ],
            items_count=len(invalid),
            changes_made=fixed_count,
        )

    def _find_invalid_milestones(self) -> list[dict]:
        """Find issues with milestone references that don't exist.

        Returns:
            List of dicts with id, title, milestone
        """
        invalid = []

        try:
            # Get all available milestone names
            milestones_dir = Path(".roadmap/milestones").resolve()
            if not milestones_dir.exists():
                return invalid

            available_milestones = {f.stem for f in milestones_dir.glob("*.md")}

            # Check all issues
            for issue in self.core.issues.list():
                if not issue.milestone:
                    # No milestone is valid (goes to backlog)
                    continue

                # Convert milestone name to safe filename for comparison
                safe_name = "".join(
                    c for c in issue.milestone if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                safe_name = safe_name.replace(" ", "-").lower()

                if safe_name not in available_milestones:
                    invalid.append(
                        {
                            "id": issue.id,
                            "title": issue.title,
                            "milestone": issue.milestone,
                        }
                    )

        except Exception:
            return []

        return invalid

    def _get_suggestion(self, invalid_milestone: str) -> str | None:
        """Find a suggested milestone for an invalid one.

        Args:
            invalid_milestone: The invalid milestone name

        Returns:
            Suggested milestone name, or None if no good match found
        """
        try:
            milestones_dir = Path(".roadmap/milestones").resolve()
            if not milestones_dir.exists():
                return None

            available = [f.stem for f in milestones_dir.glob("*.md")]

            # Find close matches
            matches = get_close_matches(invalid_milestone, available, n=1, cutoff=0.6)
            return matches[0] if matches else None
        except Exception:
            return None
