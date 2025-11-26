"""Tests for core edge cases and error handling."""

import os
from unittest.mock import patch

import pytest

from roadmap.application.core import RoadmapCore
from roadmap.domain import Priority, Status


@pytest.fixture
def initialized_core(temp_dir):
    """Create an initialized roadmap core."""
    core = RoadmapCore()
    core.initialize()
    return core


class TestCoreEdgeCases:
    """Test edge cases and error handling in RoadmapCore."""

    def test_list_issues_with_malformed_files(self, initialized_core):
        """Test listing issues when some files are malformed."""
        # Create a valid issue
        initialized_core.create_issue("Valid Issue")

        # Create a malformed file in the issues directory
        malformed_file = initialized_core.issues_dir / "malformed.md"
        malformed_file.write_text(
            "This is not a valid issue file\nwithout proper frontmatter"
        )

        # List issues should skip the malformed file and return only valid ones
        issues = initialized_core.list_issues()
        assert len(issues) == 1
        assert issues[0].title == "Valid Issue"

    def test_list_issues_with_empty_files(self, initialized_core):
        """Test listing issues when some files are empty."""
        # Create a valid issue
        initialized_core.create_issue("Valid Issue")

        # Create an empty file in the issues directory
        empty_file = initialized_core.issues_dir / "empty.md"
        empty_file.write_text("")

        # List issues should skip the empty file
        issues = initialized_core.list_issues()
        assert len(issues) == 1
        assert issues[0].title == "Valid Issue"

    def test_list_issues_with_corrupted_frontmatter(self, initialized_core):
        """Test listing issues with corrupted YAML frontmatter."""
        # Create a valid issue
        initialized_core.create_issue("Valid Issue")

        # Create a file with corrupted frontmatter
        corrupted_file = initialized_core.issues_dir / "corrupted.md"
        corrupted_file.write_text(
            """---
title: Corrupted Issue
priority: [invalid yaml structure
status: todo
---

This issue has corrupted YAML frontmatter.
"""
        )

        # List issues should skip the corrupted file
        issues = initialized_core.list_issues()
        assert len(issues) == 1
        assert issues[0].title == "Valid Issue"

    def test_list_issues_with_missing_required_fields(self, initialized_core):
        """Test listing issues with missing required fields."""
        # Create a valid issue
        initialized_core.create_issue("Valid Issue")

        # Create a file with missing required fields
        missing_fields_file = initialized_core.issues_dir / "missing-fields.md"
        missing_fields_file.write_text(
            """---
priority: high
status: todo
---

This issue is missing the title field.
"""
        )

        # List issues should skip the file with missing fields
        issues = initialized_core.list_issues()
        assert len(issues) == 1
        assert issues[0].title == "Valid Issue"

    def test_list_issues_with_complex_filtering(self, initialized_core):
        """Test complex filtering scenarios."""
        # Create issues with various attributes
        issue1 = initialized_core.create_issue("Issue 1", priority=Priority.HIGH)
        issue2 = initialized_core.create_issue("Issue 2", priority=Priority.LOW)
        initialized_core.create_issue("Issue 3", priority=Priority.HIGH)

        # Update issue statuses
        initialized_core.update_issue(issue1.id, status=Status.IN_PROGRESS)
        initialized_core.update_issue(issue2.id, status=Status.CLOSED)

        # Create a milestone and assign issues
        initialized_core.create_milestone("Test Milestone", "Test description")
        initialized_core.move_issue_to_milestone(issue1.id, "Test Milestone")

        # Test filtering by multiple criteria
        # High priority, in-progress issues
        issues = initialized_core.list_issues(
            priority=Priority.HIGH, status=Status.IN_PROGRESS
        )
        assert len(issues) == 1
        assert issues[0].id == issue1.id

        # Issues in specific milestone with high priority
        issues = initialized_core.list_issues(
            milestone="Test Milestone", priority=Priority.HIGH
        )
        assert len(issues) == 1
        assert issues[0].id == issue1.id

        # Issues with no milestone (backlog)
        issues = initialized_core.list_issues(milestone=None)
        backlog_issues = [i for i in issues if i.milestone is None or i.milestone == ""]
        assert len(backlog_issues) >= 2  # issue2 and issue3

    def test_get_issue_nonexistent(self, initialized_core):
        """Test getting a non-existent issue."""
        issue = initialized_core.get_issue("nonexistent-id")
        assert issue is None

    def test_update_issue_nonexistent(self, initialized_core):
        """Test updating a non-existent issue."""
        result = initialized_core.update_issue("nonexistent-id", title="New Title")
        assert result is None

    def test_delete_issue_nonexistent(self, initialized_core):
        """Test deleting a non-existent issue."""
        result = initialized_core.delete_issue("nonexistent-id")
        assert result is False

    def test_move_issue_to_nonexistent_milestone(self, initialized_core):
        """Test moving issue to non-existent milestone."""
        issue = initialized_core.create_issue("Test Issue")

        result = initialized_core.move_issue_to_milestone(
            issue.id, "Nonexistent Milestone"
        )
        assert result is False

    def test_move_nonexistent_issue_to_milestone(self, initialized_core):
        """Test moving non-existent issue to milestone."""
        initialized_core.create_milestone("Test Milestone", "Test description")

        result = initialized_core.move_issue_to_milestone(
            "nonexistent-id", "Test Milestone"
        )
        assert result is False

    def test_list_issues_with_assignee_edge_cases(self, initialized_core):
        """Test assignee filtering edge cases."""
        # Create issues with various assignee states
        issue1 = initialized_core.create_issue("Issue 1")
        issue2 = initialized_core.create_issue("Issue 2")
        initialized_core.create_issue("Issue 3")

        # Set different assignee states
        initialized_core.update_issue(issue1.id, assignee="alice")
        initialized_core.update_issue(issue2.id, assignee="")  # Empty string
        # issue3 stays with assignee=None

        # Test filtering by assignee
        issues = initialized_core.list_issues(assignee="alice")
        assert len(issues) == 1
        assert issues[0].id == issue1.id

        # Test that when assignee="" (empty string), the filter is not applied
        # because empty string is falsy, so all issues are returned
        issues = initialized_core.list_issues(assignee="")
        assert len(issues) == 3  # All issues returned

        # Test that when no assignee filter is provided, all issues are returned
        all_issues = initialized_core.list_issues()
        assert len(all_issues) == 3

    def test_initialize_already_initialized_directory(self, temp_dir):
        """Test initializing an already initialized directory."""
        core = RoadmapCore()

        # First initialization should succeed
        core.initialize()  # This doesn't return a value
        assert core.is_initialized()

        # Second initialization should raise an error
        with pytest.raises(ValueError, match="Roadmap already initialized"):
            core.initialize()

    def test_operations_on_uninitialized_roadmap(self, temp_dir):
        """Test operations on uninitialized roadmap raise appropriate errors."""
        core = RoadmapCore()

        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.create_issue("Test Issue")

        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.list_issues()

        with pytest.raises(ValueError, match="Roadmap not initialized"):
            core.create_milestone("Test Milestone", "Description")

    @patch("roadmap.infrastructure.persistence.parser.IssueParser.parse_issue_file")
    def test_list_issues_with_parser_exception(self, mock_parse, initialized_core):
        """Test list_issues handles parser exceptions gracefully."""
        # Create a valid issue first
        issue = initialized_core.create_issue("Valid Issue")

        # Mock the parser to raise an exception for some files
        def side_effect(file_path):
            if "valid" in str(file_path).lower():
                # Return the actual issue for valid files
                return issue
            else:
                # Raise exception for problematic files
                raise Exception("Parser error")

        mock_parse.side_effect = side_effect

        # Create a problematic file
        problem_file = initialized_core.issues_dir / "problem.md"
        problem_file.write_text("Some content")

        # List issues should handle the exception and continue
        issues = initialized_core.list_issues()
        assert len(issues) == 1  # Only the valid issue should be returned

    def test_file_operations_with_permission_errors(self, initialized_core):
        """Test handling of file permission errors."""
        import stat

        # Create an issue
        issue = initialized_core.create_issue("Test Issue")
        issue_file = initialized_core.issues_dir / issue.filename

        try:
            # Make the file read-only
            os.chmod(issue_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

            # Try to update the issue (should handle permission error gracefully)
            # Note: This might not always fail on all systems, so we just ensure it doesn't crash
            try:
                initialized_core.update_issue(issue.id, title="New Title")
                # If it succeeds, that's fine too
            except PermissionError:
                # If it fails with permission error, that's expected
                pass

        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(
                    issue_file,
                    stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,
                )
            except:
                pass
