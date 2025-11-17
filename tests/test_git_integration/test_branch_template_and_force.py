from roadmap.git_integration import GitIntegration
from roadmap.models import Issue, RoadmapConfig


def make_issue():
    return Issue(id="abc12345", title="Test Issue", priority="medium", status="todo")


def test_suggest_branch_uses_template(tmp_path):
    cfg = RoadmapConfig()
    cfg.defaults["branch_name_template"] = "feat/{id}/{slug}"

    g = GitIntegration(repo_path=tmp_path, config=cfg)
    issue = make_issue()
    name = g.suggest_branch_name(issue)
    assert name.startswith("feat/abc12345/")


def test_create_branch_allows_force_on_dirty_tree(tmp_path, monkeypatch):
    g = GitIntegration(repo_path=tmp_path)
    (tmp_path / ".git").mkdir()
    g._git_dir = tmp_path / ".git"

    # Simulate dirty status, but allow branch creation when force=True
    def run_git(args, cwd=None):
        if args[:2] == ["status", "--porcelain"]:
            return " M modified.py"
        if args[:3] == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return "main"
        if args[:3] == ["checkout", "-b", "feature/abc12345-test-issue"]:
            return "Switched to branch 'feature/abc12345-test-issue'"
        return ""

    monkeypatch.setattr(g, "_run_git_command", run_git)
    issue = make_issue()
    success = g.create_branch_for_issue(issue, checkout=True, force=True)
    assert success is True
