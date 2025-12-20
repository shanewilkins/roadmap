"""Tests for EntityHealthScanner service."""

from datetime import datetime

from roadmap.common.constants import Status
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue
from roadmap.core.services.entity_health_scanner import (
    EntityHealthScanner,
    EntityType,
)


class TestEntityHealthScanner:
    """Test suite for EntityHealthScanner."""

    def test_scan_healthy_issue(self):
        """Test scanning a fully healthy issue."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="This is a detailed description",
            status=Status.TODO,
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        assert report.entity_id == "issue-1"
        assert report.entity_type == EntityType.ISSUE
        assert report.is_healthy
        assert report.issue_count == 0

    def test_scan_issue_missing_description(self):
        """Test detection of missing issue description."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="",  # Empty content
            status=Status.TODO,
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        # Missing description is info level, so is_healthy is still true
        # But we should detect the issue
        assert report.issue_count == 1
        assert any(i.code == "missing_description" for i in report.issues)

    def test_scan_issue_with_invalid_comments(self):
        """Test detection of issues in comments."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.TODO,
            comments=[
                Comment(
                    id=1,
                    issue_id="issue-1",
                    author="",  # Empty author
                    body="Valid comment",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            ],
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        # Missing comment author is a warning
        assert report.warning_count >= 1
        assert any(i.code == "missing_comment_author" for i in report.issues)

    def test_scan_issue_invalid_date_range(self):
        """Test detection of invalid date ranges."""
        start = datetime(2025, 1, 15)
        end = datetime(2025, 1, 10)  # Earlier than start

        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.IN_PROGRESS,
            actual_start_date=start,
            actual_end_date=end,
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        assert not report.is_healthy
        assert any(i.code == "invalid_date_range" for i in report.issues)

    def test_scan_issue_in_progress_no_estimate(self):
        """Test warning for in-progress issue without estimate."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.IN_PROGRESS,
            estimated_hours=None,
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        # Missing estimate is info level
        assert report.info_count >= 1
        assert any(i.code == "missing_estimate" for i in report.issues)

    def test_scan_issue_invalid_progress_percentage(self):
        """Test detection of invalid progress percentage."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.IN_PROGRESS,
            progress_percentage=150,  # Invalid: > 100
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        assert not report.is_healthy
        assert any(i.code == "invalid_progress_percentage" for i in report.issues)

    def test_scan_issue_done_with_inconsistent_completion(self):
        """Test detection of Done status with non-100% progress."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.DONE,
            progress_percentage=75,
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        # Inconsistent completion is a warning
        assert report.warning_count >= 1
        assert any(i.code == "inconsistent_completion" for i in report.issues)

    def test_scan_issue_inconsistent_status(self):
        """Test detection of inconsistent status (has start date but TODO)."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.TODO,
            actual_start_date=datetime(2025, 1, 10),
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        # Inconsistent status is warning
        assert report.warning_count >= 1
        assert any(i.code == "inconsistent_status" for i in report.issues)

    def test_scan_issue_missing_completion_date(self):
        """Test detection of Done status without completion date."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.DONE,
            actual_end_date=None,
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        # Should have warning about missing completion date
        assert any(i.code == "missing_completion_date" for i in report.issues)

    def test_scan_issue_missing_handoff_date(self):
        """Test detection of handoff without date."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.DONE,
            previous_assignee="alice",
            handoff_date=None,
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        assert any(i.code == "missing_handoff_date" for i in report.issues)

    def test_report_counts(self):
        """Test that report correctly counts issues by severity."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="",  # Missing description (info)
            status=Status.DONE,
            progress_percentage=50,  # Inconsistent (warning)
            actual_end_date=None,  # Missing completion date (warning)
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        assert report.issue_count >= 2
        assert report.info_count >= 1
        assert report.warning_count >= 1

    def test_scan_empty_comment_list(self):
        """Test that scanner handles empty comment list correctly."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.TODO,
            comments=[],
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        # Empty comment list shouldn't cause issues
        assert report.is_healthy

    def test_circular_comment_reference_detection(self):
        """Test detection of circular references in comment replies."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.TODO,
            comments=[
                Comment(
                    id=1,
                    issue_id="issue-1",
                    author="alice",
                    body="First comment",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    in_reply_to=2,  # Replies to comment 2
                ),
                Comment(
                    id=2,
                    issue_id="issue-1",
                    author="bob",
                    body="Second comment",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    in_reply_to=1,  # Replies to comment 1 (circular!)
                ),
            ],
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        assert not report.is_healthy
        assert any(i.code == "circular_comment_reference" for i in report.issues)

    def test_duplicate_comment_id_detection(self):
        """Test detection of duplicate comment IDs."""
        issue = Issue(
            id="issue-1",
            title="Test Issue",
            content="Description",
            status=Status.TODO,
            comments=[
                Comment(
                    id=1,
                    issue_id="issue-1",
                    author="alice",
                    body="First comment",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                ),
                Comment(
                    id=1,  # Duplicate ID!
                    issue_id="issue-1",
                    author="bob",
                    body="Second comment",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                ),
            ],
        )

        scanner = EntityHealthScanner()
        report = scanner.scan_issue(issue)

        assert not report.is_healthy
        assert any(i.code == "duplicate_comment_id" for i in report.issues)
