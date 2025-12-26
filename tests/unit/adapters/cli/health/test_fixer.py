"""Tests for health fix infrastructure and fixers."""


from roadmap.adapters.cli.health.fixer import (
    FixResult,
    FixSafety,
    HealthFixer,
    HealthFixOrchestrator,
)
from roadmap.adapters.cli.health.fixers.duplicate_issues_fixer import (
    DuplicateIssuesFixer,
)
from roadmap.adapters.cli.health.fixers.old_backups_fixer import OldBackupsFixer
from roadmap.adapters.cli.health.fixers.orphaned_issues_fixer import OrphanedIssuesFixer
from roadmap.infrastructure.core import RoadmapCore


class TestFixResult:
    """Tests for FixResult data class."""

    def test_fix_result_creation(self):
        """Test creating a FixResult."""
        result = FixResult(
            fix_type="test_fix",
            success=True,
            dry_run=True,
            message="Test message",
            affected_items=["item1", "item2"],
            changes_made=2,
        )

        assert result.fix_type == "test_fix"
        assert result.success is True
        assert result.dry_run is True
        assert result.message == "Test message"
        assert result.affected_items == ["item1", "item2"]
        assert result.changes_made == 2

    def test_fix_result_to_dict(self):
        """Test converting FixResult to dictionary."""
        result = FixResult(
            fix_type="test_fix",
            success=True,
            dry_run=False,
            message="Applied successfully",
            affected_items=["item1"],
            changes_made=1,
        )

        result_dict = result.to_dict()

        assert result_dict["fix_type"] == "test_fix"
        assert result_dict["success"] is True
        assert result_dict["dry_run"] is False
        assert result_dict["message"] == "Applied successfully"
        assert result_dict["affected_items"] == ["item1"]
        assert result_dict["changes_made"] == 1

    def test_fix_result_empty_affected_items(self):
        """Test FixResult with empty affected items."""
        result = FixResult(
            fix_type="test_fix",
            success=True,
            dry_run=True,
            message="No issues found",
            affected_items=[],
            changes_made=0,
        )

        assert result.affected_items == []
        assert result.changes_made == 0


class TestOldBackupsFixer:
    """Tests for OldBackupsFixer."""

    def test_safety_level_is_safe(self, core: RoadmapCore):
        """Test that OldBackupsFixer has SAFE safety level."""
        fixer = OldBackupsFixer(core)
        assert fixer.safety_level == FixSafety.SAFE

    def test_fix_type(self, core: RoadmapCore):
        """Test that OldBackupsFixer has correct fix_type."""
        fixer = OldBackupsFixer(core)
        assert fixer.fix_type == "old_backups"

    def test_description(self, core: RoadmapCore):
        """Test that OldBackupsFixer has a description."""
        fixer = OldBackupsFixer(core)
        assert len(fixer.description) > 0
        assert "backup" in fixer.description.lower()


class TestDuplicateIssuesFixer:
    """Tests for DuplicateIssuesFixer."""

    def test_safety_level_is_review(self, core: RoadmapCore):
        """Test that DuplicateIssuesFixer has REVIEW safety level."""
        fixer = DuplicateIssuesFixer(core)
        assert fixer.safety_level == FixSafety.REVIEW

    def test_fix_type(self, core: RoadmapCore):
        """Test that DuplicateIssuesFixer has correct fix_type."""
        fixer = DuplicateIssuesFixer(core)
        assert fixer.fix_type == "duplicate_issues"

    def test_description(self, core: RoadmapCore):
        """Test that DuplicateIssuesFixer has a description."""
        fixer = DuplicateIssuesFixer(core)
        assert len(fixer.description) > 0
        assert "duplicate" in fixer.description.lower()


class TestOrphanedIssuesFixer:
    """Tests for OrphanedIssuesFixer."""

    def test_safety_level_is_safe(self, core: RoadmapCore):
        """Test that OrphanedIssuesFixer has SAFE safety level."""
        fixer = OrphanedIssuesFixer(core)
        assert fixer.safety_level == FixSafety.SAFE

    def test_fix_type(self, core: RoadmapCore):
        """Test that OrphanedIssuesFixer has correct fix_type."""
        fixer = OrphanedIssuesFixer(core)
        assert fixer.fix_type == "orphaned_issues"

    def test_description(self, core: RoadmapCore):
        """Test that OrphanedIssuesFixer has a description."""
        fixer = OrphanedIssuesFixer(core)
        assert len(fixer.description) > 0
        assert (
            "unassigned" in fixer.description.lower()
            or "backlog" in fixer.description.lower()
        )


class TestHealthFixOrchestrator:
    """Tests for HealthFixOrchestrator."""

    def test_orchestrator_loads_fixers(self, core: RoadmapCore):
        """Test that orchestrator loads all available fixers."""
        orchestrator = HealthFixOrchestrator(core)
        fixers = orchestrator.get_fixers()

        assert len(fixers) > 0
        assert "old_backups" in fixers
        assert "duplicate_issues" in fixers
        assert "orphaned_issues" in fixers
        assert "folder_structure" in fixers
        assert "corrupted_comments" in fixers

    def test_orchestrator_get_fixer_by_type(self, core: RoadmapCore):
        """Test getting a specific fixer by type."""
        orchestrator = HealthFixOrchestrator(core)

        fixer = orchestrator.get_fixer("old_backups")
        assert fixer is not None
        assert isinstance(fixer, HealthFixer)
        assert fixer.fix_type == "old_backups"

    def test_orchestrator_get_invalid_fixer(self, core: RoadmapCore):
        """Test that invalid fixer type returns None."""
        orchestrator = HealthFixOrchestrator(core)

        fixer = orchestrator.get_fixer("nonexistent_fixer")
        assert fixer is None

    def test_orchestrator_scan_all(self, core: RoadmapCore):
        """Test scanning all fixers."""
        orchestrator = HealthFixOrchestrator(core)

        scan_results = orchestrator.scan_all()

        assert isinstance(scan_results, dict)
        # Results should have entries for all available fixers
        assert len(scan_results) >= 5

    def test_safety_levels_are_consistent(self, core: RoadmapCore):
        """Test that all fixers have defined safety levels."""
        orchestrator = HealthFixOrchestrator(core)
        fixers = orchestrator.get_fixers()

        for _, fixer in fixers.items():
            assert hasattr(fixer, "safety_level")
            assert fixer.safety_level in [FixSafety.SAFE, FixSafety.REVIEW]

    def test_safe_fixers_list(self, core: RoadmapCore):
        """Test identifying safe fixers."""
        orchestrator = HealthFixOrchestrator(core)
        fixers = orchestrator.get_fixers()

        safe_fixers = [
            fix_type
            for fix_type, fixer in fixers.items()
            if fixer.safety_level == FixSafety.SAFE
        ]

        # Should have at least: old_backups, orphaned_issues, folder_structure
        assert "old_backups" in safe_fixers
        assert "orphaned_issues" in safe_fixers
        assert "folder_structure" in safe_fixers

    def test_review_fixers_list(self, core: RoadmapCore):
        """Test identifying review-required fixers."""
        orchestrator = HealthFixOrchestrator(core)
        fixers = orchestrator.get_fixers()

        review_fixers = [
            fix_type
            for fix_type, fixer in fixers.items()
            if fixer.safety_level == FixSafety.REVIEW
        ]

        # Should have at least: duplicate_issues, corrupted_comments
        assert "duplicate_issues" in review_fixers
        assert "corrupted_comments" in review_fixers


class TestFixerInterface:
    """Tests for standard fixer interface."""

    def test_all_fixers_implement_interface(self, core: RoadmapCore):
        """Test that all fixers implement the required interface."""
        orchestrator = HealthFixOrchestrator(core)
        fixers = orchestrator.get_fixers()

        for fix_type, fixer in fixers.items():
            # Check required methods
            assert hasattr(fixer, "scan"), f"{fix_type} missing scan() method"
            assert hasattr(fixer, "dry_run"), f"{fix_type} missing dry_run() method"
            assert hasattr(fixer, "apply"), f"{fix_type} missing apply() method"

            # Check required properties
            assert hasattr(fixer, "fix_type"), f"{fix_type} missing fix_type property"
            assert hasattr(
                fixer, "safety_level"
            ), f"{fix_type} missing safety_level property"
            assert hasattr(
                fixer, "description"
            ), f"{fix_type} missing description property"

            # Verify they are callable
            assert callable(fixer.scan), f"{fix_type}.scan is not callable"
            assert callable(fixer.dry_run), f"{fix_type}.dry_run is not callable"
            assert callable(fixer.apply), f"{fix_type}.apply is not callable"
