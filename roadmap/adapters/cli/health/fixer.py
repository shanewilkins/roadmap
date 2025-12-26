"""Health check fixer orchestrator and base infrastructure.

Provides framework for automatically fixing detected health issues with:
- Safe/review categorization
- Dry-run preview mode (default)
- Rollback capability tracking
- Detailed fix result reporting
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FixSafety(Enum):
    """Safety level for a fixer.

    SAFE: Can be applied automatically without human review
    REVIEW: Requires human review before applying
    """

    SAFE = "safe"
    REVIEW = "review"


@dataclass
class FixResult:
    """Result of a fix operation.

    Attributes:
        fix_type: Type of fix that was applied
        success: Whether the fix succeeded
        dry_run: Whether this was a dry-run
        message: Description of what was fixed
        affected_items: IDs or names of affected entities
        items_count: Number of items affected
        changes_made: Number of changes actually made
        rollback_info: Information for rolling back (if applicable)
    """

    fix_type: str
    success: bool
    dry_run: bool
    message: str
    affected_items: list[str] = field(default_factory=list)
    items_count: int = 0
    changes_made: int = 0
    rollback_info: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "fix_type": self.fix_type,
            "success": self.success,
            "dry_run": self.dry_run,
            "message": self.message,
            "affected_items": self.affected_items,
            "items_count": self.items_count,
            "changes_made": self.changes_made,
            "has_rollback": self.rollback_info is not None,
        }


class HealthFixer(ABC):
    """Abstract base class for health check fixers.

    Each fixer handles a specific type of health issue:
    - old_backups: Delete old backup files
    - duplicate_issues: Merge duplicate issues
    - orphaned_issues: Assign unassigned issues to Backlog
    - folder_structure: Move issues to correct milestone folders
    - corrupted_comments: Sanitize malformed JSON comments
    """

    def __init__(self, core):
        """Initialize fixer with core instance.

        Args:
            core: Core application instance
        """
        self.core = core

    @property
    @abstractmethod
    def fix_type(self) -> str:
        """Identifier for this fixer (e.g., 'duplicate_issues')."""
        pass

    @property
    @abstractmethod
    def safety_level(self) -> FixSafety:
        """Safety level: SAFE or REVIEW."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this fixer does."""
        pass

    @abstractmethod
    def scan(self) -> dict[str, Any]:
        """Scan for issues that can be fixed.

        Returns:
            Dict with:
            - found: bool (whether issues were found)
            - count: int (number of issues found)
            - message: str (description)
            - details: list (specific issues found)
        """
        pass

    @abstractmethod
    def dry_run(self) -> FixResult:
        """Preview what would be fixed without making changes.

        Returns:
            FixResult with dry_run=True
        """
        pass

    @abstractmethod
    def apply(self, force: bool = False) -> FixResult:
        """Apply the fix (actually make changes).

        Args:
            force: If True, apply without prompts

        Returns:
            FixResult with dry_run=False
        """
        pass

    def confirm_apply(self, dry_run_result: FixResult) -> bool:
        """Ask user to confirm applying a fix.

        For SAFE fixes, this can auto-approve.
        For REVIEW fixes, user must manually confirm.

        Args:
            dry_run_result: Result from dry_run()

        Returns:
            True if user confirms, False otherwise
        """
        if self.safety_level == FixSafety.SAFE:
            return True

        # REVIEW fixes require user confirmation
        import click

        message = f"\nApply {self.fix_type}? {dry_run_result.message}"
        return click.confirm(message, default=False)


class HealthFixOrchestrator:
    """Orchestrates health fixes across all available fixers.

    Handles:
    - Loading all available fixers
    - Running dry-run previews
    - Applying fixes with proper safety checks
    - Collecting results
    """

    def __init__(self, core):
        """Initialize orchestrator.

        Args:
            core: Core application instance
        """
        self.core = core
        self._fixers: dict[str, HealthFixer] = {}
        self._load_fixers()

    def _load_fixers(self) -> None:
        """Load all available fixers."""
        from roadmap.adapters.cli.health.fixers.corrupted_comments_fixer import (
            CorruptedCommentsFixer,
        )
        from roadmap.adapters.cli.health.fixers.data_integrity_fixer import (
            DataIntegrityFixer,
        )
        from roadmap.adapters.cli.health.fixers.duplicate_issues_fixer import (
            DuplicateIssuesFixer,
        )
        from roadmap.adapters.cli.health.fixers.folder_structure_fixer import (
            FolderStructureFixer,
        )
        from roadmap.adapters.cli.health.fixers.milestone_name_normalization_fixer import (
            MilestoneNameNormalizationFixer,
        )
        from roadmap.adapters.cli.health.fixers.milestone_naming_compliance_fixer import (
            MilestoneNamingComplianceFixer,
        )
        from roadmap.adapters.cli.health.fixers.milestone_validation_fixer import (
            MilestoneValidationFixer,
        )
        from roadmap.adapters.cli.health.fixers.old_backups_fixer import (
            OldBackupsFixer,
        )
        from roadmap.adapters.cli.health.fixers.orphaned_issues_fixer import (
            OrphanedIssuesFixer,
        )

        fixers = [
            OldBackupsFixer(self.core),
            DuplicateIssuesFixer(self.core),
            OrphanedIssuesFixer(self.core),
            FolderStructureFixer(self.core),
            CorruptedCommentsFixer(self.core),
            DataIntegrityFixer(self.core),
            MilestoneNameNormalizationFixer(self.core),
            MilestoneNamingComplianceFixer(self.core),
            MilestoneValidationFixer(self.core),
        ]

        for fixer in fixers:
            self._fixers[fixer.fix_type] = fixer

    def get_fixers(self) -> dict[str, HealthFixer]:
        """Get all available fixers.

        Returns:
            Dict mapping fix_type to HealthFixer instance
        """
        return self._fixers.copy()

    def get_fixer(self, fix_type: str) -> HealthFixer | None:
        """Get a specific fixer by type.

        Args:
            fix_type: The fix type identifier

        Returns:
            HealthFixer instance or None if not found
        """
        return self._fixers.get(fix_type)

    def scan_all(self) -> dict[str, dict[str, Any]]:
        """Scan for all fixable issues.

        Returns:
            Dict mapping fix_type to scan results
        """
        results = {}
        for fix_type, fixer in self._fixers.items():
            results[fix_type] = fixer.scan()
        return results

    def dry_run_fix(self, fix_type: str) -> FixResult | None:
        """Preview a specific fix.

        Args:
            fix_type: Which fix to preview

        Returns:
            FixResult or None if fixer not found
        """
        fixer = self.get_fixer(fix_type)
        if not fixer:
            return None
        return fixer.dry_run()

    def apply_fix(self, fix_type: str, force: bool = False) -> FixResult | None:
        """Apply a specific fix.

        Args:
            fix_type: Which fix to apply
            force: If True, apply without confirmation

        Returns:
            FixResult or None if fixer not found
        """
        fixer = self.get_fixer(fix_type)
        if not fixer:
            return None

        # For review fixes, confirm first
        if not force and fixer.safety_level == FixSafety.REVIEW:
            dry_result = fixer.dry_run()
            if not fixer.confirm_apply(dry_result):
                return None

        return fixer.apply(force=force)
