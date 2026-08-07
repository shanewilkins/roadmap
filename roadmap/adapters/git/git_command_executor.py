"""Low-level Git command executor."""

import subprocess
from pathlib import Path


class GitCommandExecutor:
    """Executes Git commands and handles subprocess interaction."""

    def __init__(self, repo_path: Path | None = None):
        """Initialize executor with repository path."""
        self.repo_path = repo_path or Path.cwd()
        self._git_dir = self._find_git_directory()

    def _find_git_directory(self) -> Path | None:
        """Find the .git directory by walking up the directory tree."""
        current = self.repo_path.resolve()

        while current != current.parent:
            git_dir = current / ".git"
            if git_dir.exists():
                return git_dir
            current = current.parent

        return None

    def is_git_repository(self) -> bool:
        """Check if current directory is in a Git repository."""
        if self._git_dir is None:
            self._git_dir = self._find_git_directory()
        return self._git_dir is not None

    def run(self, args: list[str], cwd: Path | None = None) -> str | None:
        """Run a git command and return the output.

        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory for command execution

        Returns:
            Command output stripped of whitespace, or None if command fails
        """
        if not self.is_git_repository():
            return None

        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
