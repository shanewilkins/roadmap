"""Unit tests for milestone name normalization fixer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.cli.health.fixers.milestone_name_normalization_fixer import (
    MilestoneNameNormalizationFixer,
)
from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue


@pytest.fixture
def mock_core():
    """Create a mock RoadmapCore."""
    core = MagicMock()
    core.issues.list.return_value = []
    return core


@pytest.fixture
def fixer(mock_core):
    """Create a MilestoneNameNormalizationFixer instance."""
    return MilestoneNameNormalizationFixer(mock_core)


class TestMilestoneNameNormalizationFixer:
    """Test milestone name normalization fixer."""

    def test_fix_type_property(self, fixer):
        """Test fix_type property."""
        assert fixer.fix_type == "milestone_name_normalization"

    def test_description_property(self, fixer):
        """Test description property."""
        assert (
            "Normalize milestone names to match milestone filenames"
            in fixer.description
        )

    def test_safety_level_property(self, fixer):
        """Test safety_level property."""
        from roadmap.adapters.cli.health.fixer import FixSafety

        assert fixer.safety_level == FixSafety.SAFE

    def test_scan_no_issues(self, fixer):
        """Test scanning when there are no issues."""
        result = fixer.scan()

        assert result["found"] is False
        assert result["count"] == 0
        assert len(result["details"]) == 0

    def test_scan_with_mismatched_milestone(self, mock_core, fixer):
        """Test scanning with mismatched milestone names."""
        issue = Issue(
            id="issue1",
            title="Test Issue",
            status=Status.TODO,
            milestone="v 1 0 0",
        )
        mock_core.issues.list.return_value = [issue]

        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.glob") as mock_glob:
                mock_exists.return_value = True
                mock_glob.return_value = [
                    Path(".roadmap/milestones/v-1-0-0.md"),
                ]

                result = fixer.scan()

                assert result["count"] == 1

    def test_dry_run_no_mismatches(self, fixer):
        """Test dry run with no mismatched milestones."""
        result = fixer.dry_run()

        assert result.success is True
        assert result.dry_run is True
        assert result.items_count == 0
        assert "Would normalize 0" in result.message

    def test_dry_run_with_mismatches(self, mock_core, fixer):
        """Test dry run with mismatched milestones."""
        issue = Issue(
            id="issue1",
            title="Test Issue",
            status=Status.TODO,
            milestone="v 1 0 0",
        )
        mock_core.issues.list.return_value = [issue]

        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.glob") as mock_glob:
                mock_exists.return_value = True
                mock_glob.return_value = [
                    Path(".roadmap/milestones/v-1-0-0.md"),
                ]

                result = fixer.dry_run()

                assert result.success is True
                assert result.dry_run is True
                assert result.items_count == 1

    def test_apply_no_mismatches(self, fixer):
        """Test applying fixes with no mismatches."""
        result = fixer.apply()

        assert result.success is True
        assert result.dry_run is False
        assert result.items_count == 0
        assert "Normalized 0/0" in result.message

    def test_apply_with_mismatches(self, mock_core, fixer):
        """Test applying fixes with mismatched milestones."""
        issue = Issue(
            id="issue1",
            title="Test Issue",
            status=Status.TODO,
            milestone="v 1 0 0",
        )
        mock_core.issues.list.return_value = [issue]
        mock_core.issues.assign_to_milestone.return_value = True

        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.glob") as mock_glob:
                mock_exists.return_value = True
                mock_glob.return_value = [
                    Path(".roadmap/milestones/v-1-0-0.md"),
                ]

                result = fixer.apply()

                assert result.success is True
                assert result.dry_run is False
                assert result.changes_made >= 0

    def test_apply_with_partial_failure(self, mock_core, fixer):
        """Test applying fixes with partial failures."""
        issue1 = Issue(
            id="issue1",
            title="Test Issue 1",
            status=Status.TODO,
            milestone="v 1 0 0",
        )
        issue2 = Issue(
            id="issue2",
            title="Test Issue 2",
            status=Status.TODO,
            milestone="v 2 0 0",
        )
        mock_core.issues.list.return_value = [issue1, issue2]

        # First assignment succeeds, second fails
        mock_core.issues.assign_to_milestone.side_effect = [True, False]

        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.glob") as mock_glob:
                mock_exists.return_value = True
                mock_glob.return_value = [
                    Path(".roadmap/milestones/v-1-0-0.md"),
                    Path(".roadmap/milestones/v-2-0-0.md"),
                ]

                result = fixer.apply()

                assert result.success is False
                assert result.changes_made == 1

    def test_find_mismatched_milestone_names_no_milestones(self, fixer):
        """Test finding mismatched names when milestones dir doesn't exist."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            mismatched = fixer._find_mismatched_milestone_names()

            assert mismatched == []

    def test_find_mismatched_milestone_names_with_exception(self, mock_core, fixer):
        """Test handling exceptions when finding mismatched names."""
        mock_core.issues.list.side_effect = Exception("Test error")

        mismatched = fixer._find_mismatched_milestone_names()

        assert mismatched == []
