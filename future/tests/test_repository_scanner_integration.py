"""
Integration tests for repository scanner functionality.

Tests the advanced repository scanning features in isolation
to ensure comprehensive coverage of the scanning capabilities.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from roadmap.core import RoadmapCore
from roadmap.models import Issue, IssueType, Priority, Status
from roadmap.parser import IssueParser
from roadmap.repository_scanner import (
    AdvancedRepositoryScanner,
    BranchAnalysis,
    CommitAnalysis,
    RepositoryScanConfig,
    RepositoryScanResult,
)


@pytest.mark.integration
@pytest.mark.slow
class TestRepositoryScannerCore:
    """Test core repository scanning functionality."""

    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir)
        self.original_cwd = os.getcwd()

        # Initialize git repo
        subprocess.run(
            ["git", "init"], cwd=self.repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test Scanner"],
            cwd=self.repo_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "scanner@test.com"],
            cwd=self.repo_path,
            check=True,
        )

        # Change to test directory
        os.chdir(self.repo_path)

        # Initialize roadmap
        self.core = RoadmapCore()
        self.core.initialize()

    def teardown_method(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_commits(self):
        """Create a realistic commit history for testing."""
        commits_data = [
            # Basic commits
            ("Initial commit", "README.md", "# Test Repository\\n"),
            ("Add project structure", "src/__init__.py", "# Main package\\n"),
            # Conventional commits with issue references
            (
                "feat: implement user authentication abc12345",
                "src/auth.py",
                "# Authentication module\\n",
            ),
            (
                "fix: resolve login bug abc12345 [progress:25%]",
                "src/auth.py",
                "# Authentication module\\n# Fixed login\\n",
            ),
            ("test: add authentication tests", "tests/test_auth.py", "# Auth tests\\n"),
            (
                "abc12345: complete authentication [progress:75%]",
                "src/auth.py",
                "# Authentication module\\n# Complete implementation\\n",
            ),
            # Different issue
            (
                "def67890: start user management feature",
                "src/users.py",
                "# User management\\n",
            ),
            (
                "feat(users): add user creation def67890",
                "src/users.py",
                "# User management\\n# User creation\\n",
            ),
            (
                "def67890: implement user profiles [progress:50%]",
                "src/users.py",
                "# User management\\n# Profiles\\n",
            ),
            # Completion markers
            (
                "abc12345: finalize authentication [closes roadmap:abc12345]",
                "src/auth.py",
                "# Authentication module\\n# Final version\\n",
            ),
            (
                "def67890: complete user management [progress:100%]",
                "src/users.py",
                "# User management\\n# Complete\\n",
            ),
            # Various commit types
            ("docs: update API documentation", "docs/api.md", "# API Documentation\\n"),
            (
                "chore: update dependencies",
                "requirements.txt",
                "requests==2.28.0\\npytest==7.0.0\\n",
            ),
            ("refactor: improve code structure", "src/utils.py", "# Utilities\\n"),
            (
                "style: fix code formatting",
                "src/auth.py",
                "# Authentication module\\n# Final version\\n# Formatted\\n",
            ),
            # Breaking changes
            (
                "feat!: redesign API interface 12345abc",
                "src/api.py",
                "# New API design\n",
            ),
            (
                "12345abc: implement breaking changes [progress:60%]",
                "src/api.py",
                "# New API design\n# Breaking changes\n",
            ),
        ]

        for message, filename, content in commits_data:
            file_path = self.repo_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            subprocess.run(["git", "add", filename], cwd=self.repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", message], cwd=self.repo_path, check=True
            )

        return len(commits_data)

    def create_test_branches(self):
        """Create test branches with various naming patterns."""
        branches = [
            ("feature/abc12345-authentication", "abc12345: add OAuth integration"),
            ("bugfix/def67890-user-validation", "def67890: fix user validation bug"),
            ("hotfix/critical-security-patch", "fix: patch security vulnerability"),
            ("feature/12345abc-api-redesign", "12345abc: implement new API endpoints"),
            ("docs/update-readme", "docs: comprehensive README update"),
            ("chore/dependency-updates", "chore: update all dependencies"),
        ]

        for branch_name, commit_msg in branches:
            subprocess.run(
                ["git", "checkout", "-b", branch_name], cwd=self.repo_path, check=True
            )
            test_file = self.repo_path / f'{branch_name.replace("/", "_")}.txt'
            test_file.write_text(f"Branch: {branch_name}\\n")
            subprocess.run(
                ["git", "add", test_file.name], cwd=self.repo_path, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", commit_msg], cwd=self.repo_path, check=True
            )
            subprocess.run(
                ["git", "checkout", "master"], cwd=self.repo_path, check=True
            )

        return len(branches)

    def test_commit_history_scanning(self):
        """Test comprehensive commit history analysis."""
        commit_count = self.create_test_commits()

        config = RepositoryScanConfig(max_commits=50, use_parallel_processing=False)
        scanner = AdvancedRepositoryScanner(self.core, config)

        commits = scanner.scan_commit_history()

        # Verify basic scanning
        assert len(commits) >= commit_count
        assert all(isinstance(c, CommitAnalysis) for c in commits)

        # Verify commit type detection
        commit_types = {c.commit_type for c in commits if c.commit_type}
        expected_types = {"feat", "fix", "test", "docs", "chore", "refactor", "style"}
        assert len(commit_types.intersection(expected_types)) >= 5

        # Verify issue ID extraction
        commits_with_issues = [c for c in commits if c.issue_ids]
        assert len(commits_with_issues) >= 8  # Should find multiple issue references

        # Verify specific issue IDs
        all_issue_ids = set()
        for c in commits_with_issues:
            all_issue_ids.update(c.issue_ids)
        assert "abc12345" in all_issue_ids
        assert "def67890" in all_issue_ids
        assert "12345abc" in all_issue_ids

        # Verify progress markers
        commits_with_progress = [c for c in commits if c.progress_markers]
        assert len(commits_with_progress) >= 4  # Should find progress markers

        # Verify completion markers
        commits_with_completion = [c for c in commits if c.completion_markers]
        assert len(commits_with_completion) >= 1  # Should find completion markers

        # Verify breaking change detection
        breaking_commits = [c for c in commits if c.breaking_change]
        assert len(breaking_commits) >= 1  # Should detect feat! commits

    def test_branch_history_scanning(self):
        """Test comprehensive branch analysis."""
        self.create_test_commits()  # Need some commits first
        branch_count = self.create_test_branches()

        config = RepositoryScanConfig(max_branches=20, use_parallel_processing=False)
        scanner = AdvancedRepositoryScanner(self.core, config)

        branches = scanner.scan_branch_history()

        # Verify basic scanning (includes master + created branches)
        assert len(branches) >= branch_count
        assert all(isinstance(b, BranchAnalysis) for b in branches)

        # Verify branch type detection
        branch_types = {b.branch_type for b in branches if b.branch_type}
        expected_types = {"feature", "bugfix", "docs", "chore"}
        assert len(branch_types.intersection(expected_types)) >= 3

        # Verify issue ID extraction from branch names
        branches_with_issues = [b for b in branches if b.issue_ids]
        assert len(branches_with_issues) >= 3  # Should find issue IDs in branch names

        # Verify specific issue associations
        branch_issue_ids = set()
        for b in branches_with_issues:
            branch_issue_ids.update(b.issue_ids)
        assert "abc12345" in branch_issue_ids
        assert "def67890" in branch_issue_ids
        assert "12345abc" in branch_issue_ids

        # Verify lifecycle stage detection
        lifecycle_stages = {b.lifecycle_stage for b in branches}
        # Should have main branch and other stages
        assert "main" in lifecycle_stages or "merged" in lifecycle_stages

    def test_comprehensive_scan_integration(self):
        """Test full comprehensive scanning functionality."""
        self.create_test_commits()
        self.create_test_branches()

        config = RepositoryScanConfig(
            max_commits=30,
            max_branches=15,
            use_parallel_processing=False,
            analyze_commit_patterns=True,
            analyze_branch_patterns=True,
        )

        scanner = AdvancedRepositoryScanner(self.core, config)
        result = scanner.perform_comprehensive_scan()

        # Verify result structure
        assert isinstance(result, RepositoryScanResult)
        assert result.total_commits_scanned > 0
        assert result.total_branches_scanned > 0
        assert result.scan_duration_seconds > 0

        # Verify issue associations
        assert len(result.issue_associations) >= 3  # abc12345, def67890, 12345abc
        assert len(result.commit_associations) > 0

        # Verify statistics
        assert result.issues_with_commits > 0
        assert result.commits_with_issues > 0
        assert result.commits_per_second > 0

        # Verify data completeness
        assert len(result.commits) > 0
        assert len(result.branches) > 0

    def test_migration_functionality(self):
        """Test project migration capabilities."""
        self.create_test_commits()

        # Create some existing issues that should be linked
        auth_issue = Issue(
            id="abc12345",
            title="Authentication Feature",
            priority=Priority.HIGH,
            type=IssueType.FEATURE,
            status=Status.IN_PROGRESS,
        )
        auth_issue_path = self.core.issues_dir / "abc12345.yaml"
        IssueParser.save_issue_file(auth_issue, auth_issue_path)

        user_issue = Issue(
            id="def67890",
            title="User Management",
            priority=Priority.MEDIUM,
            type=IssueType.FEATURE,
            status=Status.IN_PROGRESS,
        )
        user_issue_path = self.core.issues_dir / "def67890.yaml"
        IssueParser.save_issue_file(user_issue, user_issue_path)

        config = RepositoryScanConfig(
            max_commits=20, create_missing_issues=True, auto_link_issues=True
        )

        scanner = AdvancedRepositoryScanner(self.core, config)
        result = scanner.migrate_existing_project(create_issues=True, auto_link=True)

        # Verify migration results
        assert result.successful > 0
        assert result.duration > 0

        # Check that commits were linked to existing issues
        # Verify migration results
        assert result.successful > 0
        assert result.duration > 0

        # Check that the migration created files and linked commits properly
        # We can verify by checking the files directly since RoadmapCore.get_issue()
        # may have caching issues in the test environment
        abc_file = self.core.issues_dir / "abc12345.yaml"
        def_file = self.core.issues_dir / "def67890.yaml"
        new_file = self.core.issues_dir / "12345abc.yaml"

        # All files should exist
        assert abc_file.exists()
        assert def_file.exists()
        assert new_file.exists()

        # The new issue should have been created with git commits
        new_issue_data = IssueParser.parse_issue_file(new_file)
        assert new_issue_data.id == "12345abc"
        assert len(new_issue_data.git_commits) > 0

        # Existing issues should have had commits linked
        abc_issue_data = IssueParser.parse_issue_file(abc_file)
        assert len(abc_issue_data.git_commits) > 0

        # May or may not exist depending on create_missing_issues setting

    def test_export_functionality(self):
        """Test exporting scan results to JSON."""
        self.create_test_commits()
        self.create_test_branches()

        config = RepositoryScanConfig(max_commits=15, max_branches=10)
        scanner = AdvancedRepositoryScanner(self.core, config)

        scan_result = scanner.perform_comprehensive_scan()

        # Test export to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            export_path = Path(f.name)

        try:
            exported_path = scanner.export_scan_results(scan_result, export_path)
            assert exported_path.exists()
            assert exported_path == export_path

            # Verify exported content structure
            with open(exported_path) as f:
                data = json.load(f)

            # Check required sections
            required_sections = [
                "scan_metadata",
                "statistics",
                "commits",
                "branches",
                "associations",
            ]
            for section in required_sections:
                assert section in data

            # Verify metadata
            metadata = data["scan_metadata"]
            assert "scan_date" in metadata
            assert "repository_path" in metadata
            assert "scan_duration_seconds" in metadata

            # Verify statistics
            stats = data["statistics"]
            assert stats["total_commits_scanned"] > 0
            assert stats["total_branches_scanned"] > 0

            # Verify commits data
            commits = data["commits"]
            assert len(commits) > 0

            # Check commit structure
            commit = commits[0]
            required_commit_fields = ["sha", "message", "author", "date", "issue_ids"]
            for field in required_commit_fields:
                assert field in commit

            # Verify branches data
            branches = data["branches"]
            assert len(branches) > 0

            # Check branch structure
            branch = branches[0]
            required_branch_fields = [
                "name",
                "issue_ids",
                "branch_type",
                "lifecycle_stage",
            ]
            for field in required_branch_fields:
                assert field in branch

            # Verify associations
            associations = data["associations"]
            assert "issue_to_commits" in associations
            assert "commit_to_issues" in associations

        finally:
            if export_path.exists():
                export_path.unlink()

    def test_configuration_options(self):
        """Test various configuration options for scanning."""
        self.create_test_commits()

        # Test with minimal configuration
        minimal_config = RepositoryScanConfig(
            max_commits=5, max_branches=3, use_parallel_processing=False
        )

        scanner = AdvancedRepositoryScanner(self.core, minimal_config)
        result = scanner.perform_comprehensive_scan()

        assert result.total_commits_scanned <= 5
        assert result.total_branches_scanned <= 3

        # Test with date filtering
        from datetime import datetime, timedelta

        recent_config = RepositoryScanConfig(
            max_commits=50,
            since_date=datetime.now() - timedelta(days=1),  # Only recent commits
            use_parallel_processing=False,
        )

        scanner = AdvancedRepositoryScanner(self.core, recent_config)
        result = scanner.perform_comprehensive_scan()

        # Should find commits (they were just created)
        assert result.total_commits_scanned > 0

        # Test with custom patterns
        custom_config = RepositoryScanConfig(
            max_commits=20,
            custom_patterns=[r"custom-pattern-\\d+"],
            ignore_patterns=[r"^Merge\\s+", r"^WIP"],
            use_parallel_processing=False,
        )

        scanner = AdvancedRepositoryScanner(self.core, custom_config)
        result = scanner.perform_comprehensive_scan()

        # Should still scan successfully with custom patterns
        assert result.total_commits_scanned > 0

    def test_error_handling(self):
        """Test error handling in various scenarios."""
        config = RepositoryScanConfig(max_commits=10, use_parallel_processing=False)
        scanner = AdvancedRepositoryScanner(self.core, config)

        # Test scanning empty repository
        result = scanner.perform_comprehensive_scan()

        # Should handle gracefully even with minimal commit history
        assert isinstance(result, RepositoryScanResult)
        assert result.total_commits_scanned >= 0  # Could be 0 for empty repo
        assert result.scan_duration_seconds >= 0

        # Test with invalid configuration
        invalid_config = RepositoryScanConfig(
            max_commits=-1,  # Invalid
            max_branches=0,  # Edge case
        )

        scanner = AdvancedRepositoryScanner(self.core, invalid_config)
        result = scanner.perform_comprehensive_scan()

        # Should handle invalid config gracefully
        assert isinstance(result, RepositoryScanResult)

    def test_performance_characteristics(self):
        """Test performance characteristics of scanning."""
        # Create larger commit history for performance testing
        self.create_test_commits()

        # Test sequential vs parallel processing (when applicable)
        sequential_config = RepositoryScanConfig(
            max_commits=20, use_parallel_processing=False
        )

        parallel_config = RepositoryScanConfig(
            max_commits=20, use_parallel_processing=True, max_workers=2
        )

        scanner_seq = AdvancedRepositoryScanner(self.core, sequential_config)
        scanner_par = AdvancedRepositoryScanner(self.core, parallel_config)

        # Test sequential scanning
        result_seq = scanner_seq.perform_comprehensive_scan()

        # Test parallel scanning
        result_par = scanner_par.perform_comprehensive_scan()

        # Both should produce valid results
        assert result_seq.total_commits_scanned > 0
        assert result_par.total_commits_scanned > 0

        # Results should be equivalent
        assert result_seq.total_commits_scanned == result_par.total_commits_scanned
        assert len(result_seq.issue_associations) == len(result_par.issue_associations)

        # Both should complete in reasonable time
        assert result_seq.scan_duration_seconds < 30  # Should be fast for small repos
        assert result_par.scan_duration_seconds < 30
