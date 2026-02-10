import subprocess

from roadmap.adapters.git.git import GitIntegration
from roadmap.core.domain import Issue


def test_untracked_files_do_not_block_branch_creation(tmp_path):
    # Initialize a real git repo
    repo_path = tmp_path
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True
    )

    # Create and commit a file so repo has a HEAD
    (repo_path / "README.md").write_text("# Repo")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)

    g = GitIntegration(repo_path=repo_path)

    # Create an untracked file (do NOT add it)
    (repo_path / "untracked.txt").write_text("untracked")

    issue = Issue(id="abc12345", title="Test Issue")

    # Should succeed despite untracked files
    success = g.create_branch_for_issue(issue, checkout=False)
    assert success is True, (
        "create_branch_for_issue should return True despite untracked files"
    )

    # Verify branch name was generated
    branch_name = g.suggest_branch_name(issue)
    assert branch_name is not None, "Branch name should not be None"
    assert "abc12345" in branch_name.lower(), "Branch name should include issue ID"
