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


def test_create_branch_fails_on_dirty_tree(git_repo_factory):
    """Test that create_branch fails when working tree has uncommitted changes."""
    # Factory creates a real git repo with initial commit
    repo_path = git_repo_factory.create_repo()

    # Now create a modification (but don't add/commit it)
    (repo_path / "modified_file.py").write_text("some code")
    subprocess.run(["git", "add", "modified_file.py"], cwd=repo_path, check=True)

    g = GitIntegration(repo_path=repo_path)

    issue = make_issue()
    success = g.create_branch_for_issue(issue)
    # Should fail because working tree is dirty (has staged changes)
    assert success is False


def test_create_branch_checks_out_existing_branch(git_repo_factory):
    """Test that create_branch can checkout an existing branch."""
    # Factory creates a real git repo with initial commit on main
    repo_path = git_repo_factory.create_repo()

    # Create a feature branch from main
    subprocess.run(
        ["git", "checkout", "-b", "feature/abc12345-test-issue"],
        cwd=repo_path,
        check=True,
    )
    # Switch back to main
    subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True)

    g = GitIntegration(repo_path=repo_path)

    issue = make_issue()
    # Should checkout the existing branch successfully
    success = g.create_branch_for_issue(issue, checkout=True)
    assert success is True

    # Verify we're on the feature branch
    current_branch = g.get_current_branch()
    assert current_branch is not None
    assert "abc12345" in current_branch.name
