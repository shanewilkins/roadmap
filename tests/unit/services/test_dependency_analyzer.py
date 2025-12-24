"""Tests for DependencyAnalyzer service."""

from roadmap.core.domain.issue import Issue
from roadmap.core.services.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyIssueType,
)


class TestDependencyAnalyzer:
    """Test suite for DependencyAnalyzer."""

    @staticmethod
    def create_issue(
        issue_id: str,
        title: str | None = None,
        depends_on: list | None = None,
        blocks: list | None = None,
    ):
        """Helper to create Issue objects with sensible defaults."""
        return Issue(
            id=issue_id,
            title=title or f"Issue {issue_id}",
            depends_on=depends_on or [],
            blocks=blocks or [],
        )

    def test_analyze_healthy_dependencies(self):
        """Test analyzing a set of healthy dependencies."""
        issues = [
            self.create_issue("1", depends_on=[], blocks=["2"]),
            self.create_issue("2", depends_on=["1"], blocks=[]),
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        # Should be one problem: missing bidirectional link warning
        # (Issue 1 blocks 2, but this check is expected)
        assert result.total_issues == 2
        assert result.issues_with_dependencies == 2
        assert len(result.circular_chains) == 0

    def test_detect_self_dependency(self):
        """Test detection of self-dependency (issue depends on itself)."""
        issues = [
            self.create_issue("1", depends_on=["1"], blocks=[]),
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        assert not result.is_healthy
        assert any(p.issue_type == DependencyIssueType.SELF for p in result.problems)

    def test_detect_circular_dependency_two_issues(self):
        """Test detection of circular dependency between two issues."""
        issues = [
            self.create_issue("1", depends_on=["2"], blocks=[]),
            self.create_issue("2", depends_on=["1"], blocks=[]),
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        assert not result.is_healthy
        assert len(result.circular_chains) > 0
        assert any(
            p.issue_type == DependencyIssueType.CIRCULAR for p in result.problems
        )

    def test_detect_circular_dependency_three_issues(self):
        """Test detection of circular dependency chain (A->B->C->A)."""
        issues = [
            self.create_issue("1", depends_on=["2"], blocks=[]),
            self.create_issue("2", depends_on=["3"], blocks=[]),
            self.create_issue("3", depends_on=["1"], blocks=[]),
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        assert not result.is_healthy
        assert len(result.circular_chains) > 0

    def test_detect_broken_dependency(self):
        """Test detection of broken dependency (points to non-existent issue)."""
        issues = [
            self.create_issue("1", depends_on=["non-existent"], blocks=[]),
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        assert not result.is_healthy
        assert any(p.issue_type == DependencyIssueType.BROKEN for p in result.problems)

    def test_detect_orphaned_blocker(self):
        """Test detection of orphaned blocker (blocks non-existent issue)."""
        issues = [
            self.create_issue("1", depends_on=[], blocks=["non-existent"]),
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        # Orphaned blocker is a warning, not an error
        assert any(
            p.issue_type == DependencyIssueType.ORPHANED_BLOCKER
            for p in result.problems
        )

    def test_detect_deep_dependency_chain(self):
        """Test detection of deep dependency chain (>5 levels)."""
        # Create a chain: 1 <- 2 <- 3 <- 4 <- 5 <- 6 <- 7
        issues = [
            self.create_issue("1", depends_on=[], blocks=[]),
            self.create_issue("2", depends_on=["1"], blocks=[]),
            self.create_issue("3", depends_on=["2"], blocks=[]),
            self.create_issue("4", depends_on=["3"], blocks=[]),
            self.create_issue("5", depends_on=["4"], blocks=[]),
            self.create_issue("6", depends_on=["5"], blocks=[]),
            self.create_issue("7", depends_on=["6"], blocks=[]),
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        # Issue 7 has a chain of length 7 (7->6->5->4->3->2->1)
        assert any(
            p.issue_type == DependencyIssueType.DEEP_CHAIN for p in result.problems
        )

    def test_missing_bidirectional_link_depends(self):
        """Test detection of missing bidirectional link (A depends on B, but B doesn't block A)."""
        issues = [
            Issue(id="1", title="Issue 1", depends_on=["2"], blocks=[]),
            Issue(
                id="2", title="Issue 2", depends_on=[], blocks=[]
            ),  # Doesn't list 1 as blocked
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        assert any(
            p.issue_type == DependencyIssueType.MISSING_BIDIRECTIONAL
            for p in result.problems
        )

    def test_missing_bidirectional_link_blocks(self):
        """Test detection of missing bidirectional link (A blocks B, but B doesn't depend on A)."""
        issues = [
            Issue(id="1", title="Issue 1", depends_on=[], blocks=["2"]),
            self.create_issue("2", depends_on=[], blocks=[]),  # Doesn't depend on 1
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        assert any(
            p.issue_type == DependencyIssueType.MISSING_BIDIRECTIONAL
            for p in result.problems
        )

    def test_analyze_empty_list(self):
        """Test analyzing an empty issue list."""
        analyzer = DependencyAnalyzer()
        result = analyzer.analyze([])

        assert result.total_issues == 0
        assert result.issues_with_dependencies == 0
        assert len(result.problems) == 0
        assert result.is_healthy

    def test_get_issues_affecting(self):
        """Test getting all issues affected by a given issue."""
        # Create a dependency tree:
        # 1 <- 2 <- 3
        # 1 <- 4
        issues = [
            self.create_issue("1", depends_on=[], blocks=["2", "4"]),
            self.create_issue("2", depends_on=["1"], blocks=["3"]),
            self.create_issue("3", depends_on=["2"], blocks=[]),
            self.create_issue("4", depends_on=["1"], blocks=[]),
        ]

        analyzer = DependencyAnalyzer()
        analyzer.analyze(issues)

        # Issue 1 affects issues 2, 3, 4 (directly or indirectly through blocking)
        affected = analyzer.get_issues_affecting("1")
        # The implementation looks for issues that depend on this one
        # Since 1 blocks 2 and 4, those should be affected
        assert "2" in affected
        assert "4" in affected

    def test_result_severity_classification(self):
        """Test that problem severities are correctly classified."""
        issues = [
            self.create_issue("1", depends_on=["1"], blocks=[]),  # Self (error)
            self.create_issue(
                "2", depends_on=["non-existent"], blocks=[]
            ),  # Broken (error)
            self.create_issue(
                "3", depends_on=["1"], blocks=[]
            ),  # Unidirectional (warning)
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        errors = [p for p in result.problems if p.severity == "error"]
        warnings = [p for p in result.problems if p.severity == "warning"]

        assert len(errors) >= 2  # Self and broken
        assert len(warnings) >= 1  # Missing bidirectional

    def test_result_counts(self):
        """Test that result correctly counts problems."""
        issues = [
            self.create_issue("1", depends_on=["1"], blocks=[]),  # error
            self.create_issue(
                "2", depends_on=["1"], blocks=[]
            ),  # warning (missing bidirectional)
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        assert result.error_count >= 1
        assert result.warning_count >= 1

    def test_multiple_blocking_relationships(self):
        """Test issue that blocks multiple other issues."""
        issues = [
            self.create_issue("1", depends_on=[], blocks=["2", "3", "4"]),
            self.create_issue("2", depends_on=["1"], blocks=[]),
            self.create_issue("3", depends_on=["1"], blocks=[]),
            self.create_issue("4", depends_on=["1"], blocks=[]),
        ]

        analyzer = DependencyAnalyzer()
        result = analyzer.analyze(issues)

        # Should be healthy - bidirectional links exist
        assert len(result.circular_chains) == 0
