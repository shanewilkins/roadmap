import subprocess

from roadmap.adapters.git.git import GitIntegration
from roadmap.core.domain import Issue, Priority, Status


# Simple config class for testing (RoadmapConfig moved out of roadmap.models)
class RoadmapConfig:
    def __init__(self):
        self.defaults = {}


def make_issue():
    return Issue(
        id="abc12345", title="Test Issue", priority=Priority.MEDIUM, status=Status.TODO
    )


def test_suggest_branch_uses_template(tmp_path):
    cfg = RoadmapConfig()
    cfg.defaults["branch_name_template"] = "feat/{id}/{slug}"

    g = GitIntegration(repo_path=tmp_path, config=cfg)
    issue = make_issue()
    name = g.suggest_branch_name(issue)
    assert name.startswith("feat/abc12345/")


def test_create_branch_allows_force_on_dirty_tree(tmp_path):
    """Test that create_branch can create branch with force=True even on dirty tree."""
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

    # Create a modification (staged)
    (tmp_path / "modified.py").write_text("code")
    subprocess.run(["git", "add", "modified.py"], cwd=tmp_path, check=True)

    g = GitIntegration(repo_path=tmp_path)
    issue = make_issue()
    # Should succeed with force=True despite dirty tree
    success = g.create_branch_for_issue(issue, checkout=True, force=True)
    assert success is True
