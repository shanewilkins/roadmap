"""Advanced integration tests for Git hooks with complex scenarios."""

import os
import subprocess
from pathlib import Path

import pytest

from roadmap.adapters.git.git_hooks import GitHookManager
from roadmap.core.domain import IssueType, Priority
from roadmap.infrastructure.coordination.core import RoadmapCore


@pytest.mark.integration
@pytest.mark.slow
class TestGitHooksAdvancedIntegration:
    """Advanced integration tests for git hooks with complex scenarios."""

    @pytest.fixture
    def advanced_repo(self, temp_dir_context):
        """Create a complex git repository for advanced testing."""
        with temp_dir_context() as temp_dir:
            repo_path = Path(temp_dir)
            original_cwd = os.getcwd()

            try:
                # Initialize git repository with multiple branches and complex history
                subprocess.run(["git", "init"], cwd=repo_path, check=True)
                subprocess.run(
                    ["git", "config", "user.name", "Advanced Test"],
                    cwd=repo_path,
                    check=True,
                )
                subprocess.run(
                    ["git", "config", "user.email", "advanced@test.com"],
                    cwd=repo_path,
                    check=True,
                )

                # Create main branch with initial content
                (repo_path / "README.md").write_text("# Advanced Integration Test\\n")
                subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True
                )

                # Create develop branch
                subprocess.run(
                    ["git", "checkout", "-b", "develop"], cwd=repo_path, check=True
                )
                (repo_path / "develop.md").write_text("# Develop branch\\n")
                subprocess.run(["git", "add", "develop.md"], cwd=repo_path, check=True)
                subprocess.run(
                    ["git", "commit", "-m", "Add develop branch"],
                    cwd=repo_path,
                    check=True,
                )
                subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True)

                os.chdir(repo_path)

                core = RoadmapCore()
                core.initialize()

                yield core, repo_path

            finally:
                os.chdir(original_cwd)

    def test_multi_branch_workflow_integration(self, advanced_repo):
        """Test git hooks with complex multi-branch workflows."""
        core, repo_path = advanced_repo

        # Create multiple issues for different workflow stages
        workflow_issues = []
        for i, (title, stage) in enumerate(
            [
                ("Epic Feature Implementation", "feature"),
                ("Critical Bug Investigation", "bugfix"),
                ("Performance Optimization", "enhancement"),
                ("Documentation Update", "docs"),
            ]
        ):
            core.issues.create(
                title=title,
                priority=Priority.HIGH if i < 2 else Priority.MEDIUM,
                issue_type=IssueType.FEATURE if stage == "feature" else IssueType.BUG,
            )
            issues = core.issues.list()
            workflow_issues.append((issues[-1].id, stage))

        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()

        # Create complex branching workflow
        for issue_id, stage in workflow_issues:
            # Create feature branch
            branch_name = f"{stage}/{issue_id}-{stage}-work"
            subprocess.run(
                ["git", "checkout", "-b", branch_name], cwd=repo_path, check=True
            )

            # Make multiple commits with different patterns
            for j in range(3):
                work_file = repo_path / f"{stage}_{j}.py"
                work_file.write_text(
                    f"# {stage.capitalize()} work {j+1}\\n# Issue: {issue_id}\\n"
                )
                subprocess.run(
                    ["git", "add", f"{stage}_{j}.py"], cwd=repo_path, check=True
                )

                if j == 2:  # Final commit
                    commit_msg = (
                        f"{issue_id}: Complete {stage} work [closes roadmap:{issue_id}]"
                    )
                else:
                    commit_msg = f"{issue_id}: {stage.capitalize()} work part {j+1} [progress:{(j+1)*30}%]"

                subprocess.run(
                    ["git", "commit", "-m", commit_msg], cwd=repo_path, check=True
                )

            # Merge back to develop
            subprocess.run(["git", "checkout", "develop"], cwd=repo_path, check=True)
            subprocess.run(
                [
                    "git",
                    "merge",
                    "--no-ff",
                    branch_name,
                    "-m",
                    f"Merge {branch_name} into develop",
                ],
                cwd=repo_path,
                check=True,
            )

        # Final merge to master
        subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "merge", "--no-ff", "develop", "-m", "Merge develop into master"],
            cwd=repo_path,
            check=True,
        )

        # Verify complex workflow completed without hook errors
        result = subprocess.run(
            ["git", "log", "--oneline", "--graph"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have complex merge graph
        assert len(result.stdout.split("\n")) > 15  # Many commits from complex workflow

    def test_rebase_and_squash_integration(self, advanced_repo):
        """Test git hooks with rebase and squash operations."""
        core, repo_path = advanced_repo

        # Create issue for rebase testing
        core.issues.create(
            title="Rebase Integration Test",
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE,
        )

        issues = core.issues.list()
        issue_id = issues[0].id

        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()

        # Create feature branch with multiple commits
        feature_branch = f"feature/{issue_id}-rebase-test"
        subprocess.run(
            ["git", "checkout", "-b", feature_branch], cwd=repo_path, check=True
        )

        # Make several small commits
        for i in range(4):
            rebase_file = repo_path / f"rebase_file_{i}.txt"
            rebase_file.write_text(f"Rebase test content {i}\\n")
            subprocess.run(
                ["git", "add", f"rebase_file_{i}.txt"], cwd=repo_path, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"{issue_id}: Rebase test commit {i+1}"],
                cwd=repo_path,
                check=True,
            )

        # Test interactive rebase (squash commits)
        # Note: This would normally be interactive, but we can test the hook behavior
        subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True)

        # Simulate squash merge
        subprocess.run(
            ["git", "merge", "--squash", feature_branch], cwd=repo_path, check=True
        )
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"{issue_id}: Squashed rebase test commits [closes roadmap:{issue_id}]",
            ],
            cwd=repo_path,
            check=True,
        )

        # Verify squash merge worked with hooks
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        squash_commits = [
            line for line in result.stdout.split("\n") if "Squashed rebase test" in line
        ]
        assert len(squash_commits) == 1

    def test_cherry_pick_integration(self, advanced_repo):
        """Test git hooks with cherry-pick operations."""
        core, repo_path = advanced_repo

        # Create issues for cherry-pick testing
        core.issues.create(
            title="Critical Hotfix", priority=Priority.HIGH, issue_type=IssueType.BUG
        )

        issues = core.issues.list()
        hotfix_id = issues[0].id

        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()

        # Create hotfix on develop branch
        subprocess.run(["git", "checkout", "develop"], cwd=repo_path, check=True)

        hotfix_file = repo_path / "hotfix.py"
        hotfix_file.write_text(f"# Critical hotfix\\n# Issue: {hotfix_id}\\n")
        subprocess.run(["git", "add", "hotfix.py"], cwd=repo_path, check=True)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"{hotfix_id}: Critical hotfix implementation [closes roadmap:{hotfix_id}]",
            ],
            cwd=repo_path,
            check=True,
        )

        # Get the commit hash for cherry-picking
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        hotfix_commit = result.stdout.strip()

        # Cherry-pick to master
        subprocess.run(["git", "checkout", "master"], cwd=repo_path, check=True)
        subprocess.run(["git", "cherry-pick", hotfix_commit], cwd=repo_path, check=True)

        # Verify cherry-pick worked with hooks
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        hotfix_commits = [
            line for line in result.stdout.split("\n") if "Critical hotfix" in line
        ]
        assert len(hotfix_commits) >= 1

    def test_submodule_integration(self, advanced_repo):
        """Test git hooks behavior with submodules."""
        core, repo_path = advanced_repo

        # Install hooks in main repo
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()

        # Create issue for submodule work
        core.issues.create(
            title="Submodule Integration",
            priority=Priority.MEDIUM,
            issue_type=IssueType.OTHER,
        )

        issues = core.issues.list()
        issue_id = issues[0].id

        # Create a fake submodule directory structure
        submodule_dir = repo_path / "vendor" / "library"
        submodule_dir.mkdir(parents=True)

        # Add submodule content
        (submodule_dir / "library.py").write_text("# External library\\n")
        subprocess.run(["git", "add", "vendor/"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"{issue_id}: Add vendor library [progress:50%]"],
            cwd=repo_path,
            check=True,
        )

        # Update submodule
        (submodule_dir / "update.py").write_text("# Library update\\n")
        subprocess.run(["git", "add", "vendor/"], cwd=repo_path, check=True)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"{issue_id}: Update vendor library [closes roadmap:{issue_id}]",
            ],
            cwd=repo_path,
            check=True,
        )

        # Verify submodule commits worked with hooks
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        vendor_commits = [
            line for line in result.stdout.split("\n") if "vendor library" in line
        ]
        assert len(vendor_commits) == 2
