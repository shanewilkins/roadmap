"""Test for git hooks manager hook script generation and execution."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.git.git_hooks_manager import GitHookManager
from roadmap.infrastructure.core import RoadmapCore


class TestGitHooksManagerFix:
    """Test that git hooks are properly generated and can execute."""

    def test_hook_content_generation(self):
        """Test that hook content is properly formatted bash/python."""
        mock_core = MagicMock(spec=RoadmapCore)
        manager = GitHookManager(mock_core)

        # Test all hook types
        for hook_name in ["post-commit", "pre-push", "post-merge", "post-checkout"]:
            content = manager._get_hook_content(hook_name)

            # Verify it's a bash script
            assert content.startswith("#!/bin/bash")

            # Verify it contains the hook marker
            assert f"roadmap-hook: {hook_name}" in content

            # Verify it imports the necessary modules
            assert (
                "from roadmap.adapters.git.git_hooks_manager import GitHookManager"
                in content
            )
            assert "from roadmap.infrastructure.core import RoadmapCore" in content

            # Verify it has proper method name (underscores instead of hyphens)
            handler_name = hook_name.replace("-", "_")
            assert f'getattr(hook_manager, "{handler_name}")' in content

            # Verify heredoc syntax for python code
            assert "PYTHON_HOOK_EOF" in content

    def test_hook_content_has_proper_python_syntax(self):
        """Test that the Python code inside the hook script is syntactically valid."""
        mock_core = MagicMock(spec=RoadmapCore)
        manager = GitHookManager(mock_core)

        for hook_name in ["post-commit", "pre-push", "post-merge", "post-checkout"]:
            content = manager._get_hook_content(hook_name)

            # Extract the Python part between the heredocs
            start_marker = "PYTHON_HOOK_EOF'"
            end_marker = "PYTHON_HOOK_EOF"

            if start_marker in content and end_marker in content:
                start_idx = content.find(start_marker) + len(start_marker)
                end_idx = content.find(end_marker, start_idx)
                python_code = content[start_idx:end_idx].strip()

                # Try to compile the Python code to verify syntax
                try:
                    compile(python_code, "<hook_script>", "exec")
                except SyntaxError as e:
                    pytest.fail(f"Hook {hook_name} has invalid Python syntax: {e}")

    def test_handler_methods_exist(self):
        """Test that all handler methods exist on GitHookManager."""
        mock_core = MagicMock(spec=RoadmapCore)
        manager = GitHookManager(mock_core)

        handler_methods = [
            "handle_post_commit",
            "handle_pre_push",
            "handle_post_merge",
            "handle_post_checkout",
        ]

        for method_name in handler_methods:
            assert hasattr(manager, method_name), f"Missing method: {method_name}"
            assert callable(
                getattr(manager, method_name)
            ), f"Not callable: {method_name}"

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.chmod")
    def test_hook_installation_creates_files(
        self, mock_chmod, mock_write, mock_mkdir, mock_exists
    ):
        """Test that installing hooks creates the hook files with correct permissions."""
        mock_exists.return_value = True

        with patch.object(GitHookManager, "__init__", lambda x, y: None):
            manager = GitHookManager(None)
            manager.hooks_dir = Path(".git/hooks")
            manager.core = MagicMock(spec=RoadmapCore)

            # Mock the parent class initialization
            manager.git_integration = MagicMock()
            manager.git_integration.is_git_repository.return_value = True

            # Test installing a single hook
            manager._install_hook("post-commit")

            # Verify write_text was called
            assert mock_write.called, "Hook file should be written"

            # Verify chmod was called with executable permissions (0o755)
            assert mock_chmod.called, "Hook file should be made executable"
            chmod_args = mock_chmod.call_args[0]
            assert (
                chmod_args[0] == 0o755
            ), "Hook should have executable permission (0o755)"

    def test_hook_script_error_handling(self):
        """Test that hook scripts handle errors silently."""
        mock_core = MagicMock(spec=RoadmapCore)
        manager = GitHookManager(mock_core)

        content = manager._get_hook_content("post-commit")

        # Verify exception handling exists (accepts both "except Exception:" and "except Exception as e:")
        assert "except Exception" in content
        assert "pass" in content  # Silent fail

    def test_handler_methods_dont_raise(self):
        """Test that handler methods don't raise exceptions even with mock core."""
        mock_core = MagicMock(spec=RoadmapCore)
        manager = GitHookManager(mock_core)

        # These should not raise even with mocked core
        try:
            manager.handle_post_commit()
            manager.handle_pre_push()
            manager.handle_post_merge()
            manager.handle_post_checkout()
        except Exception as e:
            pytest.fail(f"Handler method raised exception: {e}")
