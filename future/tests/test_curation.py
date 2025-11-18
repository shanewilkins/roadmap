"""Tests for roadmap curation functionality."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.application.services import RoadmapCore
from roadmap.curation import CurationReport, OrphanageType, OrphanedItem, RoadmapCurator
from roadmap.domain import (
    IssueType,
    Priority,
)


@pytest.fixture
def temp_roadmap():
    """Create a temporary roadmap for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        core = RoadmapCore(temp_path)

        # Initialize roadmap in temp directory
        core.initialize()

        yield core


@pytest.fixture
def curator(temp_roadmap):
    """Create a curator instance with test roadmap."""
    return RoadmapCurator(temp_roadmap)


@pytest.fixture
def sample_issues(temp_roadmap):
    """Create sample issues for testing."""
    core = temp_roadmap

    # Create milestones
    milestone1 = core.create_milestone("Sprint 1", "First sprint")
    milestone2 = core.create_milestone("Sprint 2", "Second sprint")

    # Create issues - some orphaned, some assigned
    issue1 = core.create_issue(
        "Assigned Issue", priority=Priority.HIGH
    )  # Will be assigned
    issue2 = core.create_issue(
        "Orphaned High Priority", priority=Priority.HIGH
    )  # Orphaned
    issue3 = core.create_issue(
        "Orphaned Bug", priority=Priority.MEDIUM, issue_type=IssueType.BUG
    )  # Orphaned
    issue4 = core.create_issue("Old Orphan", priority=Priority.LOW)  # Old orphan
    issue5 = core.create_issue(
        "Invalid Milestone Ref", priority=Priority.MEDIUM
    )  # Invalid milestone

    # Assign some issues
    core.assign_issue_to_milestone(issue1.id, "Sprint 1")

    # Simulate old orphan by modifying created date
    old_date = datetime.now() - timedelta(days=35)
    core.update_issue(issue4.id, created=old_date)

    # Simulate invalid milestone reference
    core.update_issue(issue5.id, milestone="NonExistent")

    return {
        "issues": [issue1, issue2, issue3, issue4, issue5],
        "milestones": [milestone1, milestone2],
        "orphaned_count": 3,  # issue2, issue3, issue4
        "invalid_ref_count": 1,  # issue5
        "assigned_count": 1,  # issue1
    }


class TestRoadmapCurator:
    """Test roadmap curation functionality."""

    def test_curator_initialization(self, temp_roadmap):
        """Test curator can be initialized with a core instance."""
        curator = RoadmapCurator(temp_roadmap)
        assert curator.core == temp_roadmap
        assert curator.orphan_threshold_days == 30

    def test_analyze_orphaned_items_empty_roadmap(self, curator):
        """Test analysis on empty roadmap."""
        report = curator.analyze_orphaned_items()

        assert isinstance(report, CurationReport)
        assert report.total_issues == 0
        assert report.total_milestones == 0
        assert len(report.orphaned_issues) == 0
        assert len(report.orphaned_milestones) == 0
        assert report.backlog_size == 0

    def test_analyze_orphaned_items_with_data(self, curator, sample_issues):
        """Test analysis with sample data."""
        report = curator.analyze_orphaned_items(include_backlog=True)

        assert report.total_issues == 5
        assert report.total_milestones == 2
        assert len(report.orphaned_issues) >= 3  # At least 3 orphaned issues
        assert report.backlog_size >= 3  # Issues without milestones

    def test_detect_orphaned_issues_backlog(self, curator, sample_issues):
        """Test detection of backlog orphaned issues."""
        all_issues = curator.core.list_issues()
        all_milestones = curator.core.list_milestones()

        orphaned = curator._detect_orphaned_issues(
            all_issues,
            all_milestones,
            include_backlog=True,
            min_age_days=0,
            max_age_days=None,
        )

        # Should find orphaned issues (not assigned to milestones)
        assert len(orphaned) >= 3

        # Check that orphaned items have correct properties
        for item in orphaned:
            assert item.item_type == "issue"
            assert item.orphanage_type in [
                OrphanageType.UNASSIGNED_ISSUE,
                OrphanageType.OLD_ORPHAN,
                OrphanageType.INVALID_MILESTONE,
            ]
            assert len(item.recommendations) > 0

    def test_detect_invalid_milestone_references(self, curator, sample_issues):
        """Test detection of issues with invalid milestone references."""
        all_issues = curator.core.list_issues()
        all_milestones = curator.core.list_milestones()

        invalid = curator._detect_invalid_milestone_references(
            all_issues, all_milestones, min_age_days=0, max_age_days=None
        )

        # Should find at least one issue with invalid milestone reference
        assert len(invalid) >= 1

        for item in invalid:
            assert item.item_type == "issue"
            assert item.orphanage_type == OrphanageType.INVALID_MILESTONE
            assert "non-existent milestone" in item.recommendations[0].lower()

    def test_detect_empty_milestones(self, curator, sample_issues):
        """Test detection of milestones with no issues."""
        all_issues = curator.core.list_issues()
        all_milestones = curator.core.list_milestones()

        empty = curator._detect_empty_milestones(
            all_milestones, all_issues, min_age_days=0, max_age_days=None
        )

        # Should find at least one empty milestone (Sprint 2 has no issues)
        assert len(empty) >= 1

        for item in empty:
            assert item.item_type == "milestone"
            assert item.orphanage_type == OrphanageType.ORPHANED_MILESTONE
            assert "empty" in item.orphanage_reasons

    def test_detect_unassigned_milestones(self, curator, sample_issues):
        """Test detection of milestones not assigned to any roadmap."""
        all_milestones = curator.core.list_milestones()

        unassigned = curator._detect_unassigned_milestones(
            all_milestones, min_age_days=0, max_age_days=None
        )

        # Since our test setup doesn't create roadmaps by default,
        # all milestones should be unassigned
        assert len(unassigned) == len(all_milestones)

        for item in unassigned:
            assert item.item_type == "milestone"
            assert item.orphanage_type == OrphanageType.ORPHANED_MILESTONE
            assert "unassigned" in item.orphanage_reasons
            assert "not assigned to any roadmap" in item.recommendations[0]

    def test_get_roadmap_assigned_milestones(self, curator):
        """Test getting milestones assigned to roadmaps."""
        # Test with no roadmaps directory
        assigned = curator._get_roadmap_assigned_milestones()
        assert isinstance(assigned, set)
        assert len(assigned) == 0

        # Create a test roadmap with milestones
        roadmaps_dir = curator.core.roadmap_dir / "roadmaps"
        roadmaps_dir.mkdir(exist_ok=True)

        roadmap_content = """---
id: test-roadmap
name: Test Roadmap
status: active
milestones:
  - milestone_1
  - v0.5.0
---

# Test Roadmap
"""
        roadmap_file = roadmaps_dir / "test-roadmap.md"
        roadmap_file.write_text(roadmap_content)

        assigned = curator._get_roadmap_assigned_milestones()
        assert "milestone_1" in assigned
        assert "v0.5.0" in assigned
        assert len(assigned) == 2

    def test_age_filtering(self, curator, sample_issues):
        """Test age-based filtering of orphaned items."""
        # Test minimum age filtering
        report_recent = curator.analyze_orphaned_items(
            include_backlog=True, min_age_days=30
        )

        # Should find fewer items when filtering for older items only
        report_all = curator.analyze_orphaned_items(include_backlog=True)

        assert len(report_recent.orphaned_issues) <= len(report_all.orphaned_issues)

    def test_bulk_assign_to_milestone(self, curator, sample_issues):
        """Test bulk assignment of issues to milestone."""
        # Get some orphaned issues
        orphaned_issues = curator.core.get_backlog_issues()
        issue_ids = [issue.id for issue in orphaned_issues[:2]]

        successful, failed = curator.bulk_assign_to_milestone(issue_ids, "Sprint 1")

        assert len(successful) == 2
        assert len(failed) == 0

        # Verify issues were actually assigned
        for issue_id in successful:
            issue = curator.core.get_issue(issue_id)
            assert issue.milestone == "Sprint 1"

    def test_bulk_move_to_backlog(self, curator, sample_issues):
        """Test bulk move of issues to backlog."""
        # First assign some issues to a milestone
        orphaned_issues = curator.core.get_backlog_issues()
        issue_ids = [issue.id for issue in orphaned_issues[:2]]
        curator.bulk_assign_to_milestone(issue_ids, "Sprint 1")

        # Now move them back to backlog
        successful, failed = curator.bulk_move_to_backlog(issue_ids)

        assert len(successful) == 2
        assert len(failed) == 0

        # Verify issues are now in backlog
        for issue_id in successful:
            issue = curator.core.get_issue(issue_id)
            assert issue.is_backlog

    def test_suggest_milestone_assignments(self, curator, sample_issues):
        """Test intelligent milestone assignment suggestions."""
        report = curator.analyze_orphaned_items(include_backlog=True)
        suggestions = curator.suggest_milestone_assignments(report.orphaned_issues)

        assert isinstance(suggestions, dict)

        # Should have suggestions for open milestones
        if suggestions:
            for milestone_name, issue_ids in suggestions.items():
                assert isinstance(issue_ids, list)
                assert len(issue_ids) > 0

                # Verify milestone exists and is open
                milestone = curator.core.get_milestone(milestone_name)
                assert milestone is not None

    def test_priority_based_recommendations(self, curator, sample_issues):
        """Test that high priority issues get appropriate recommendations."""
        # Create a high priority issue
        high_priority_issue = curator.core.create_issue(
            "Critical Bug", priority=Priority.CRITICAL, issue_type=IssueType.BUG
        )

        milestones = curator.core.list_milestones()
        recommendations = curator._get_issue_assignment_recommendations(
            high_priority_issue, milestones
        )

        # High priority issues should get next milestone recommendation
        assert any("next milestone" in rec.lower() for rec in recommendations)

    def test_export_json_report(self, curator, sample_issues, tmp_path):
        """Test JSON export functionality."""
        report = curator.analyze_orphaned_items(include_backlog=True)
        output_path = tmp_path / "test_report.json"

        curator.export_curation_report(report, output_path, "json")

        assert output_path.exists()

        # Verify JSON content
        import json

        with open(output_path) as f:
            data = json.load(f)

        assert "total_issues" in data
        assert "total_milestones" in data
        assert "orphaned_issues" in data
        assert "recommendations" in data

    def test_export_csv_report(self, curator, sample_issues, tmp_path):
        """Test CSV export functionality."""
        report = curator.analyze_orphaned_items(include_backlog=True)
        output_path = tmp_path / "test_report.csv"

        curator.export_curation_report(report, output_path, "csv")

        assert output_path.exists()

        # Verify CSV content
        import csv

        with open(output_path) as f:
            reader = csv.reader(f)
            headers = next(reader)

        expected_headers = [
            "Type",
            "ID",
            "Title",
            "Orphanage Type",
            "Priority",
            "Status",
            "Assignee",
            "Milestone",
            "Orphaned Days",
            "Recommendations",
        ]
        assert headers == expected_headers

    def test_export_markdown_report(self, curator, sample_issues, tmp_path):
        """Test Markdown export functionality."""
        report = curator.analyze_orphaned_items(include_backlog=True)
        output_path = tmp_path / "test_report.md"

        curator.export_curation_report(report, output_path, "markdown")

        assert output_path.exists()

        # Verify Markdown content
        content = output_path.read_text()
        assert "# Roadmap Curation Report" in content
        assert "## Summary" in content
        assert "## Recommendations" in content

    def test_curation_report_properties(self, curator, sample_issues):
        """Test curation report contains expected properties."""
        report = curator.analyze_orphaned_items(include_backlog=True)

        # Test basic properties
        assert hasattr(report, "total_issues")
        assert hasattr(report, "total_milestones")
        assert hasattr(report, "orphaned_issues")
        assert hasattr(report, "orphaned_milestones")
        assert hasattr(report, "backlog_size")
        assert hasattr(report, "recommendations")
        assert hasattr(report, "generated_at")
        assert hasattr(report, "summary_stats")

        # Test summary stats
        stats = report.summary_stats
        assert "total_orphaned" in stats
        assert "orphan_percentage" in stats
        assert "average_orphan_age_days" in stats
        assert "critical_orphans" in stats

    def test_orphaned_item_dataclass(self):
        """Test OrphanedItem dataclass functionality."""
        item = OrphanedItem(
            item_type="issue",
            item_id="test123",
            title="Test Issue",
            orphanage_type=OrphanageType.UNASSIGNED_ISSUE,
            created=datetime.now(),
            updated=datetime.now(),
            priority=Priority.HIGH,
            orphaned_days=5,
        )

        assert item.item_type == "issue"
        assert item.item_id == "test123"
        assert item.orphanage_type == OrphanageType.UNASSIGNED_ISSUE
        assert item.recommendations == []  # Default empty list

    def test_error_handling_uninitialized_roadmap(self, tmp_path):
        """Test error handling for uninitialized roadmap."""
        core = RoadmapCore(tmp_path)  # Not initialized
        curator = RoadmapCurator(core)

        with pytest.raises(ValueError, match="Roadmap not initialized"):
            curator.analyze_orphaned_items()


class TestCurationCLI:
    """Test curation CLI commands."""

    @patch("roadmap.cli.RoadmapCore")
    @patch("roadmap.curation.RoadmapCurator")
    def test_curate_orphaned_command(self, mock_curator_class, mock_core_class):
        """Test the curate orphaned CLI command."""
        from click.testing import CliRunner

        from roadmap.presentation.cli import curate_orphaned

        # Mock the core
        mock_core = MagicMock()
        mock_core.is_initialized.return_value = True
        mock_core_class.return_value = mock_core

        # Mock the curator
        mock_curator = MagicMock()
        mock_curator_class.return_value = mock_curator

        # Create a mock report
        mock_report = MagicMock()
        mock_report.total_issues = 10
        mock_report.total_milestones = 3
        mock_report.backlog_size = 5
        mock_report.orphaned_issues = []
        mock_report.orphaned_milestones = []
        mock_report.empty_milestones = []
        mock_report.unassigned_milestones = []
        mock_report.recommendations = ["Test recommendation"]
        mock_report.generated_at = datetime.now()
        mock_report.summary_stats = {
            "total_orphaned": 2,
            "orphan_percentage": 10.0,
            "critical_orphans": 0,
            "average_orphan_age_days": 5.0,
        }

        mock_curator.analyze_orphaned_items.return_value = mock_report

        runner = CliRunner()
        result = runner.invoke(curate_orphaned, [])

        assert result.exit_code == 0
        # Check that the curator was called and some analysis output is shown
        mock_curator.analyze_orphaned_items.assert_called_once()
        assert (
            "Found 0 orphaned issues" in result.output
            or "Found 0 orphaned milestones" in result.output
        )

    @patch("roadmap.cli.RoadmapCore")
    def test_curate_uninitialized_roadmap(self, mock_core_class):
        """Test curation commands with uninitialized roadmap."""
        from click.testing import CliRunner

        from roadmap.presentation.cli import curate_orphaned

        mock_core = MagicMock()
        mock_core.is_initialized.return_value = False
        mock_core_class.return_value = mock_core

        runner = CliRunner()
        result = runner.invoke(curate_orphaned, [])

        assert result.exit_code == 0
        assert "Roadmap not initialized" in result.output

    def test_curation_workflow_integration(self, temp_roadmap):
        """Test full curation workflow integration."""
        curator = RoadmapCurator(temp_roadmap)

        # Create test data
        temp_roadmap.create_milestone("Test Milestone", "Test description")
        temp_roadmap.create_issue("Orphaned Issue 1", priority=Priority.HIGH)
        temp_roadmap.create_issue("Orphaned Issue 2", priority=Priority.MEDIUM)

        # Analyze orphaned items
        report = curator.analyze_orphaned_items(include_backlog=True)
        assert len(report.orphaned_issues) >= 2

        # Test bulk assignment
        orphaned_ids = [item.item_id for item in report.orphaned_issues]
        successful, failed = curator.bulk_assign_to_milestone(
            orphaned_ids, "Test Milestone"
        )

        assert len(successful) == len(orphaned_ids)
        assert len(failed) == 0

        # Verify assignment worked
        updated_report = curator.analyze_orphaned_items(include_backlog=True)
        assert len(updated_report.orphaned_issues) < len(report.orphaned_issues)


@pytest.mark.integration
class TestCurationIntegration:
    """Integration tests for curation functionality."""

    def test_real_world_scenario(self, temp_roadmap):
        """Test curation in a realistic roadmap scenario."""
        core = temp_roadmap
        curator = RoadmapCurator(core)

        # Create a realistic roadmap structure
        [
            core.create_milestone(
                "Sprint 1",
                "Current sprint",
                due_date=datetime.now() + timedelta(days=7),
            ),
            core.create_milestone(
                "Sprint 2", "Next sprint", due_date=datetime.now() + timedelta(days=14)
            ),
            core.create_milestone(
                "Backlog Planning",
                "Future work",
                due_date=datetime.now() + timedelta(days=30),
            ),
        ]

        # Create various types of issues
        issues = [
            core.create_issue(
                "Critical Bug Fix", priority=Priority.CRITICAL, issue_type=IssueType.BUG
            ),
            core.create_issue(
                "High Priority Feature",
                priority=Priority.HIGH,
                issue_type=IssueType.FEATURE,
            ),
            core.create_issue(
                "Medium Priority Task",
                priority=Priority.MEDIUM,
                issue_type=IssueType.OTHER,
            ),
            core.create_issue(
                "Low Priority Enhancement",
                priority=Priority.LOW,
                issue_type=IssueType.OTHER,
            ),
            core.create_issue(
                "Documentation Update",
                priority=Priority.MEDIUM,
                issue_type=IssueType.OTHER,
            ),
        ]

        # Assign only some issues to milestones
        core.assign_issue_to_milestone(
            issues[0].id, "Sprint 1"
        )  # Critical bug to current sprint

        # Run curation analysis
        report = curator.analyze_orphaned_items(include_backlog=True)

        # Verify realistic results
        assert report.total_issues == 5
        assert report.total_milestones == 3
        assert len(report.orphaned_issues) == 4  # 4 unassigned issues
        assert report.backlog_size == 4

        # Test smart assignment suggestions
        suggestions = curator.suggest_milestone_assignments(report.orphaned_issues)

        # High priority issues should be suggested for Sprint 1
        suggestions.get("Sprint 1", [])
        issues[1].id  # High priority feature

        # Apply smart suggestions
        for milestone_name, issue_ids in suggestions.items():
            successful, failed = curator.bulk_assign_to_milestone(
                issue_ids, milestone_name
            )
            assert len(failed) == 0

        # Verify final state
        final_report = curator.analyze_orphaned_items(include_backlog=True)
        assert len(final_report.orphaned_issues) == 0  # All issues should be assigned
        assert final_report.backlog_size == 0


if __name__ == "__main__":
    pytest.main([__file__])
