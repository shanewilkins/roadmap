"""Integration tests for team collaboration features."""

import os
import tempfile
from pathlib import Path

from click.testing import CliRunner

from roadmap.presentation.cli import main


class TestTeamCollaborationIntegration:
    """End-to-end integration tests for team collaboration."""

    def test_complete_team_workflow(self):
        """Test complete team collaboration workflow from start to finish."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            # Step 1: Initialize roadmap
            result = runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "Team Collaboration Test",
                ],
            )
            assert result.exit_code == 0
            assert "Roadmap CLI Initialization" in result.output

            # Step 2: Create issues with different assignees
            result = runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    "Fix login bug",
                    "--assignee",
                    "alice",
                    "--priority",
                    "high",
                ],
            )
            assert result.exit_code == 0
            assert "Assignee: alice" in result.output

            result = runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    "Add dark mode",
                    "--assignee",
                    "bob",
                    "--priority",
                    "medium",
                ],
            )
            assert result.exit_code == 0
            assert "Assignee: bob" in result.output

            result = runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    "Database optimization",
                    "--assignee",
                    "alice",
                    "--priority",
                    "low",
                ],
            )
            assert result.exit_code == 0
            assert "Assignee: alice" in result.output

            result = runner.invoke(main, ["issue", "create", "Unassigned task"])
            assert result.exit_code == 0

            # Step 3: List all issues and verify assignee information
            result = runner.invoke(main, ["issue", "list"])
            assert result.exit_code == 0
            # Check for assignee data in the output
            assert "alice" in result.output
            assert "bob" in result.output
            assert "Unassigned" in result.output

            # Step 4: Filter by specific assignee
            result = runner.invoke(main, ["issue", "list", "--assignee", "alice"])
            assert result.exit_code == 0
            assert "assigned to alice" in result.output
            # Should show 2 issues for alice
            lines = result.output.split("\n")
            table_lines = [line for line in lines if "alice" in line and "│" in line]
            assert len(table_lines) == 2

            # Step 5: Test assignee filter validation
            result = runner.invoke(
                main, ["issue", "list", "--assignee", "alice", "--my-issues"]
            )
            assert result.exit_code == 0
            assert "Cannot combine --assignee and --my-issues filters" in result.output

            # Step 6: Verify file system structure
            issues_dir = Path(".roadmap/issues")
            assert issues_dir.exists()
            issue_files = list(issues_dir.glob("*.md"))
            assert len(issue_files) == 4

            # Step 7: Verify assignee data is persisted in files
            alice_issues = []
            for issue_file in issue_files:
                content = issue_file.read_text()
                if "assignee: alice" in content:
                    alice_issues.append(issue_file)
            assert len(alice_issues) == 2

    def test_team_assignment_workflow(self):
        """Test team assignment and workload management workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            # Initialize and create test issues
            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            # Create issues with different statuses and assignees
            runner.invoke(main, ["issue", "create", "Task 1", "--assignee", "alice"])
            runner.invoke(main, ["issue", "create", "Task 2", "--assignee", "alice"])
            runner.invoke(main, ["issue", "create", "Task 3", "--assignee", "bob"])

            # Test team assignments command
            result = runner.invoke(main, ["team", "assignments"])
            assert result.exit_code == 0
            # Strip ANSI codes for cleaner matching
            import re

            clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
            assert "alice (2 issues)" in clean_output
            assert "bob (1 issue)" in clean_output

            # Test team workload command
            result = runner.invoke(main, ["team", "workload"])
            assert result.exit_code == 0
            assert "Team Workload Summary" in result.output

    def test_assignee_update_workflow(self):
        """Test updating issue assignees."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            # Initialize and create an issue
            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            result = runner.invoke(
                main, ["issue", "create", "Test task", "--assignee", "alice"]
            )
            assert result.exit_code == 0

            # Extract issue ID from output
            output_lines = result.output.split("\n")
            id_line = [line for line in output_lines if "ID:" in line][0]
            issue_id = id_line.split("ID:")[1].strip()

            # Update assignee
            result = runner.invoke(
                main, ["issue", "update", issue_id, "--assignee", "bob"]
            )
            assert result.exit_code == 0

            # Verify the assignee was updated
            result = runner.invoke(main, ["issue", "list", "--assignee", "bob"])
            assert result.exit_code == 0
            assert "assigned to bob" in result.output

            # Verify alice no longer has this issue
            result = runner.invoke(main, ["issue", "list", "--assignee", "alice"])
            assert result.exit_code == 0
            assert "No assigned to alice issues found" in result.output

    def test_unassign_workflow(self):
        """Test unassigning issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            # Initialize and create an assigned issue
            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            result = runner.invoke(
                main, ["issue", "create", "Test task", "--assignee", "alice"]
            )
            assert result.exit_code == 0

            # Extract issue ID
            output_lines = result.output.split("\n")
            id_line = [line for line in output_lines if "ID:" in line][0]
            issue_id = id_line.split("ID:")[1].strip()

            # Unassign by setting empty assignee
            result = runner.invoke(
                main, ["issue", "update", issue_id, "--assignee", ""]
            )
            assert result.exit_code == 0

            # Verify the issue is now unassigned
            result = runner.invoke(main, ["issue", "list"])
            assert result.exit_code == 0
            # Check for unassigned status (may be truncated in table display)
            assert (
                "Unassi" in result.output
                or "Unassigned" in result.output
                or "Unass" in result.output
            )

            # Verify alice no longer has this issue
            result = runner.invoke(main, ["issue", "list", "--assignee", "alice"])
            assert result.exit_code == 0
            assert "No assigned to alice issues found" in result.output

    def test_mixed_status_assignee_workflow(self):
        """Test assignee functionality with different issue statuses."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            # Initialize roadmap
            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            # Create issues with different statuses
            result = runner.invoke(
                main, ["issue", "create", "Todo task", "--assignee", "alice"]
            )
            result.output.split("ID:")[1].split()[0]

            result = runner.invoke(
                main, ["issue", "create", "In progress task", "--assignee", "alice"]
            )
            progress_id = result.output.split("ID:")[1].split()[0]

            result = runner.invoke(
                main, ["issue", "create", "Review task", "--assignee", "alice"]
            )
            review_id = result.output.split("ID:")[1].split()[0]

            # Update statuses
            runner.invoke(
                main, ["issue", "update", progress_id, "--status", "in-progress"]
            )
            runner.invoke(main, ["issue", "update", review_id, "--status", "review"])

            # Test filtering by assignee with different statuses
            result = runner.invoke(main, ["issue", "list", "--assignee", "alice"])
            assert result.exit_code == 0
            assert "assigned to alice" in result.output

            # Should show all 3 issues for alice regardless of status
            lines = result.output.split("\n")
            table_lines = [line for line in lines if "alice" in line and "│" in line]
            assert len(table_lines) == 3

            # Test combining assignee with status filter
            result = runner.invoke(
                main, ["issue", "list", "--assignee", "alice", "--status", "review"]
            )
            assert result.exit_code == 0
            # Should show only the review task
            lines = result.output.split("\n")
            table_lines = [line for line in lines if "alice" in line and "│" in line]
            assert len(table_lines) == 1

    def test_persistence_across_sessions(self):
        """Test that assignee data persists across different CLI sessions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Session 1: Create issues with assignees
            runner1 = CliRunner()
            runner1.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )
            runner1.invoke(
                main, ["issue", "create", "Persistent task", "--assignee", "alice"]
            )

            # Session 2: Verify assignee data is still there
            runner2 = CliRunner()
            result = runner2.invoke(main, ["issue", "list", "--assignee", "alice"])
            assert result.exit_code == 0
            assert "assigned to alice" in result.output

            # Session 3: Update assignee
            runner3 = CliRunner()
            result = runner3.invoke(main, ["issue", "list"])
            assert result.exit_code == 0

            # Get the issue ID from the list
            lines = result.output.split("\n")
            issue_line = [line for line in lines if "alice" in line and "│" in line][0]
            issue_id = issue_line.split("│")[1].strip()

            runner3.invoke(main, ["issue", "update", issue_id, "--assignee", "bob"])

            # Session 4: Verify the update persisted
            runner4 = CliRunner()
            result = runner4.invoke(main, ["issue", "list", "--assignee", "bob"])
            assert result.exit_code == 0
            assert "assigned to bob" in result.output

    def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases in team collaboration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            # Test team commands without initialization
            result = runner.invoke(main, ["team", "members"])
            assert result.exit_code == 0
            # Should handle gracefully

            # Initialize for remaining tests
            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            # Test with special characters in assignee names
            result = runner.invoke(
                main,
                ["issue", "create", "Special char test", "--assignee", "user-name_123"],
            )
            assert result.exit_code == 0
            assert "user-name_123" in result.output

            # Test filtering with non-existent assignee
            result = runner.invoke(main, ["issue", "list", "--assignee", "nonexistent"])
            assert result.exit_code == 0
            assert "No assigned to nonexistent issues found" in result.output

            # Test empty assignee handling
            result = runner.invoke(
                main, ["issue", "create", "Empty assignee test", "--assignee", ""]
            )
            assert result.exit_code == 0

            # Test very long assignee name
            long_name = "a" * 100
            result = runner.invoke(
                main, ["issue", "create", "Long name test", "--assignee", long_name]
            )
            assert result.exit_code == 0
            # The long name might be wrapped, so check if it contains most of it
            assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in result.output


class TestTeamCollaborationPerformance:
    """Performance tests for team collaboration features."""

    def test_large_team_performance(self):
        """Test performance with many assignees and issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            # Initialize roadmap
            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            # Create many issues with different assignees
            assignees = [f"user{i}" for i in range(10)]

            for i in range(50):  # 50 issues
                assignee = assignees[i % len(assignees)]
                result = runner.invoke(
                    main, ["issue", "create", f"Task {i}", "--assignee", assignee]
                )
                assert result.exit_code == 0

            # Test performance of listing all issues
            result = runner.invoke(main, ["issue", "list"])
            assert result.exit_code == 0
            assert "50 all issues" in result.output

            # Test performance of filtering by assignee
            result = runner.invoke(main, ["issue", "list", "--assignee", "user0"])
            assert result.exit_code == 0
            assert "assigned to user0" in result.output

            # Test team commands performance
            result = runner.invoke(main, ["team", "assignments"])
            assert result.exit_code == 0

            result = runner.invoke(main, ["team", "workload"])
            assert result.exit_code == 0

    def test_assignee_filter_performance(self):
        """Test performance of assignee filtering with many issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            # Create 20 issues for the same assignee
            for i in range(20):
                runner.invoke(
                    main, ["issue", "create", f"Alice task {i}", "--assignee", "alice"]
                )

            # Create 20 issues for another assignee
            for i in range(20):
                runner.invoke(
                    main, ["issue", "create", f"Bob task {i}", "--assignee", "bob"]
                )

            # Test filtering performance
            result = runner.invoke(main, ["issue", "list", "--assignee", "alice"])
            assert result.exit_code == 0
            assert "20 assigned to alice" in result.output

            result = runner.invoke(main, ["issue", "list", "--assignee", "bob"])
            assert result.exit_code == 0
            assert "20 assigned to bob" in result.output


class TestTeamCollaborationCompatibility:
    """Test compatibility with existing features."""

    def test_assignee_with_milestones(self):
        """Test assignee functionality works with milestones."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            # Create a milestone
            runner.invoke(main, ["milestone", "create", "v1.0"])

            # Create issue with both assignee and milestone
            result = runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    "Feature task",
                    "--assignee",
                    "alice",
                    "--milestone",
                    "v1.0",
                    "--priority",
                    "high",
                ],
            )
            assert result.exit_code == 0
            assert "Assignee: alice" in result.output
            assert "Milestone: v1.0" in result.output

            # Test filtering by assignee shows milestone
            result = runner.invoke(main, ["issue", "list", "--assignee", "alice"])
            assert result.exit_code == 0
            assert "alice" in result.output
            assert "v1.0" in result.output

    def test_assignee_with_labels(self):
        """Test assignee functionality works with labels."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            # Create issue with both assignee and labels
            result = runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    "Bug fix",
                    "--assignee",
                    "alice",
                    "--labels",
                    "bug",
                    "--labels",
                    "urgent",
                ],
            )
            assert result.exit_code == 0
            assert "Assignee: alice" in result.output

            # Verify assignee filtering still works
            result = runner.invoke(main, ["issue", "list", "--assignee", "alice"])
            assert result.exit_code == 0
            assert "alice" in result.output

    def test_assignee_with_comments(self):
        """Test assignee functionality works with comments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            # Create issue with assignee
            result = runner.invoke(
                main, ["issue", "create", "Task with comments", "--assignee", "alice"]
            )
            assert result.exit_code == 0

            # Extract issue ID
            issue_id = result.output.split("ID:")[1].split()[0]

            # Add a comment
            result = runner.invoke(
                main, ["comment", "create", issue_id, "Working on this task"]
            )
            assert result.exit_code == 0

            # Verify assignee filtering still works with comments
            result = runner.invoke(main, ["issue", "list", "--assignee", "alice"])
            assert result.exit_code == 0
            assert "alice" in result.output


# Performance benchmarking helper
class TestTeamCollaborationBenchmarks:
    """Benchmark tests for team collaboration features."""

    def test_assignee_operations_benchmark(self):
        """Benchmark key assignee operations."""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            runner = CliRunner()

            runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--skip-github",
                    "--project-name",
                    "test-project",
                ],
            )

            # Benchmark: Create 100 issues with assignees
            start_time = time.time()
            for i in range(100):
                assignee = f"user{i % 10}"  # 10 different assignees
                runner.invoke(
                    main,
                    ["issue", "create", f"Benchmark task {i}", "--assignee", assignee],
                )
            create_time = time.time() - start_time

            # Benchmark: List all issues
            start_time = time.time()
            result = runner.invoke(main, ["issue", "list"])
            list_time = time.time() - start_time
            assert result.exit_code == 0

            # Benchmark: Filter by assignee
            start_time = time.time()
            result = runner.invoke(main, ["issue", "list", "--assignee", "user0"])
            filter_time = time.time() - start_time
            assert result.exit_code == 0

            # Benchmark: Team workload
            start_time = time.time()
            result = runner.invoke(main, ["team", "workload"])
            workload_time = time.time() - start_time
            assert result.exit_code == 0

            # Performance assertions (reasonable thresholds)
            assert create_time < 30.0  # Creating 100 issues should take < 30 seconds
            assert list_time < 2.0  # Listing 100 issues should take < 2 seconds
            assert filter_time < 1.0  # Filtering should take < 1 second
            assert workload_time < 2.0  # Workload calculation should take < 2 seconds

            print("\nPerformance Benchmark Results:")
            print(f"Create 100 issues: {create_time:.2f}s")
            print(f"List all issues: {list_time:.2f}s")
            print(f"Filter by assignee: {filter_time:.2f}s")
            print(f"Team workload: {workload_time:.2f}s")
