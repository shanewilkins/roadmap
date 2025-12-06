"""Integration tests for team onboarding and project detection during init.

Tests the Option A architecture where projects are committed team artifacts
that new team members join rather than creating new projects locally.
"""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


@pytest.fixture
def temp_repo_dir():
    """Create a temporary repository directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestInitProjectDetection:
    """Test project detection during initialization."""

    def test_init_creates_new_project_in_empty_roadmap(self, cli_runner, temp_repo_dir):
        """Test that init creates a new project when .roadmap/projects is empty."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Initialize roadmap
            result = cli_runner.invoke(
                main, ["init", "--project-name", "Test Project", "--yes"]
            )

            assert result.exit_code == 0
            assert "Created main project" in result.output or "✅" in result.output

            # Verify project file was created
            projects_dir = Path(".roadmap/projects")
            assert projects_dir.exists()
            project_files = list(projects_dir.glob("*.md"))
            assert len(project_files) >= 1

    def test_init_joins_existing_project_on_rerun(self, cli_runner, temp_repo_dir):
        """Test that re-running init joins existing project instead of creating new one."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # First init: create project
            result1 = cli_runner.invoke(
                main, ["init", "--project-name", "Alice's Project", "--yes"]
            )
            assert result1.exit_code == 0

            # Get the created project file
            projects_dir = Path(".roadmap/projects")
            project_files_1 = list(projects_dir.glob("*.md"))
            assert len(project_files_1) == 1
            first_project_id = project_files_1[0].stem.split("-")[0]

            # Second init (simulating team member joining)
            result2 = cli_runner.invoke(main, ["init", "--yes"])
            assert result2.exit_code == 0
            assert "Joined existing project" in result2.output

            # Verify no new project was created
            project_files_2 = list(projects_dir.glob("*.md"))
            assert len(project_files_2) == 1
            second_project_id = project_files_2[0].stem.split("-")[0]

            # Verify it's the same project
            assert first_project_id == second_project_id

    def test_init_preserves_existing_milestones_issues(self, cli_runner, temp_repo_dir):
        """Test that init preserves existing milestones and issues."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Initial setup
            result1 = cli_runner.invoke(
                main, ["init", "--project-name", "Team Project", "--yes"]
            )
            assert result1.exit_code == 0

            # Create a milestone and issue
            result_milestone = cli_runner.invoke(
                main, ["milestone", "create", "v1.0", "--description", "First release"]
            )
            assert result_milestone.exit_code == 0

            result_issue = cli_runner.invoke(
                main, ["issue", "create", "Test Issue", "-m", "v1.0"]
            )
            assert result_issue.exit_code == 0

            # Get counts before re-init
            milestones_before = list(Path(".roadmap/milestones").glob("*.md"))
            issues_before = list(Path(".roadmap/issues").glob("*/*.md"))

            # Re-init (shouldn't destroy existing data)
            result2 = cli_runner.invoke(main, ["init", "--yes"])
            assert result2.exit_code == 0

            # Verify data is preserved
            milestones_after = list(Path(".roadmap/milestones").glob("*.md"))
            issues_after = list(Path(".roadmap/issues").glob("*/*.md"))

            assert len(milestones_before) == len(milestones_after)
            assert len(issues_before) == len(issues_after)

    def test_init_with_skip_project_flag(self, cli_runner, temp_repo_dir):
        """Test that --skip-project prevents project creation."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            result = cli_runner.invoke(main, ["init", "--skip-project", "--yes"])

            assert result.exit_code == 0

            # Verify no project was created
            projects_dir = Path(".roadmap/projects")
            if projects_dir.exists():
                project_files = list(projects_dir.glob("*.md"))
                assert len(project_files) == 0

    def test_init_shows_multiple_projects_when_present(self, cli_runner, temp_repo_dir):
        """Test that init shows all existing projects when there are multiple."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Initial setup
            result1 = cli_runner.invoke(
                main, ["init", "--project-name", "Project A", "--yes"]
            )
            assert result1.exit_code == 0

            # Manually create another project by copying and modifying the first
            projects_dir = Path(".roadmap/projects")
            project_files = list(projects_dir.glob("*.md"))
            if project_files:
                first_project = project_files[0]
                content = first_project.read_text()

                # Create a second project by modifying content
                modified_content = content.replace("Project A", "Project B")
                second_project = projects_dir / "second-project.md"
                second_project.write_text(modified_content)

                # Re-init should show both projects
                result2 = cli_runner.invoke(main, ["init", "--yes"])
                assert result2.exit_code == 0
                assert "Joined existing project" in result2.output
                # Should mention multiple projects
                assert "Project" in result2.output

    def test_init_force_recreates_roadmap(self, cli_runner, temp_repo_dir):
        """Test that --force flag recreates roadmap from scratch."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Initial setup
            result1 = cli_runner.invoke(
                main, ["init", "--project-name", "Original Project", "--yes"]
            )
            assert result1.exit_code == 0

            projects_dir = Path(".roadmap/projects")
            original_files = list(projects_dir.glob("*.md"))
            assert len(original_files) >= 1

            # Force re-init
            result2 = cli_runner.invoke(
                main, ["init", "--project-name", "New Project", "--force", "--yes"]
            )
            assert result2.exit_code == 0

            # Should have new project
            new_files = list(projects_dir.glob("*.md"))
            assert len(new_files) >= 1

    def test_init_dry_run_shows_detection(self, cli_runner, temp_repo_dir):
        """Test that dry-run mode shows what would happen."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Initial setup
            result1 = cli_runner.invoke(
                main, ["init", "--project-name", "Test", "--yes"]
            )
            assert result1.exit_code == 0

            # Dry run should show detection
            result2 = cli_runner.invoke(main, ["init", "--dry-run"])
            assert result2.exit_code == 0
            assert (
                "Roadmap already initialized" in result2.output
                or "would" in result2.output.lower()
            )


class TestProjectFileHandling:
    """Test handling of project files during init."""

    def test_project_file_preserved_on_reinit(self, cli_runner, temp_repo_dir):
        """Test that existing project files are preserved across reinits."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Initial setup
            result1 = cli_runner.invoke(
                main, ["init", "--project-name", "Preserved Project", "--yes"]
            )
            assert result1.exit_code == 0

            # Get original project file
            projects_dir = Path(".roadmap/projects")
            original_files = list(projects_dir.glob("*.md"))
            assert len(original_files) >= 1

            # Re-init
            result2 = cli_runner.invoke(main, ["init", "--yes"])
            assert result2.exit_code == 0

            # Verify file still exists with same ID
            new_files = list(projects_dir.glob("*.md"))
            assert len(new_files) == 1
            new_content = new_files[0].read_text()

            # Content should be same (no modification)
            assert "Preserved Project" in new_content

    def test_project_parsing_errors_handled_gracefully(self, cli_runner, temp_repo_dir):
        """Test that corrupted project files don't crash init."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Initial setup
            result1 = cli_runner.invoke(
                main, ["init", "--project-name", "Test", "--yes"]
            )
            assert result1.exit_code == 0

            # Create a corrupted project file
            projects_dir = Path(".roadmap/projects")
            bad_project = projects_dir / "corrupted.md"
            bad_project.write_text("this is not valid yaml frontmatter")

            # Re-init should still work
            result2 = cli_runner.invoke(main, ["init", "--yes"])
            assert result2.exit_code == 0
            # Should not crash, but may show warning about corrupted file

    def test_empty_projects_directory_treated_as_fresh(self, cli_runner, temp_repo_dir):
        """Test that empty .roadmap/projects directory triggers new project creation."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Create empty roadmap structure
            projects_dir = Path(".roadmap/projects")
            projects_dir.mkdir(parents=True, exist_ok=True)

            # Init should create new project since directory is empty
            result = cli_runner.invoke(
                main, ["init", "--project-name", "New Project", "--yes"]
            )
            assert result.exit_code == 0
            assert "Created main project" in result.output or "✅" in result.output

            # Should have created a project file
            project_files = list(projects_dir.glob("*.md"))
            assert len(project_files) == 1


class TestTeamOnboardingScenarios:
    """Test realistic team onboarding scenarios."""

    def test_alice_creates_project_bob_joins(self, cli_runner, temp_repo_dir):
        """Test the Alice creates, Bob joins scenario.

        Scenario:
        1. Alice creates new repo and runs init (creates project)
        2. Alice commits to git
        3. Bob clones repo
        4. Bob runs init (should join Alice's project, not create new one)
        """
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Step 1: Alice initializes
            alice_result = cli_runner.invoke(
                main, ["init", "--project-name", "Alice's Project", "--yes"]
            )
            assert alice_result.exit_code == 0
            assert (
                "Created main project" in alice_result.output
                or "✅" in alice_result.output
            )

            # Get Alice's project ID
            projects_dir = Path(".roadmap/projects")
            alice_project_files = list(projects_dir.glob("*.md"))
            assert len(alice_project_files) == 1
            alice_project_id = alice_project_files[0].stem.split("-")[0]

            # Step 2: Simulate git commit (files already in place)

            # Step 3: Simulate Bob cloning (already in place in isolated filesystem)

            # Step 4: Bob initializes
            bob_result = cli_runner.invoke(main, ["init", "--yes"])
            assert bob_result.exit_code == 0
            assert "Joined existing project" in bob_result.output

            # Verify Bob sees Alice's project
            bob_project_files = list(projects_dir.glob("*.md"))
            assert len(bob_project_files) == 1
            bob_project_id = bob_project_files[0].stem.split("-")[0]

            # Both should have same project ID
            assert alice_project_id == bob_project_id

    def test_multiple_projects_in_monorepo(self, cli_runner, temp_repo_dir):
        """Test handling multiple projects in a single repository."""
        with cli_runner.isolated_filesystem(temp_dir=temp_repo_dir):
            # Initialize roadmap
            result1 = cli_runner.invoke(
                main, ["init", "--project-name", "Project A", "--yes"]
            )
            assert result1.exit_code == 0

            projects_dir = Path(".roadmap/projects")
            projects = list(projects_dir.glob("*.md"))
            assert len(projects) == 1

            # Manually add another project by copying
            first_proj = projects[0]
            content = first_proj.read_text()
            modified = content.replace("Project A", "Project B")
            second_proj = projects_dir / "proj-b.md"
            second_proj.write_text(modified)

            # Re-init should detect both
            result2 = cli_runner.invoke(main, ["init", "--yes"])
            assert result2.exit_code == 0
            assert "Joined existing project" in result2.output
            # Should see multiple projects
            projects_now = list(projects_dir.glob("*.md"))
            assert len(projects_now) == 2
