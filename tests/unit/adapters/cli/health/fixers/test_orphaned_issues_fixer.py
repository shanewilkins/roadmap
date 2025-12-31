"""Unit tests for orphaned issues fixer."""

from unittest.mock import patch

from roadmap.adapters.cli.health.fixers.orphaned_issues_fixer import OrphanedIssuesFixer


class TestOrphanedIssuesFixer:
    """Test orphaned issues fixer."""

    def test_fix_type_property(self, mock_core):
        """Test fix_type property."""
        fixer = OrphanedIssuesFixer(mock_core)

        assert fixer.fix_type == "orphaned_issues"

    def test_scan_no_orphaned_issues(self, mock_core):
        """Test scanning with no orphaned issues."""
        fixer = OrphanedIssuesFixer(mock_core)

        with patch.object(fixer, "_find_orphaned_issues") as mock_find:
            mock_find.return_value = []

            result = fixer.scan()

            assert result["found"] is False
            assert result["count"] == 0

    def test_scan_with_orphaned_issues(self, mock_core):
        """Test scanning with orphaned issues."""
        fixer = OrphanedIssuesFixer(mock_core)
        orphaned = [
            {
                "id": "issue1",
                "title": "Orphaned Issue",
                "milestone": "nonexistent",
            }
        ]

        with patch.object(fixer, "_find_orphaned_issues") as mock_find:
            mock_find.return_value = orphaned

            result = fixer.scan()

            assert result["found"] is True
            assert result["count"] == 1

    def test_dry_run_no_orphaned(self, mock_core):
        """Test dry run with no orphaned issues."""
        fixer = OrphanedIssuesFixer(mock_core)

        with patch.object(fixer, "_find_orphaned_issues") as mock_find:
            mock_find.return_value = []

            result = fixer.dry_run()

            assert result.success is True
            assert result.dry_run is True
            assert result.items_count == 0

    def test_dry_run_with_orphaned(self, mock_core):
        """Test dry run with orphaned issues."""
        fixer = OrphanedIssuesFixer(mock_core)
        orphaned = [
            {"id": "issue1", "title": "Orphaned Issue", "milestone": "nonexistent"}
        ]

        with patch.object(fixer, "_find_orphaned_issues") as mock_find:
            mock_find.return_value = orphaned

            result = fixer.dry_run()

            assert result.success is True
            assert result.dry_run is True
            assert result.items_count == 1

    def test_apply_no_orphaned(self, mock_core):
        """Test applying fixes with no orphaned issues."""
        fixer = OrphanedIssuesFixer(mock_core)

        with patch.object(fixer, "_find_orphaned_issues") as mock_find:
            mock_find.return_value = []

            result = fixer.apply()

            assert result.success is True
            assert result.dry_run is False

    def test_apply_with_orphaned(self, mock_core):
        """Test applying fixes with orphaned issues."""
        fixer = OrphanedIssuesFixer(mock_core)
        orphaned = [
            {"id": "issue1", "title": "Orphaned Issue", "milestone": "nonexistent"}
        ]

        with patch.object(fixer, "_find_orphaned_issues") as mock_find:
            mock_find.return_value = orphaned
            fixer.core.issues.assign_to_milestone.return_value = True

            result = fixer.apply()

            assert result.success is True
            assert result.dry_run is False

    def test_find_orphaned_issues_with_exception(self, mock_core):
        """Test handling exceptions when finding orphaned issues."""
        fixer = OrphanedIssuesFixer(mock_core)
        fixer.core.issues.list.side_effect = Exception("Test error")

        orphaned = fixer._find_orphaned_issues()

        assert orphaned == []
