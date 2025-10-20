from pathlib import Path
from unittest.mock import patch, Mock
from roadmap.git_integration import GitIntegration
from roadmap.models import Issue


def make_issue():
    i = Issue(id='abc12345', title='Test Issue', priority='medium', status='todo')
    return i


def test_create_branch_fails_on_dirty_tree(tmp_path, monkeypatch):
    g = GitIntegration(repo_path=tmp_path)
    # Simulate a git repository by setting a .git directory
    (tmp_path / '.git').mkdir()
    g._git_dir = tmp_path / '.git'
    # Mock _run_git_command to simulate dirty status
    def run_git(args, cwd=None):
        if args[:2] == ["status", "--porcelain"]:
            return " M modified_file.py"
        return ""

    monkeypatch.setattr(g, '_run_git_command', run_git)

    issue = make_issue()
    success = g.create_branch_for_issue(issue)
    assert success is False


def test_create_branch_checks_out_existing_branch(tmp_path, monkeypatch):
    g = GitIntegration(repo_path=tmp_path)
    # Simulate a git repository by setting a .git directory
    (tmp_path / '.git').mkdir()
    g._git_dir = tmp_path / '.git'

    # Simulate git repo
    def run_git(args, cwd=None):
        if args[:2] == ["status", "--porcelain"]:
            return ""
        if args[:3] == ["rev-parse", "--verify"]:
            # Indicate branch exists
            return "refs/heads/feature/abc12345-test-issue"
        if args[:2] == ["checkout", "feature/abc12345-test-issue"] or args[:3] == ["checkout", "-b", "feature/abc12345-test-issue"]:
            return "Switched to branch 'feature/abc12345-test-issue'"
        return ""

    monkeypatch.setattr(g, '_run_git_command', run_git)

    issue = make_issue()
    success = g.create_branch_for_issue(issue, checkout=True)
    assert success is True
