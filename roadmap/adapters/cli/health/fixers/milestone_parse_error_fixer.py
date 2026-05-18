"""Fixer for milestone files that fail to parse (invisible to CLI)."""

from pathlib import Path

from structlog import get_logger

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer
from roadmap.adapters.persistence.parser.milestone import MilestoneParser

logger = get_logger()


class MilestoneParseErrorFixer(HealthFixer):
    """Detects milestone files that exist on disk but fail to parse.

    Safety: REVIEW (regenerates files from minimal defaults, discarding
    unrecoverable YAML content)

    A milestone file that fails to parse is silently excluded from
    ``milestone list`` and ``milestone view``, causing confusing
    inconsistencies (issues are queryable by milestone name but the
    milestone itself is "not found").  This fixer surfaces those files
    so the user is not left guessing why a milestone disappeared.

    The ``apply()`` fix regenerates each broken file with sensible
    defaults derived from the filename, which replicates the manual
    workaround of running ``roadmap milestone create``.
    """

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "milestone_parse_errors"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - REVIEW because we overwrite files."""
        return FixSafety.REVIEW

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Detect milestone files that fail to parse and are invisible to the CLI"

    def scan(self) -> dict:
        """Scan for milestone files that cannot be parsed.

        Returns:
            Dict with found, count, message, details
        """
        broken = self._find_broken_milestone_files()

        return {
            "found": len(broken) > 0,
            "count": len(broken),
            "message": f"Found {len(broken)} milestone file(s) that fail to parse",
            "details": broken,
        }

    def dry_run(self) -> FixResult:
        """Preview which milestone files would be regenerated.

        Returns:
            FixResult with dry_run=True
        """
        broken = self._find_broken_milestone_files()

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would regenerate {len(broken)} milestone file(s) from defaults",
            affected_items=[item["file"] for item in broken],
            items_count=len(broken),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Regenerate broken milestone files with minimal valid defaults.

        Each broken file is overwritten with a new milestone whose ``name``
        is derived from the filename stem, preserving the original file
        location.  This replicates the manual workaround of recreating the
        milestone via ``roadmap milestone create``.

        Args:
            force: Ignored (safety handled by REVIEW level and orchestrator).

        Returns:
            FixResult
        """
        broken = self._find_broken_milestone_files()
        fixed_count = 0
        failed_items: list[str] = []

        for item in broken:
            file_path = Path(item["file"])
            milestone_name = item["name"]
            try:
                milestone = self.core.milestones.create(
                    name=milestone_name,
                    headline="",
                )
                if milestone:
                    fixed_count += 1
                else:
                    failed_items.append(str(file_path))
            except Exception as e:
                logger.error(
                    "milestone_parse_error_fix_failed",
                    file=str(file_path),
                    error=str(e),
                    severity="data_error",
                )
                failed_items.append(str(file_path))

        return FixResult(
            fix_type=self.fix_type,
            success=len(failed_items) == 0,
            dry_run=False,
            message=f"Regenerated {fixed_count}/{len(broken)} broken milestone file(s)",
            affected_items=[
                item["file"] for item in broken if item["file"] not in failed_items
            ],
            items_count=len(broken),
            changes_made=fixed_count,
        )

    def _find_broken_milestone_files(self) -> list[dict]:
        """Find milestone files that raise exceptions during parsing.

        Returns:
            List of dicts with 'file', 'name', 'error' keys
        """
        broken: list[dict] = []

        try:
            milestones_dir = Path(".roadmap/milestones").resolve()
            if not milestones_dir.exists():
                return broken

            for md_file in sorted(milestones_dir.glob("*.md")):
                if ".backup" in md_file.name:
                    continue
                try:
                    MilestoneParser.parse_milestone_file(md_file)
                except Exception as e:
                    broken.append(
                        {
                            "file": str(md_file),
                            "name": md_file.stem,
                            "error": f"{type(e).__name__}: {e}",
                        }
                    )
        except Exception as e:
            logger.error(
                "find_broken_milestone_files_failed",
                error=str(e),
                severity="data_error",
            )

        return broken
