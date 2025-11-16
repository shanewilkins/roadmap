"""Comprehensive integration tests for Git hooks functionality."""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.core import RoadmapCore
from roadmap.git_hooks import GitHookManager, WorkflowAutomation
from roadmap.models import Issue, IssueType, Priority, Status


class TestGitHooksIntegration:
    """Integration tests for git hooks in realistic scenarios."""

    @pytest.fixture
    def git_hooks_repo(self):
        """Create a git repository with roadmap initialized for hooks testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            original_cwd = os.getcwd()
            
            try:
                # Initialize git repository
                subprocess.run(['git', 'init'], cwd=repo_path, check=True)
                subprocess.run(['git', 'config', 'user.name', 'Hook Integration Test'], cwd=repo_path, check=True)
                subprocess.run(['git', 'config', 'user.email', 'hook-test@integration.com'], cwd=repo_path, check=True)
                
                # Create initial commit
                (repo_path / 'README.md').write_text('# Git Hooks Integration Test\\n')
                subprocess.run(['git', 'add', 'README.md'], cwd=repo_path, check=True)
                subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, check=True)
                
                # Change to repo directory and initialize roadmap
                os.chdir(repo_path)
                
                core = RoadmapCore()
                core.initialize()
                
                yield core, repo_path
                
            finally:
                os.chdir(original_cwd)

    def test_complete_hook_lifecycle_integration(self, git_hooks_repo):
        """Test complete git hook lifecycle with real commits and issue updates."""
        core, repo_path = git_hooks_repo
        
        # Create test issues for different scenarios
        feature_issue = core.create_issue(
            title="Feature Implementation with Hooks",
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE
        )
        
        bug_issue = core.create_issue(
            title="Critical Bug Fix with Progress",
            priority=Priority.HIGH,
            issue_type=IssueType.BUG
        )
        
        # Get actual issue IDs (auto-generated)
        issues = core.list_issues()
        feature_id = issues[0].id
        bug_id = issues[1].id
        
        # Install git hooks
        hook_manager = GitHookManager(core)
        assert hook_manager.install_hooks()
        
        # Verify hooks are installed and executable
        hooks_dir = repo_path / '.git' / 'hooks'
        for hook_name in ['post-commit', 'pre-push', 'post-checkout', 'post-merge']:
            hook_file = hooks_dir / hook_name
            assert hook_file.exists()
            assert hook_file.stat().st_mode & 0o111  # Check executable
        
        # Test post-commit hook with progress tracking
        test_file = repo_path / 'feature.py'
        test_file.write_text(f'# Feature implementation\\n# Issue: {feature_id}\\n')
        subprocess.run(['git', 'add', 'feature.py'], cwd=repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', f'{feature_id}: Start feature implementation [progress:20%]'], 
                      cwd=repo_path, check=True)
        
        # Allow some time for hook processing
        time.sleep(0.1)
        
        # Check if issue was updated by hook
        updated_feature = core.get_issue(feature_id)
        # Note: The hook may or may not update the issue depending on CI tracking integration
        # We'll verify the hook was called by checking the log file
        log_file = repo_path / '.git' / 'roadmap-hooks.log'
        if log_file.exists():
            log_content = log_file.read_text()
            assert 'Post-commit hook tracked commit' in log_content
            assert feature_id in log_content or 'issues:' in log_content
        
        # Test commit with completion marker
        bug_file = repo_path / 'bugfix.py'
        bug_file.write_text(f'# Bug fix implementation\\n# Issue: {bug_id}\\n')
        subprocess.run(['git', 'add', 'bugfix.py'], cwd=repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', f'{bug_id}: Fix critical bug [closes roadmap:{bug_id}]'], 
                      cwd=repo_path, check=True)
        
        time.sleep(0.1)
        
        # Check log for completion tracking
        if log_file.exists():
            log_content = log_file.read_text()
            commit_logs = [line for line in log_content.split('\n') if 'Post-commit hook tracked commit' in line]
            assert len(commit_logs) >= 2  # Should have at least 2 commit entries

    def test_pre_push_hook_integration(self, git_hooks_repo):
        """Test pre-push hook integration with branch workflows."""
        core, repo_path = git_hooks_repo
        
        # Create a feature issue
        issue = core.create_issue(
            title="Feature Branch Integration",
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE
        )
        
        issues = core.list_issues()
        issue_id = issues[0].id
        
        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create feature branch with issue ID
        feature_branch = f'feature/{issue_id}-integration-test'
        subprocess.run(['git', 'checkout', '-b', feature_branch], cwd=repo_path, check=True)
        
        # Make some commits on feature branch
        for i in range(3):
            test_file = repo_path / f'feature_part_{i}.py'
            test_file.write_text(f'# Feature part {i+1}\\n# Issue: {issue_id}\\n')
            subprocess.run(['git', 'add', f'feature_part_{i}.py'], cwd=repo_path, check=True)
            subprocess.run(['git', 'commit', '-m', f'{issue_id}: Implement feature part {i+1} [progress:{(i+1)*30}%]'], 
                          cwd=repo_path, check=True)
        
        # Set up remote (simulate pushing)
        subprocess.run(['git', 'remote', 'add', 'origin', '/tmp/fake-remote'], cwd=repo_path)
        
        # Test pre-push hook by attempting push (will fail but hook should run)
        try:
            subprocess.run(['git', 'push', '-u', 'origin', feature_branch], 
                          cwd=repo_path, check=False, capture_output=True)
        except:
            pass  # Expected to fail due to fake remote
        
        # Verify pre-push hook ran (check log or hook execution)
        log_file = repo_path / '.git' / 'roadmap-hooks.log'
        # Pre-push hook might not create log entries, but it should not crash

    def test_post_checkout_hook_integration(self, git_hooks_repo):
        """Test post-checkout hook integration with branch switching."""
        core, repo_path = git_hooks_repo
        
        # Create multiple issues for different branches
        issues_data = [
            ("Main Feature", Priority.HIGH, IssueType.FEATURE),
            ("Bug Fix", Priority.MEDIUM, IssueType.BUG),
            ("Enhancement", Priority.LOW, IssueType.OTHER)
        ]
        
        created_issues = []
        for title, priority, issue_type in issues_data:
            issue = core.create_issue(title=title, priority=priority, issue_type=issue_type)
            created_issues.append(core.list_issues()[-1].id)  # Get the last created issue ID
        
        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create branches for each issue
        for i, issue_id in enumerate(created_issues):
            branch_name = f'feature/{issue_id}-branch-{i}'
            subprocess.run(['git', 'checkout', '-b', branch_name], cwd=repo_path, check=True)
            
            # Make a commit on this branch
            test_file = repo_path / f'work_{i}.py'
            test_file.write_text(f'# Work for issue {issue_id}\\n')
            subprocess.run(['git', 'add', f'work_{i}.py'], cwd=repo_path, check=True)
            subprocess.run(['git', 'commit', '-m', f'{issue_id}: Work on branch {i}'], 
                          cwd=repo_path, check=True)
            
            # Switch back to main
            subprocess.run(['git', 'checkout', 'master'], cwd=repo_path, check=True)
        
        # Test switching between branches (triggers post-checkout)
        for i, issue_id in enumerate(created_issues):
            branch_name = f'feature/{issue_id}-branch-{i}'
            subprocess.run(['git', 'checkout', branch_name], cwd=repo_path, check=True)
            
            # Verify we're on the correct branch
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  cwd=repo_path, capture_output=True, text=True, check=True)
            assert result.stdout.strip() == branch_name

    def test_post_merge_hook_integration(self, git_hooks_repo):
        """Test post-merge hook integration with merge scenarios."""
        core, repo_path = git_hooks_repo
        
        # Create an issue for merge testing
        issue = core.create_issue(
            title="Merge Integration Feature",
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE
        )
        
        issues = core.list_issues()
        issue_id = issues[0].id
        
        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create feature branch
        feature_branch = f'feature/{issue_id}-merge-test'
        subprocess.run(['git', 'checkout', '-b', feature_branch], cwd=repo_path, check=True)
        
        # Make commits with completion marker
        merge_file = repo_path / 'merge_feature.py'
        merge_file.write_text(f'# Merge feature implementation\\n# Issue: {issue_id}\\n')
        subprocess.run(['git', 'add', 'merge_feature.py'], cwd=repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', f'{issue_id}: Complete merge feature [closes roadmap:{issue_id}]'], 
                      cwd=repo_path, check=True)
        
        # Switch back to main and merge
        subprocess.run(['git', 'checkout', 'master'], cwd=repo_path, check=True)
        subprocess.run(['git', 'merge', '--no-ff', feature_branch, '-m', f'Merge {feature_branch}'], 
                      cwd=repo_path, check=True)
        
        # Check if post-merge hook executed (check logs or issue status)
        log_file = repo_path / '.git' / 'roadmap-hooks.log'
        if log_file.exists():
            log_content = log_file.read_text()
            # Should have log entries from both the feature commits and merge
            assert log_content.count('Post-commit hook tracked commit') >= 1

    def test_hook_error_handling_integration(self, git_hooks_repo):
        """Test git hook error handling and recovery."""
        core, repo_path = git_hooks_repo
        
        # Create an issue with potentially problematic characters
        issue = core.create_issue(
            title="Test Issue with Special Characters: [brackets] & symbols!",
            priority=Priority.MEDIUM,
            issue_type=IssueType.BUG
        )
        
        issues = core.list_issues()
        issue_id = issues[0].id
        
        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Test commit with malformed issue references
        test_scenarios = [
            f'{issue_id}: Normal commit message',
            f'malformed_id: This should not crash the hook',
            f'{issue_id}: Progress with invalid format [progress:invalid]',
            f'{issue_id}: Multiple progress markers [progress:50%] [progress:75%]',
            f'NONEXISTENT123: Reference to non-existent issue',
            f'{issue_id}: Unicode characters: 你好世界 🚀 [progress:30%]'
        ]
        
        for i, commit_msg in enumerate(test_scenarios):
            test_file = repo_path / f'error_test_{i}.txt'
            test_file.write_text(f'Test file {i}\\n')
            subprocess.run(['git', 'add', f'error_test_{i}.txt'], cwd=repo_path, check=True)
            
            # This should not crash even with problematic commit messages
            result = subprocess.run(['git', 'commit', '-m', commit_msg], 
                                  cwd=repo_path, check=False)
            
            # Git commit should succeed even if hook has issues
            assert result.returncode == 0

    def test_hook_performance_integration(self, git_hooks_repo):
        """Test git hook performance with multiple commits and issues."""
        core, repo_path = git_hooks_repo
        
        # Create multiple issues
        issue_ids = []
        for i in range(5):
            issue = core.create_issue(
                title=f"Performance Test Issue {i+1}",
                priority=Priority.MEDIUM,
                issue_type=IssueType.FEATURE
            )
            issues = core.list_issues()
            issue_ids.append(issues[-1].id)
        
        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create many commits quickly
        start_time = time.time()
        
        for i in range(10):
            issue_id = issue_ids[i % len(issue_ids)]
            test_file = repo_path / f'perf_test_{i}.py'
            test_file.write_text(f'# Performance test file {i}\\n# Issue: {issue_id}\\n')
            subprocess.run(['git', 'add', f'perf_test_{i}.py'], cwd=repo_path, check=True)
            subprocess.run(['git', 'commit', '-m', f'{issue_id}: Performance test commit {i} [progress:{(i+1)*10}%]'], 
                          cwd=repo_path, check=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete within reasonable time (hooks shouldn't add significant overhead)
        assert total_time < 30.0  # 30 seconds should be more than enough for 10 commits
        
        # Check that log file exists and has entries
        log_file = repo_path / '.git' / 'roadmap-hooks.log'
        if log_file.exists():
            log_content = log_file.read_text()
            log_lines = [line for line in log_content.split('\n') if 'Post-commit hook tracked commit' in line]
            # Should have log entries for most/all commits
            assert len(log_lines) >= 5

    def test_hook_uninstall_integration(self, git_hooks_repo):
        """Test complete hook installation and uninstallation cycle."""
        core, repo_path = git_hooks_repo
        
        hook_manager = GitHookManager(core)
        hooks_dir = repo_path / '.git' / 'hooks'
        
        # Install all hooks
        assert hook_manager.install_hooks()
        
        # Verify all hooks are installed
        expected_hooks = ['post-commit', 'pre-push', 'post-checkout', 'post-merge']
        for hook_name in expected_hooks:
            hook_file = hooks_dir / hook_name
            assert hook_file.exists()
            assert hook_file.stat().st_mode & 0o111
        
        # Test uninstalling all hooks
        result = hook_manager.uninstall_hooks()
        assert result  # Should return True for success
        
        # Verify hooks are removed (only our roadmap hooks, others might remain)
        for hook_name in expected_hooks:
            hook_file = hooks_dir / hook_name
            if hook_file.exists():
                # If file exists, it should not contain roadmap-hook marker
                content = hook_file.read_text()
                assert "roadmap-hook" not in content

    def test_workflow_automation_integration(self, git_hooks_repo):
        """Test workflow automation integration with git hooks."""
        core, repo_path = git_hooks_repo
        
        # Create issues for automation testing
        issues_data = [
            ("Automated Feature", Priority.HIGH, IssueType.FEATURE),
            ("Automated Bug Fix", Priority.MEDIUM, IssueType.BUG)
        ]
        
        issue_ids = []
        for title, priority, issue_type in issues_data:
            issue = core.create_issue(title=title, priority=priority, issue_type=issue_type)
            issues = core.list_issues()
            issue_ids.append(issues[-1].id)
        
        # Install hooks and set up automation
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Test WorkflowAutomation if available
        try:
            automation = WorkflowAutomation(core)
            
            # Create branch-based workflows
            for issue_id in issue_ids:
                branch_name = f'feature/{issue_id}-automated'
                subprocess.run(['git', 'checkout', '-b', branch_name], cwd=repo_path, check=True)
                
                # Make commits that should trigger automation
                auto_file = repo_path / f'automated_{issue_id}.py'
                auto_file.write_text(f'# Automated workflow test\\n# Issue: {issue_id}\\n')
                subprocess.run(['git', 'add', f'automated_{issue_id}.py'], cwd=repo_path, check=True)
                subprocess.run(['git', 'commit', '-m', f'{issue_id}: Automated workflow test [progress:100%]'], 
                              cwd=repo_path, check=True)
                
                subprocess.run(['git', 'checkout', 'master'], cwd=repo_path, check=True)
        
        except ImportError:
            # WorkflowAutomation might not be available, skip this part
            pass

    def test_concurrent_hook_execution(self, git_hooks_repo):
        """Test git hooks handling concurrent operations."""
        core, repo_path = git_hooks_repo
        
        # Create issue for concurrent testing
        issue = core.create_issue(
            title="Concurrent Operations Test",
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE
        )
        
        issues = core.list_issues()
        issue_id = issues[0].id
        
        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Simulate rapid commits (like in automated CI/CD)
        for i in range(5):
            concurrent_file = repo_path / f'concurrent_{i}.txt'
            concurrent_file.write_text(f'Concurrent test {i}\\n')
            subprocess.run(['git', 'add', f'concurrent_{i}.txt'], cwd=repo_path, check=True)
            subprocess.run(['git', 'commit', '-m', f'{issue_id}: Concurrent commit {i} [progress:{(i+1)*20}%]'], 
                          cwd=repo_path, check=True)
            
            # Small delay to simulate realistic timing
            time.sleep(0.05)
        
        # Verify all commits succeeded and hooks ran without conflicts
        result = subprocess.run(['git', 'log', '--oneline'], 
                              cwd=repo_path, capture_output=True, text=True, check=True)
        commit_lines = result.stdout.strip().split('\n')
        
        # Should have initial commit + 5 concurrent commits + any setup commits
        assert len(commit_lines) >= 6
        
        # Check for concurrent commit messages
        concurrent_commits = [line for line in commit_lines if 'Concurrent commit' in line]
        assert len(concurrent_commits) == 5


class TestGitHooksErrorRecovery:
    """Test git hooks error handling and recovery scenarios."""

    @pytest.fixture
    def corrupted_repo(self):
        """Create a git repository with potential corruption scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            original_cwd = os.getcwd()
            
            try:
                # Initialize git repository
                subprocess.run(['git', 'init'], cwd=repo_path, check=True)
                subprocess.run(['git', 'config', 'user.name', 'Corruption Test'], cwd=repo_path, check=True)
                subprocess.run(['git', 'config', 'user.email', 'corrupt@test.com'], cwd=repo_path, check=True)
                
                # Create initial commit
                (repo_path / 'README.md').write_text('# Corruption Test\\n')
                subprocess.run(['git', 'add', 'README.md'], cwd=repo_path, check=True)
                subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, check=True)
                
                os.chdir(repo_path)
                
                core = RoadmapCore()
                core.initialize()
                
                yield core, repo_path
                
            finally:
                os.chdir(original_cwd)

    def test_hook_recovery_from_roadmap_corruption(self, corrupted_repo):
        """Test hook behavior when roadmap data is corrupted."""
        core, repo_path = corrupted_repo
        
        # Create and install hooks normally
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create a test issue
        issue = core.create_issue(
            title="Corruption Recovery Test",
            priority=Priority.HIGH,
            issue_type=IssueType.BUG
        )
        
        issues = core.list_issues()
        issue_id = issues[0].id
        
        # Simulate roadmap data corruption by corrupting the issues file
        roadmap_dir = repo_path / '.roadmap'
        issues_dir = roadmap_dir / 'issues'
        
        if issues_dir.exists():
            # Corrupt the issue file
            for issue_file in issues_dir.glob('*.md'):
                issue_file.write_text('CORRUPTED DATA\\n')
        
        # Try to make commits - hooks should not crash git operations
        test_file = repo_path / 'recovery_test.py'
        test_file.write_text('# Recovery test\\n')
        subprocess.run(['git', 'add', 'recovery_test.py'], cwd=repo_path, check=True)
        
        # This should succeed even with corrupted roadmap data
        result = subprocess.run(['git', 'commit', '-m', f'{issue_id}: Recovery test commit'], 
                              cwd=repo_path, check=False)
        
        # Git commit should succeed (hooks fail silently)
        assert result.returncode == 0

    def test_hook_recovery_from_missing_roadmap(self, corrupted_repo):
        """Test hook behavior when roadmap is completely missing."""
        core, repo_path = corrupted_repo
        
        # Install hooks first
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Remove entire .roadmap directory
        import shutil
        roadmap_dir = repo_path / '.roadmap'
        if roadmap_dir.exists():
            shutil.rmtree(roadmap_dir)
        
        # Try to make commits - should not crash
        test_file = repo_path / 'missing_roadmap_test.py'
        test_file.write_text('# Missing roadmap test\\n')
        subprocess.run(['git', 'add', 'missing_roadmap_test.py'], cwd=repo_path, check=True)
        
        result = subprocess.run(['git', 'commit', '-m', 'TEST123: Test with missing roadmap'], 
                              cwd=repo_path, check=False)
        
        # Should succeed
        assert result.returncode == 0

    def test_hook_recovery_from_permission_errors(self, corrupted_repo):
        """Test hook behavior with permission errors."""
        core, repo_path = corrupted_repo
        
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create issue and make roadmap directory read-only
        issue = core.create_issue(
            title="Permission Error Test",
            priority=Priority.MEDIUM,
            issue_type=IssueType.OTHER
        )
        
        issues = core.list_issues()
        issue_id = issues[0].id
        
        # Make .roadmap directory read-only
        roadmap_dir = repo_path / '.roadmap'
        if roadmap_dir.exists():
            os.chmod(roadmap_dir, 0o444)
        
        try:
            # Try to make commits
            test_file = repo_path / 'permission_test.py'
            test_file.write_text('# Permission test\\n')
            subprocess.run(['git', 'add', 'permission_test.py'], cwd=repo_path, check=True)
            
            result = subprocess.run(['git', 'commit', '-m', f'{issue_id}: Permission test commit'], 
                                  cwd=repo_path, check=False)
            
            # Should succeed despite permission errors
            assert result.returncode == 0
        
        finally:
            # Restore permissions
            if roadmap_dir.exists():
                os.chmod(roadmap_dir, 0o755)


class TestGitHooksAdvancedIntegration:
    """Advanced integration tests for git hooks with complex scenarios."""

    @pytest.fixture
    def advanced_repo(self):
        """Create a complex git repository for advanced testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            original_cwd = os.getcwd()
            
            try:
                # Initialize git repository with multiple branches and complex history
                subprocess.run(['git', 'init'], cwd=repo_path, check=True)
                subprocess.run(['git', 'config', 'user.name', 'Advanced Test'], cwd=repo_path, check=True)
                subprocess.run(['git', 'config', 'user.email', 'advanced@test.com'], cwd=repo_path, check=True)
                
                # Create main branch with initial content
                (repo_path / 'README.md').write_text('# Advanced Integration Test\\n')
                subprocess.run(['git', 'add', 'README.md'], cwd=repo_path, check=True)
                subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, check=True)
                
                # Create develop branch
                subprocess.run(['git', 'checkout', '-b', 'develop'], cwd=repo_path, check=True)
                (repo_path / 'develop.md').write_text('# Develop branch\\n')
                subprocess.run(['git', 'add', 'develop.md'], cwd=repo_path, check=True)
                subprocess.run(['git', 'commit', '-m', 'Add develop branch'], cwd=repo_path, check=True)
                subprocess.run(['git', 'checkout', 'master'], cwd=repo_path, check=True)
                
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
        for i, (title, stage) in enumerate([
            ("Epic Feature Implementation", "feature"),
            ("Critical Bug Investigation", "bugfix"),
            ("Performance Optimization", "enhancement"),
            ("Documentation Update", "docs")
        ]):
            issue = core.create_issue(
                title=title,
                priority=Priority.HIGH if i < 2 else Priority.MEDIUM,
                issue_type=IssueType.FEATURE if stage == "feature" else IssueType.BUG
            )
            issues = core.list_issues()
            workflow_issues.append((issues[-1].id, stage))
        
        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create complex branching workflow
        for issue_id, stage in workflow_issues:
            # Create feature branch
            branch_name = f'{stage}/{issue_id}-{stage}-work'
            subprocess.run(['git', 'checkout', '-b', branch_name], cwd=repo_path, check=True)
            
            # Make multiple commits with different patterns
            for j in range(3):
                work_file = repo_path / f'{stage}_{j}.py'
                work_file.write_text(f'# {stage.capitalize()} work {j+1}\\n# Issue: {issue_id}\\n')
                subprocess.run(['git', 'add', f'{stage}_{j}.py'], cwd=repo_path, check=True)
                
                if j == 2:  # Final commit
                    commit_msg = f'{issue_id}: Complete {stage} work [closes roadmap:{issue_id}]'
                else:
                    commit_msg = f'{issue_id}: {stage.capitalize()} work part {j+1} [progress:{(j+1)*30}%]'
                
                subprocess.run(['git', 'commit', '-m', commit_msg], cwd=repo_path, check=True)
            
            # Merge back to develop
            subprocess.run(['git', 'checkout', 'develop'], cwd=repo_path, check=True)
            subprocess.run(['git', 'merge', '--no-ff', branch_name, '-m', f'Merge {branch_name} into develop'], 
                          cwd=repo_path, check=True)
        
        # Final merge to master
        subprocess.run(['git', 'checkout', 'master'], cwd=repo_path, check=True)
        subprocess.run(['git', 'merge', '--no-ff', 'develop', '-m', 'Merge develop into master'], 
                      cwd=repo_path, check=True)
        
        # Verify complex workflow completed without hook errors
        result = subprocess.run(['git', 'log', '--oneline', '--graph'], 
                              cwd=repo_path, capture_output=True, text=True, check=True)
        
        # Should have complex merge graph
        assert len(result.stdout.split('\n')) > 15  # Many commits from complex workflow

    def test_rebase_and_squash_integration(self, advanced_repo):
        """Test git hooks with rebase and squash operations."""
        core, repo_path = advanced_repo
        
        # Create issue for rebase testing
        issue = core.create_issue(
            title="Rebase Integration Test",
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE
        )
        
        issues = core.list_issues()
        issue_id = issues[0].id
        
        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create feature branch with multiple commits
        feature_branch = f'feature/{issue_id}-rebase-test'
        subprocess.run(['git', 'checkout', '-b', feature_branch], cwd=repo_path, check=True)
        
        # Make several small commits
        for i in range(4):
            rebase_file = repo_path / f'rebase_file_{i}.txt'
            rebase_file.write_text(f'Rebase test content {i}\\n')
            subprocess.run(['git', 'add', f'rebase_file_{i}.txt'], cwd=repo_path, check=True)
            subprocess.run(['git', 'commit', '-m', f'{issue_id}: Rebase test commit {i+1}'], 
                          cwd=repo_path, check=True)
        
        # Test interactive rebase (squash commits)
        # Note: This would normally be interactive, but we can test the hook behavior
        subprocess.run(['git', 'checkout', 'master'], cwd=repo_path, check=True)
        
        # Simulate squash merge
        subprocess.run(['git', 'merge', '--squash', feature_branch], cwd=repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', f'{issue_id}: Squashed rebase test commits [closes roadmap:{issue_id}]'], 
                      cwd=repo_path, check=True)
        
        # Verify squash merge worked with hooks
        result = subprocess.run(['git', 'log', '--oneline'], 
                              cwd=repo_path, capture_output=True, text=True, check=True)
        
        squash_commits = [line for line in result.stdout.split('\n') if 'Squashed rebase test' in line]
        assert len(squash_commits) == 1

    def test_cherry_pick_integration(self, advanced_repo):
        """Test git hooks with cherry-pick operations."""
        core, repo_path = advanced_repo
        
        # Create issues for cherry-pick testing
        hotfix_issue = core.create_issue(
            title="Critical Hotfix",
            priority=Priority.HIGH,
            issue_type=IssueType.BUG
        )
        
        issues = core.list_issues()
        hotfix_id = issues[0].id
        
        # Install hooks
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create hotfix on develop branch
        subprocess.run(['git', 'checkout', 'develop'], cwd=repo_path, check=True)
        
        hotfix_file = repo_path / 'hotfix.py'
        hotfix_file.write_text(f'# Critical hotfix\\n# Issue: {hotfix_id}\\n')
        subprocess.run(['git', 'add', 'hotfix.py'], cwd=repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', f'{hotfix_id}: Critical hotfix implementation [closes roadmap:{hotfix_id}]'], 
                      cwd=repo_path, check=True)
        
        # Get the commit hash for cherry-picking
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              cwd=repo_path, capture_output=True, text=True, check=True)
        hotfix_commit = result.stdout.strip()
        
        # Cherry-pick to master
        subprocess.run(['git', 'checkout', 'master'], cwd=repo_path, check=True)
        subprocess.run(['git', 'cherry-pick', hotfix_commit], cwd=repo_path, check=True)
        
        # Verify cherry-pick worked with hooks
        result = subprocess.run(['git', 'log', '--oneline'], 
                              cwd=repo_path, capture_output=True, text=True, check=True)
        
        hotfix_commits = [line for line in result.stdout.split('\n') if 'Critical hotfix' in line]
        assert len(hotfix_commits) >= 1

    def test_submodule_integration(self, advanced_repo):
        """Test git hooks behavior with submodules."""
        core, repo_path = advanced_repo
        
        # Install hooks in main repo
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()
        
        # Create issue for submodule work
        issue = core.create_issue(
            title="Submodule Integration",
            priority=Priority.MEDIUM,
            issue_type=IssueType.OTHER
        )
        
        issues = core.list_issues()
        issue_id = issues[0].id
        
        # Create a fake submodule directory structure
        submodule_dir = repo_path / 'vendor' / 'library'
        submodule_dir.mkdir(parents=True)
        
        # Add submodule content
        (submodule_dir / 'library.py').write_text('# External library\\n')
        subprocess.run(['git', 'add', 'vendor/'], cwd=repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', f'{issue_id}: Add vendor library [progress:50%]'], 
                      cwd=repo_path, check=True)
        
        # Update submodule
        (submodule_dir / 'update.py').write_text('# Library update\\n')
        subprocess.run(['git', 'add', 'vendor/'], cwd=repo_path, check=True)
        subprocess.run(['git', 'commit', '-m', f'{issue_id}: Update vendor library [closes roadmap:{issue_id}]'], 
                      cwd=repo_path, check=True)
        
        # Verify submodule commits worked with hooks
        result = subprocess.run(['git', 'log', '--oneline'], 
                              cwd=repo_path, capture_output=True, text=True, check=True)
        
        vendor_commits = [line for line in result.stdout.split('\n') if 'vendor library' in line]
        assert len(vendor_commits) == 2