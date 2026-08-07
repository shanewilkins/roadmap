"""Unit tests for milestone naming compliance fixer."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from roadmap.adapters.cli.health.fixers.milestone_naming_compliance_fixer import (
    MilestoneNamingComplianceFixer,
)


@pytest.fixture
def mock_core():
    """Create a mock RoadmapCore."""
    return MagicMock()


@pytest.fixture
def fixer(mock_core):
    """Create a MilestoneNamingComplianceFixer instance."""
    return MilestoneNamingComplianceFixer(mock_core)


class TestMilestoneNamingComplianceFixer:
    """Test milestone naming compliance fixer."""

    def test_fix_type_property(self, fixer):
        """Test fix_type property."""
        assert fixer.fix_type == "milestone_naming_compliance"

    def test_description_property(self, fixer):
        """Test description property."""
        assert "milestone naming" in fixer.description.lower()

    def test_safety_level_property(self, fixer):
        """Test safety_level property."""
        from roadmap.adapters.cli.health.fixer import FixSafety

        assert fixer.safety_level == FixSafety.SAFE

    def test_scan_no_non_compliant(self, fixer):
        """Test scanning with no non-compliant milestones."""
        with patch.object(fixer, "_find_non_compliant_milestones") as mock_find:
            mock_find.return_value = []

            result = fixer.scan()

            assert result["found"] is False
            assert result["count"] == 0

    def test_scan_with_non_compliant(self, fixer):
        """Test scanning with non-compliant milestones."""
        non_compliant = [
            {
                "id": "issue1",
                "title": "Test Issue",
                "file": "/path/to/issue.md",
                "current_milestone": "v.1.0.0",
                "safe_milestone": "v100",
            }
        ]

        with patch.object(fixer, "_find_non_compliant_milestones") as mock_find:
            mock_find.return_value = non_compliant

            result = fixer.scan()

            assert result["found"] is True
            assert result["count"] == 1

    def test_dry_run_no_non_compliant(self, fixer):
        """Test dry run with no non-compliant milestones."""
        with patch.object(fixer, "_find_non_compliant_milestones") as mock_find:
            mock_find.return_value = []

            result = fixer.dry_run()

            assert result.success is True
            assert result.dry_run is True
            assert result.items_count == 0

    def test_dry_run_with_non_compliant(self, fixer):
        """Test dry run with non-compliant milestones."""
        non_compliant = [
            {
                "id": "issue1",
                "title": "Test Issue",
                "file": "/path/to/issue.md",
                "current_milestone": "v.1.0.0",
                "safe_milestone": "v100",
            }
        ]

        with patch.object(fixer, "_find_non_compliant_milestones") as mock_find:
            mock_find.return_value = non_compliant

            result = fixer.dry_run()

            assert result.success is True
            assert result.dry_run is True
            assert result.items_count == 1
            assert "issue1" in str(result.affected_items)

    def test_apply_no_non_compliant(self, fixer):
        """Test applying fixes with no non-compliant milestones."""
        with patch.object(fixer, "_find_non_compliant_milestones") as mock_find:
            mock_find.return_value = []

            result = fixer.apply()

            assert result.success is True
            assert result.dry_run is False
            assert result.items_count == 0
            assert "No non-compliant" in result.message

    def test_apply_with_non_compliant(self, fixer):
        """Test applying fixes with non-compliant milestones."""
        non_compliant = [
            {
                "id": "issue1",
                "title": "Test Issue",
                "file": str(Path("/tmp/issue1.md")),
                "current_milestone": "v.1.0.0",
                "safe_milestone": "v100",
            }
        ]

        with patch.object(fixer, "_find_non_compliant_milestones") as mock_find:
            with patch(
                "builtins.open",
                mock_open(read_data="milestone: v.1.0.0\ntitle: Test Issue"),
            ):
                with patch("pathlib.Path.read_text") as mock_read:
                    mock_find.return_value = non_compliant
                    mock_read.return_value = "milestone: v.1.0.0\ntitle: Test Issue"

                    result = fixer.apply()

                    assert result.success is True
                    assert result.dry_run is False

    def test_apply_with_partial_failure(self, fixer):
        """Test applying fixes with partial failures."""
        non_compliant = [
            {
                "id": "issue1",
                "title": "Test Issue 1",
                "file": str(Path("/tmp/issue1.md")),
                "current_milestone": "v.1.0.0",
                "safe_milestone": "v100",
            },
            {
                "id": "issue2",
                "title": "Test Issue 2",
                "file": str(Path("/tmp/issue2.md")),
                "current_milestone": "v.2.0.0",
                "safe_milestone": "v200",
            },
        ]

        with patch.object(fixer, "_find_non_compliant_milestones") as mock_find:
            with patch("pathlib.Path.read_text") as mock_read:
                mock_find.return_value = non_compliant
                # First read succeeds, second raises
                mock_read.side_effect = [
                    "milestone: v.1.0.0\ntitle: Test Issue 1",
                    Exception("File error"),
                ]

                result = fixer.apply()

                assert result.success is False
                assert result.changes_made == 1

    def test_find_non_compliant_milestones_no_files(self, fixer):
        """Test finding non-compliant milestones with no files."""
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.glob") as mock_glob:
                mock_exists.return_value = False
                mock_glob.return_value = []

                result = fixer._find_non_compliant_milestones()

                assert result == []

    def test_find_non_compliant_milestones_with_exception(self, fixer):
        """Test finding non-compliant milestones with exception."""
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.glob") as mock_glob:
                mock_exists.return_value = True
                mock_glob.side_effect = Exception("Glob error")

                # The implementation doesn't catch exceptions, so they propagate
                with pytest.raises(Exception, match="Glob error"):
                    fixer._find_non_compliant_milestones()

    def test_force_parameter_ignored(self, fixer):
        """Test that force parameter is ignored for SAFE fixers."""
        with patch.object(fixer, "_find_non_compliant_milestones") as mock_find:
            mock_find.return_value = []

            result1 = fixer.apply(force=True)
            result2 = fixer.apply(force=False)

            # Both should behave the same
            assert result1.success == result2.success
