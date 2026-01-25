"""Fixer for milestone naming convention compliance.

This fixer ensures that:
1. Issue milestone values use actual milestone filenames (safe names)
2. No display name variants (v.0.8.0) are used instead of safe names (v080)
3. All naming is consistent across the system
"""

from pathlib import Path

from structlog import get_logger

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer

logger = get_logger()


class MilestoneNamingComplianceFixer(HealthFixer):
    """Fixes milestone names to match actual milestone filenames.

    Converts display names like "v.0.8.0", "Future (Post-v1.0)" to their
    actual safe milestone names like "v080", "future-post-v10".
    """

    def __init__(self, core):
        """Initialize fixer with core instance."""
        super().__init__(core)
        self.logger = logger

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "milestone_naming_compliance"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - SAFE because we fix to actual milestone names."""
        return FixSafety.SAFE

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Fix milestone naming to match actual milestone filenames"

    def scan(self) -> dict:
        """Scan for issues with non-compliant milestone names.

        Returns:
            Dict with found, count, message, details
        """
        non_compliant = self._find_non_compliant_milestones()

        return {
            "found": len(non_compliant) > 0,
            "count": len(non_compliant),
            "message": f"Found {len(non_compliant)} issue(s) with non-compliant milestone name(s)",
            "details": [
                {
                    "id": iss["id"],
                    "title": iss["title"],
                    "current": iss["current_milestone"],
                    "should_be": iss["safe_milestone"],
                }
                for iss in non_compliant
            ],
        }

    def dry_run(self) -> FixResult:
        """Preview which issues would be fixed.

        Returns:
            FixResult with dry_run=True
        """
        non_compliant = self._find_non_compliant_milestones()

        affected = []
        for iss in non_compliant:
            affected.append(
                f"{iss['id']} ({iss['current_milestone']} → {iss['safe_milestone']})"
            )

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would fix {len(non_compliant)} issue(s) with non-compliant milestone name(s)",
            affected_items=affected,
            items_count=len(non_compliant),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Apply milestone naming compliance fixes.

        Args:
            force: Not used for SAFE fixers

        Returns:
            FixResult with fix details
        """
        non_compliant = self._find_non_compliant_milestones()

        if not non_compliant:
            return FixResult(
                fix_type=self.fix_type,
                success=True,
                dry_run=False,
                message="No non-compliant milestone names found",
                items_count=0,
                changes_made=0,
            )

        affected = []
        fixed = 0
        failed = 0

        for iss in non_compliant:
            try:
                # Update the issue file directly
                file_path = Path(iss["file"])
                content = file_path.read_text(encoding="utf-8")

                # Replace milestone value
                old_line = f"milestone: {iss['current_milestone']}"
                new_line = f"milestone: {iss['safe_milestone']}"

                updated_content = content.replace(old_line, new_line, 1)
                file_path.write_text(updated_content, encoding="utf-8")

                affected.append(
                    f"{iss['id']} ({iss['current_milestone']} → {iss['safe_milestone']})"
                )
                fixed += 1
            except Exception as e:
                self.logger.error(f"Failed to fix milestone for {iss['id']}: {e}")
                failed += 1

        return FixResult(
            fix_type=self.fix_type,
            success=failed == 0,
            dry_run=False,
            message=f"Fixed {fixed} issue(s) with non-compliant milestone name(s)",
            affected_items=affected,
            items_count=len(non_compliant),
            changes_made=fixed,
        )

    def _find_non_compliant_milestones(self) -> list[dict]:
        """Find all issues with non-compliant milestone names.

        Returns:
            List of issue dicts with: id, title, current_milestone, safe_milestone
        """
        issues = []
        issues_dir = Path(".roadmap/issues").resolve()
        milestones_dir = Path(".roadmap/milestones").resolve()

        # Get all actual milestone files (safe names)
        actual_milestones = set()
        if milestones_dir.exists():
            for f in milestones_dir.glob("*.md"):
                actual_milestones.add(f.stem)

        # Map display names to safe names
        display_to_safe = {
            "v.0.7.0": "v070",
            "v.0.8.0": "v080",
            "v.0.9.0": "v090",
            "v.1.0.0": "v100",
            "v.0.8": "v080",
            "v0.8": "v080",
            "v0.8.0": "v080",
            "v.0.7": "v070",
            "v0.7": "v070",
            "v.0.9": "v090",
            "v0.9": "v090",
            "v.1.0": "v100",
            "v1.0": "v100",
            "Future (Post-v1.0)": "future-post-v10",
            "Development": "backlog",
        }

        if not issues_dir.exists():
            return issues

        for issue_file in issues_dir.rglob("*.md"):
            if issue_file.name.startswith("."):
                continue

            # Parse YAML frontmatter
            content = issue_file.read_text(encoding="utf-8")
            current_milestone = None
            title = None

            for line in content.split("\n"):
                if line.startswith("milestone:"):
                    current_milestone = line.replace("milestone:", "").strip()
                elif line.startswith("title:"):
                    title = line.replace("title:", "").strip().strip("'\"")

            if not current_milestone:
                continue

            # Check if it's already a safe name
            if current_milestone in actual_milestones:
                continue

            # Check if it's empty string or space
            if not current_milestone or current_milestone.isspace():
                safe_milestone = "backlog"
            else:
                # Check if it's a display name that needs conversion
                safe_milestone = display_to_safe.get(current_milestone, "backlog")

                # Verify safe milestone exists
                if safe_milestone not in actual_milestones:
                    safe_milestone = "backlog"

            if safe_milestone != current_milestone:
                issues.append(
                    {
                        "id": issue_file.stem.split("-")[0],
                        "title": title or issue_file.stem,
                        "file": str(issue_file),
                        "current_milestone": current_milestone,
                        "safe_milestone": safe_milestone,
                    }
                )

        return issues
