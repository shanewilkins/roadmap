import subprocess
from pathlib import Path

from roadmap.git_integration import GitIntegration
from roadmap.models import Issue


def test_untracked_files_do_not_block_branch_creation(tmp_path):
    # Initialize a real git repo
    repo_path = tmp_path
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)

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
    assert success is True

    # Branch should exist
    branch_name = g.suggest_branch_name(issue)
    exists = g._run_git_command(["rev-parse", "--verify", branch_name])
    assert exists
