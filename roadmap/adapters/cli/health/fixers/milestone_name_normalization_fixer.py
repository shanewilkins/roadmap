"""Fixer for normalizing milestone names to safe format in issue metadata."""

from pathlib import Path

from structlog import get_logger

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer

logger = get_logger()


class MilestoneNameNormalizationFixer(HealthFixer):
    """Normalizes issue milestone metadata to match milestone filenames.

    Safety: SAFE (just normalizes names to match actual milestones)

    Issues may have milestone names like 'v.0.8.0' but milestone files are 'v080.md'.
    This fixer updates issue metadata to use the safe filename format.
    """

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "milestone_name_normalization"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - SAFE because we're just normalizing names."""
        return FixSafety.SAFE

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Normalize milestone names to match milestone filenames"

    def scan(self) -> dict:
        """Scan for issues with non-normalized milestone names.

        Returns:
            Dict with found, count, message, details
        """
        mismatched = self._find_mismatched_milestone_names()

        return {
            "found": len(mismatched) > 0,
            "count": len(mismatched),
            "message": f"Found {len(mismatched)} issue(s) with non-normalized milestone name(s)",
            "details": [
                {
                    "id": iss["id"],
                    "title": iss["title"],
                    "current": iss["current_name"],
                    "should_be": iss["normalized_name"],
                }
                for iss in mismatched
            ],
        }

    def dry_run(self) -> FixResult:
        """Preview which issues would be fixed.

        Returns:
            FixResult with dry_run=True
        """
        mismatched = self._find_mismatched_milestone_names()

        affected = [
            f"{iss['id']} ({iss['current_name']} → {iss['normalized_name']})"
            for iss in mismatched
        ]

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would normalize {len(mismatched)} issue milestone name(s)",
            affected_items=affected,
            items_count=len(mismatched),
            changes_made=0,
        )

    def apply(self, _force: bool = False) -> FixResult:
        """Normalize milestone names in issue metadata.

        Args:
            _force: Ignored (SAFE fixers apply automatically)

        Returns:
            FixResult with fix results
        """
        mismatched = self._find_mismatched_milestone_names()
        fixed_count = 0
        failed_items = []

        for issue_data in mismatched:
            try:
                issue_id = issue_data["id"]
                normalized_name = issue_data["normalized_name"]

                # Assign to normalized milestone name
                if self.core.issues.assign_to_milestone(issue_id, normalized_name):
                    fixed_count += 1
                else:
                    failed_items.append(issue_id)
            except Exception as e:
                logger.error(
                    "normalize_milestone_failed",
                    issue_id=issue_data["id"],
                    error=str(e),
                    severity="data_error",
                )
                failed_items.append(issue_data["id"])

        return FixResult(
            fix_type=self.fix_type,
            success=len(failed_items) == 0,
            dry_run=False,
            message=f"Normalized {fixed_count}/{len(mismatched)} issue milestone name(s)",
            affected_items=[
                iss["id"] for iss in mismatched if iss["id"] not in failed_items
            ],
            items_count=len(mismatched),
            changes_made=fixed_count,
        )

    def _find_mismatched_milestone_names(self) -> list[dict]:
        """Find issues where milestone name doesn't match safe filename.

        Returns:
            List of dicts with id, title, current_name, normalized_name
        """
        mismatched = []

        try:
            milestones_dir = Path(".roadmap/milestones").resolve()
            if not milestones_dir.exists():
                return mismatched

            # Build map of display names to safe names
            safe_name_to_display = {}
            for f in milestones_dir.glob("*.md"):
                safe_name = f.stem
                # Try to find what display name might map to this
                safe_name_to_display[safe_name] = safe_name

            # Check all issues
            for issue in self.core.issues.list():
                if not issue.milestone:
                    continue

                # Convert issue's milestone to safe name
                safe_name = "".join(
                    c for c in issue.milestone if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                safe_name = safe_name.replace(" ", "-").lower()

                # Check if milestone file exists with this safe name
                milestone_file = milestones_dir / f"{safe_name}.md"
                if not milestone_file.exists():
                    # Milestone doesn't exist, skip
                    continue

                # If the safe name differs from the issue's milestone, it needs normalizing
                if safe_name != issue.milestone:
                    mismatched.append(
                        {
                            "id": issue.id,
                            "title": issue.title,
                            "current_name": issue.milestone,
                            "normalized_name": safe_name,
                        }
                    )

        except Exception as e:
            logger.error(
                "find_mismatched_milestones_failed", error=str(e), severity="data_error"
            )
            return []

        return mismatched
