import subprocess

from roadmap.adapters.git.git import GitIntegration
from roadmap.core.domain import Issue, Priority, Status


# Simple config class for testing
class RoadmapConfig:
    def __init__(self):
        self.defaults = {}


def make_issue():
    i = Issue(
        id="abc12345", title="Test Issue", priority=Priority.MEDIUM, status=Status.TODO
    )
    return i


def test_create_branch_fails_on_dirty_tree(tmp_path):
    """Test that create_branch fails when working tree has uncommitted changes."""
    # Initialize a real git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create and commit a file so repo has a HEAD
    (tmp_path / "README.md").write_text("# Repo")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Now create a modification (but don't add/commit it)
    (tmp_path / "modified_file.py").write_text("some code")
    subprocess.run(["git", "add", "modified_file.py"], cwd=tmp_path, check=True)

    g = GitIntegration(repo_path=tmp_path)

    issue = make_issue()
    success = g.create_branch_for_issue(issue)
    # Should fail because working tree is dirty (has staged changes)
    assert success is False


def test_create_branch_checks_out_existing_branch(tmp_path):
    """Test that create_branch can checkout an existing branch."""
    # Initialize a real git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create and commit a file so repo has a HEAD
    (tmp_path / "README.md").write_text("# Repo")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Create a branch manually
    subprocess.run(
        ["git", "checkout", "-b", "feature/abc12345-test-issue"],
        cwd=tmp_path,
        check=True,
    )
    # Switch back to main
    subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path, check=True)

    g = GitIntegration(repo_path=tmp_path)

    issue = make_issue()
    # Should checkout the existing branch successfully
    success = g.create_branch_for_issue(issue, checkout=True)
    assert success is True

    # Verify we're on the feature branch
    current_branch = g.get_current_branch()
    assert current_branch is not None
    assert "abc12345" in current_branch.name
