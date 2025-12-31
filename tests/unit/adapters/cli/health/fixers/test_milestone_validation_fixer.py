"""Unit tests for milestone validation fixer."""

from unittest.mock import patch

from roadmap.adapters.cli.health.fixers.milestone_validation_fixer import (
    MilestoneValidationFixer,
)


class TestMilestoneValidationFixer:
    """Test milestone validation fixer."""

    def test_fix_type_property(self, mock_core):
        """Test fix_type property."""
        fixer = MilestoneValidationFixer(mock_core)

        assert fixer.fix_type == "milestone_validation"

    def test_scan_no_issues(self, mock_core):
        """Test scanning with no validation issues."""
        fixer = MilestoneValidationFixer(mock_core)

        with patch.object(fixer, "_find_invalid_milestones") as mock_find:
            mock_find.return_value = []

            result = fixer.scan()

            assert result["found"] is False
            assert result["count"] == 0

    def test_scan_with_validation_issues(self, mock_core):
        """Test scanning with validation issues."""
        fixer = MilestoneValidationFixer(mock_core)
        issues = [{"id": "issue1", "title": "Test Issue", "milestone": "invalid"}]

        with patch.object(fixer, "_find_invalid_milestones") as mock_find:
            mock_find.return_value = issues

            result = fixer.scan()

            assert result["found"] is True
            assert result["count"] == 1

    def test_dry_run(self, mock_core):
        """Test dry run."""
        fixer = MilestoneValidationFixer(mock_core)

        with patch.object(fixer, "_find_invalid_milestones") as mock_find:
            mock_find.return_value = []

            result = fixer.dry_run()

            assert result.dry_run is True

    def test_apply(self, mock_core):
        """Test applying fixes."""
        fixer = MilestoneValidationFixer(mock_core)

        with patch.object(fixer, "_find_invalid_milestones") as mock_find:
            mock_find.return_value = []

            result = fixer.apply()

            assert result.dry_run is False
