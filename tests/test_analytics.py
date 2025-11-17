"""Tests for Git history analytics functionality."""

import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Mark all tests in this file as unit tests (primarily mock-based)
pytestmark = pytest.mark.unit

from roadmap.analytics import (
    AnalyticsReportGenerator,
    DeveloperMetrics,
    GitHistoryAnalyzer,
    ProjectVelocity,
    TeamInsights,
)
from roadmap.core import RoadmapCore
from roadmap.git_integration import GitCommit
from roadmap.models import Issue, Priority, Status


class TestGitHistoryAnalyzer:
    """Test Git history analyzer functionality."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary Git repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Initialize Git repo
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], check=True
            )

            # Initialize roadmap
            core = RoadmapCore()
            core.initialize()

            yield temp_dir, core

    def test_analyzer_initialization(self, temp_git_repo):
        """Test GitHistoryAnalyzer initialization."""
        _, core = temp_git_repo

        analyzer = GitHistoryAnalyzer(core)

        assert analyzer.core == core
        assert analyzer.git_integration is not None

    @patch("roadmap.analytics.GitIntegration")
    def test_analyze_developer_productivity(self, mock_git_integration, temp_git_repo):
        """Test developer productivity analysis."""
        _, core = temp_git_repo

        # Create test issue with git commits
        issue = core.create_issue("Test Issue", Priority.HIGH)
        issue.assignee = "Test Developer"
        issue.status = Status.DONE
        issue.completed_date = datetime.now().isoformat()
        issue.git_commits = [
            {
                "hash": "abc123",
                "message": "Test commit",
                "date": (datetime.now() - timedelta(hours=2)).isoformat(),
                "progress": 50.0,
            },
            {
                "hash": "def456",
                "message": "Complete work",
                "date": datetime.now().isoformat(),
                "completion": True,
            },
        ]

        # Save the issue
        from roadmap.parser import IssueParser

        issue_path = core.issues_dir / issue.filename
        IssueParser.save_issue_file(issue, issue_path)

        # Mock Git integration
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True

        # Create mock commits
        commit1 = Mock(spec=GitCommit)
        commit1.author = "Test Developer"
        commit1.date = datetime.now() - timedelta(hours=2)
        commit1.files_changed = ["test.py"]
        commit1.insertions = 10
        commit1.deletions = 5

        commit2 = Mock(spec=GitCommit)
        commit2.author = "Test Developer"
        commit2.date = datetime.now()
        commit2.files_changed = ["test.py", "README.md"]
        commit2.insertions = 20
        commit2.deletions = 3

        mock_git.get_recent_commits.return_value = [commit1, commit2]
        mock_git_integration.return_value = mock_git

        analyzer = GitHistoryAnalyzer(core)
        analyzer.git_integration = mock_git

        # Analyze developer productivity
        metrics = analyzer.analyze_developer_productivity("Test Developer", 30)

        # Verify metrics
        assert metrics.name == "Test Developer"
        assert metrics.total_commits == 2
        assert metrics.issues_completed == 1
        assert metrics.avg_commits_per_day > 0
        assert metrics.productivity_score > 0
        assert isinstance(metrics.specialization_areas, list)
        assert metrics.collaboration_score >= 0

    @patch("roadmap.analytics.GitIntegration")
    def test_analyze_project_velocity(self, mock_git_integration, temp_git_repo):
        """Test project velocity analysis."""
        _, core = temp_git_repo

        # Mock Git integration
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True

        # Create mock commits spanning multiple weeks
        commits = []
        base_date = datetime.now() - timedelta(weeks=4)

        for week in range(4):
            for day in range(5):  # 5 commits per week
                commit = Mock(spec=GitCommit)
                commit.author = f"Developer {(week + day) % 3 + 1}"  # 3 developers
                commit.date = base_date + timedelta(weeks=week, days=day)
                commit.insertions = 50 + (week * 10)
                commit.deletions = 10 + (week * 2)
                commit.extract_roadmap_references.return_value = [f"issue{week}{day}"]
                commits.append(commit)

        mock_git.get_recent_commits.return_value = commits
        mock_git_integration.return_value = mock_git

        analyzer = GitHistoryAnalyzer(core)
        analyzer.git_integration = mock_git

        # Analyze velocity
        velocities = analyzer.analyze_project_velocity("week", 4)

        # Verify results
        assert len(velocities) == 4
        assert all(isinstance(v, ProjectVelocity) for v in velocities)
        assert all(v.period == "week" for v in velocities)
        assert all(v.velocity_score >= 0 for v in velocities)
        assert all(
            v.trend_direction in ["increasing", "decreasing", "stable"]
            for v in velocities
        )

    @patch("roadmap.analytics.GitIntegration")
    def test_generate_team_insights(self, mock_git_integration, temp_git_repo):
        """Test team insights generation."""
        _, core = temp_git_repo

        # Mock Git integration
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True

        # Create mock commits from multiple developers
        commits = []
        developers = ["Alice", "Bob", "Charlie"]

        for i, dev in enumerate(developers):
            for j in range(10):  # 10 commits per developer
                commit = Mock(spec=GitCommit)
                commit.author = dev
                commit.date = datetime.now() - timedelta(hours=j)
                commit.files_changed = [f"{dev.lower()}_file_{j}.py"]
                commit.insertions = 20 + (i * 5)
                commit.deletions = 5 + i
                commits.append(commit)

        mock_git.get_recent_commits.return_value = commits
        mock_git_integration.return_value = mock_git

        analyzer = GitHistoryAnalyzer(core)
        analyzer.git_integration = mock_git

        # Generate insights
        insights = analyzer.generate_team_insights(30)

        # Verify insights
        assert isinstance(insights, TeamInsights)
        assert insights.total_developers == 3
        assert insights.avg_team_velocity > 0
        assert isinstance(insights.bottleneck_areas, list)
        assert isinstance(insights.top_performers, list)
        assert isinstance(insights.collaboration_patterns, dict)
        assert isinstance(insights.recommended_actions, list)

    @patch("roadmap.analytics.GitIntegration")
    def test_analyze_code_quality_trends(self, mock_git_integration, temp_git_repo):
        """Test code quality trend analysis."""
        _, core = temp_git_repo

        # Mock Git integration
        mock_git = Mock()
        mock_git.is_git_repository.return_value = True

        # Create mock commits with different types
        commits = []
        commit_types = [
            ("feat: add new feature", 100, 10),
            ("fix: resolve bug issue", 20, 5),
            ("refactor: cleanup code", 50, 30),
            ("feat: implement login", 200, 15),
            ("fix: auth error", 10, 2),
        ]

        for message, insertions, deletions in commit_types:
            commit = Mock(spec=GitCommit)
            commit.message = message
            commit.date = datetime.now() - timedelta(hours=len(commits))
            commit.insertions = insertions
            commit.deletions = deletions
            commits.append(commit)

        mock_git.get_recent_commits.return_value = commits
        mock_git_integration.return_value = mock_git

        analyzer = GitHistoryAnalyzer(core)
        analyzer.git_integration = mock_git

        # Analyze quality trends
        quality = analyzer.analyze_code_quality_trends(90)

        # Verify quality metrics
        assert "total_commits" in quality
        assert "bug_fix_ratio" in quality
        assert "feature_ratio" in quality
        assert "refactor_ratio" in quality
        assert "avg_commit_size" in quality
        assert "large_commits_ratio" in quality
        assert "quality_score" in quality
        assert "recommendations" in quality

        assert quality["total_commits"] == 5
        assert 0 <= quality["bug_fix_ratio"] <= 1
        assert 0 <= quality["feature_ratio"] <= 1
        assert 0 <= quality["refactor_ratio"] <= 1
        assert quality["avg_commit_size"] > 0
        assert 0 <= quality["quality_score"] <= 100

    def test_calculate_productivity_score(self, temp_git_repo):
        """Test productivity score calculation."""
        _, core = temp_git_repo
        analyzer = GitHistoryAnalyzer(core)

        # Test various scenarios
        score1 = analyzer._calculate_productivity_score(
            10, 5, 2.0, 24.0
        )  # Good performance
        score2 = analyzer._calculate_productivity_score(
            2, 1, 0.5, 48.0
        )  # Moderate performance
        score3 = analyzer._calculate_productivity_score(
            50, 20, 5.0, 12.0
        )  # Excellent performance

        assert 0 <= score1 <= 100
        assert 0 <= score2 <= 100
        assert 0 <= score3 <= 100
        assert score3 > score1 > score2  # Better metrics should yield higher scores

    def test_analyze_specialization(self, temp_git_repo):
        """Test specialization analysis."""
        _, core = temp_git_repo
        analyzer = GitHistoryAnalyzer(core)

        # Create mock commits with different file types
        commits = []
        files_and_types = [
            ["app.py", "model.py", "view.py"],
            ["script.js", "component.tsx"],
            ["README.md", "docs.md"],
            ["deploy.yaml", "config.yml"],
        ]

        for files in files_and_types:
            commit = Mock(spec=GitCommit)
            commit.files_changed = files
            commits.append(commit)

        # Create mock issues
        issues = [
            Mock(issue_type=Mock(value="feature")),
            Mock(issue_type=Mock(value="bug")),
            Mock(issue_type=Mock(value="feature")),
        ]

        specializations = analyzer._analyze_specialization(commits, issues)

        assert isinstance(specializations, list)
        assert len(specializations) <= 3
        # Should detect Python, JavaScript, Documentation, DevOps, and feature issues
        assert any(
            "Python" in spec
            or "JavaScript" in spec
            or "Documentation" in spec
            or "DevOps" in spec
            or "feature" in spec
            for spec in specializations
        )

    def test_calculate_collaboration_score(self, temp_git_repo):
        """Test collaboration score calculation."""
        _, core = temp_git_repo
        analyzer = GitHistoryAnalyzer(core)

        # Developer commits
        dev_commits = [
            Mock(author="Alice", files_changed=["file1.py", "file2.py"]),
            Mock(author="Alice", files_changed=["file3.py"]),
        ]

        # All commits including others
        all_commits = dev_commits + [
            Mock(author="Bob", files_changed=["file1.py", "file4.py"]),
            Mock(author="Charlie", files_changed=["file2.py", "file5.py"]),
        ]

        score = analyzer._calculate_collaboration_score(dev_commits, all_commits)

        assert 0 <= score <= 100
        assert score > 0  # Should have some collaboration since files are shared

    def test_non_git_repository_handling(self):
        """Test handling when not in a Git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Initialize roadmap without Git
            core = RoadmapCore()
            core.initialize()

            analyzer = GitHistoryAnalyzer(core)

            # Should raise ValueError for Git operations
            with pytest.raises(ValueError, match="Not in a Git repository"):
                analyzer.analyze_developer_productivity("test", 30)

            with pytest.raises(ValueError, match="Not in a Git repository"):
                analyzer.analyze_project_velocity()

            with pytest.raises(ValueError, match="Not in a Git repository"):
                analyzer.generate_team_insights()


class TestAnalyticsReportGenerator:
    """Test analytics report generator functionality."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create a mock analyzer for testing."""
        analyzer = Mock(spec=GitHistoryAnalyzer)

        # Mock team insights
        insights = TeamInsights(
            total_developers=3,
            avg_team_velocity=75.0,
            bottleneck_areas=["Limited collaboration"],
            top_performers=["Alice", "Bob"],
            collaboration_patterns={"shared_files_count": 10},
            recommended_actions=["Improve code reviews"],
        )
        analyzer.generate_team_insights.return_value = insights

        # Mock velocity trends
        velocities = [
            ProjectVelocity(
                period="week",
                start_date=datetime.now() - timedelta(weeks=1),
                end_date=datetime.now(),
                commits_count=20,
                issues_completed=5,
                lines_added=500,
                lines_removed=100,
                velocity_score=80.0,
                trend_direction="increasing",
            )
        ]
        analyzer.analyze_project_velocity.return_value = velocities

        # Mock quality trends
        quality = {
            "period_days": 30,
            "total_commits": 50,
            "bug_fix_ratio": 0.2,
            "feature_ratio": 0.6,
            "refactor_ratio": 0.2,
            "avg_commit_size": 75,
            "large_commits_ratio": 0.1,
            "quality_score": 80.0,
            "recommendations": ["Good quality practices"],
        }
        analyzer.analyze_code_quality_trends.return_value = quality

        # Mock Git integration
        analyzer.git_integration = Mock()
        analyzer.git_integration.get_recent_commits.return_value = [
            Mock(author="Alice"),
            Mock(author="Bob"),
            Mock(author="Charlie"),
        ]

        return analyzer

    def test_generate_team_report(self, mock_analyzer):
        """Test team report generation."""
        generator = AnalyticsReportGenerator(mock_analyzer)

        # Mock developer productivity
        with patch.object(
            mock_analyzer, "analyze_developer_productivity"
        ) as mock_dev_analysis:
            dev_metrics = DeveloperMetrics(
                name="Alice",
                total_commits=10,
                issues_completed=3,
                avg_commits_per_day=1.5,
                avg_completion_time_hours=24.0,
                productivity_score=85.0,
                specialization_areas=["Python", "Frontend"],
                collaboration_score=70.0,
            )
            mock_dev_analysis.return_value = dev_metrics

            report = generator.generate_team_report(30)

        # Verify report structure
        assert "report_generated" in report
        assert "analysis_period_days" in report
        assert "team_overview" in report
        assert "velocity_trends" in report
        assert "code_quality" in report
        assert "developer_metrics" in report
        assert "collaboration_patterns" in report

        # Verify team overview
        overview = report["team_overview"]
        assert overview["total_developers"] == 3
        assert overview["avg_team_velocity"] == 75.0
        assert "top_performers" in overview
        assert "bottlenecks" in overview
        assert "recommendations" in overview

        # Verify developer metrics
        dev_metrics = report["developer_metrics"]
        assert len(dev_metrics) > 0
        assert all("name" in dev for dev in dev_metrics)
        assert all("productivity_score" in dev for dev in dev_metrics)

    def test_save_report_to_file(self, mock_analyzer, tmp_path):
        """Test saving report to file."""
        generator = AnalyticsReportGenerator(mock_analyzer)

        report = {"test_data": "test_value", "timestamp": datetime.now().isoformat()}

        # Test with custom filename
        filename = str(tmp_path / "test_report.json")
        saved_path = generator.save_report_to_file(report, filename)

        assert Path(saved_path).exists()
        assert Path(saved_path).name == "test_report.json"

        # Verify file content
        import json

        with open(saved_path) as f:
            loaded_report = json.load(f)

        assert loaded_report["test_data"] == "test_value"
        assert "timestamp" in loaded_report

    def test_report_error_handling(self, mock_analyzer):
        """Test error handling in report generation."""
        generator = AnalyticsReportGenerator(mock_analyzer)

        # Mock analyzer to raise exception
        mock_analyzer.generate_team_insights.side_effect = Exception("Test error")

        report = generator.generate_team_report(30)

        # Should return error report
        assert "error" in report
        assert "Test error" in report["error"]
        assert "report_generated" in report


class TestAnalyticsIntegration:
    """Integration tests for analytics functionality."""

    @pytest.fixture
    def git_repo_with_data(self):
        """Create Git repo with realistic commit data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Initialize Git repo
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test Developer"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], check=True
            )

            # Initialize roadmap
            core = RoadmapCore()
            core.initialize()

            # Create some realistic files and commits
            files_and_commits = [
                ("app.py", "feat: initial app structure"),
                ("models.py", "feat: add data models"),
                ("views.py", "feat: implement views"),
                ("app.py", "fix: resolve startup issue"),
                ("tests.py", "feat: add unit tests"),
                ("README.md", "docs: add documentation"),
                ("app.py", "refactor: improve error handling"),
            ]

            # Create initial commit
            Path("README.md").write_text("# Test Project")
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

            # Create commits with realistic patterns
            for filename, commit_msg in files_and_commits:
                # Modify or create file
                file_path = Path(filename)
                if file_path.exists():
                    content = file_path.read_text() + f"\n# {commit_msg}"
                else:
                    content = f"# {filename}\n# {commit_msg}"
                file_path.write_text(content)

                subprocess.run(["git", "add", filename], check=True)
                subprocess.run(["git", "commit", "-m", commit_msg], check=True)

            yield temp_dir, core

    def test_real_analytics_workflow(self, git_repo_with_data):
        """Test analytics with real Git data."""
        _, core = git_repo_with_data

        analyzer = GitHistoryAnalyzer(core)

        # First, let's get all commits to see what we have
        all_commits = analyzer.git_integration.get_recent_commits(count=100)

        # Find the actual developer name from commits
        developers = {c.author for c in all_commits if c.author}
        assert len(developers) > 0, f"No developers found in commits: {all_commits}"

        # Use the first developer we find (should be "Test Developer")
        test_developer = next(iter(developers))

        # Test developer analysis with a longer time window to be safe
        metrics = analyzer.analyze_developer_productivity(test_developer, days=365)

        assert metrics.name == test_developer
        assert metrics.total_commits > 0, f"No commits found for {test_developer}. All commits: {[(c.author, c.date) for c in all_commits]}"
        assert metrics.productivity_score > 0
        assert metrics.avg_commits_per_day >= 0

        # Test velocity analysis
        velocities = analyzer.analyze_project_velocity("week", 4)

        assert len(velocities) <= 4
        assert all(v.commits_count >= 0 for v in velocities)
        assert all(v.velocity_score >= 0 for v in velocities)

        # Test quality analysis
        quality = analyzer.analyze_code_quality_trends(90)

        assert quality["total_commits"] > 0
        assert 0 <= quality["bug_fix_ratio"] <= 1
        assert 0 <= quality["feature_ratio"] <= 1
        assert 0 <= quality["quality_score"] <= 100

    def test_analytics_report_generation(self, git_repo_with_data):
        """Test full analytics report generation."""
        _, core = git_repo_with_data

        analyzer = GitHistoryAnalyzer(core)
        generator = AnalyticsReportGenerator(analyzer)

        # Generate report
        report = generator.generate_team_report(30)

        # Should not have errors
        assert "error" not in report

        # Verify report structure
        required_sections = [
            "report_generated",
            "analysis_period_days",
            "team_overview",
            "velocity_trends",
            "code_quality",
            "developer_metrics",
        ]

        for section in required_sections:
            assert section in report, f"Missing section: {section}"

        # Verify data quality
        assert report["analysis_period_days"] == 30
        assert report["team_overview"]["total_developers"] > 0
        assert len(report["developer_metrics"]) > 0
        assert report["code_quality"]["total_commits"] > 0


if __name__ == "__main__":
    pytest.main([__file__])
