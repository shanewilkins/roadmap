"""Git history utilities for accessing file content and baselines.

This module provides utilities to reconstruct baseline state from git history,
enabling three-way merge without a database. Key functions:

- get_file_at_timestamp: Get file content as it existed at a specific time
- find_commit_at_time: Find the git commit closest to a timestamp
- get_file_at_commit: Get file content at a specific commit SHA
"""

import subprocess
from datetime import datetime

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class GitHistoryError(Exception):
    """Base exception for git history operations."""

    pass


class NotAGitRepository(GitHistoryError):
    """Raised when not in a git repository."""

    pass


class FileNotFound(GitHistoryError):
    """Raised when file is not found in git history."""

    pass


def _run_git_command(args: list[str], cwd: str = ".") -> str:
    """Run a git command and return stdout.

    Args:
        args: Git command arguments (e.g., ['log', '--oneline'])
        cwd: Working directory for the command

    Returns:
        Command stdout as string

    Raises:
        NotAGitRepository: If not in a git repository
        GitHistoryError: If git command fails
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()

            # Check for "not a git repository" error
            if "fatal: not a git repository" in error_msg.lower():
                raise NotAGitRepository(f"Not in a git repository: {error_msg}")

            raise GitHistoryError(f"Git command failed: {error_msg}")

        return result.stdout.strip()

    except FileNotFoundError as e:
        raise GitHistoryError("Git not found in PATH") from e


def find_commit_at_time(
    timestamp: datetime | str, file_path: str | None = None, cwd: str = "."
) -> str:
    """Find the git commit closest to a given timestamp.

    Args:
        timestamp: Datetime or ISO 8601 string to search for
        file_path: Optional - only find commits affecting this file
        cwd: Working directory

    Returns:
        Commit SHA of the closest commit

    Raises:
        NotAGitRepository: If not in a git repository
        GitHistoryError: If no commits found
    """
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except ValueError as e:
            raise GitHistoryError(f"Invalid timestamp format: {timestamp}") from e

    timestamp_str = timestamp.isoformat()

    try:
        args = [
            "log",
            "--format=%H %aI",  # SHA and timestamp
            f"--until={timestamp_str}",
            "-1",  # Get most recent commit before timestamp
        ]

        if file_path:
            args.append("--")
            args.append(file_path)

        output = _run_git_command(args, cwd)

        if not output:
            # No commits found - try to get the very first commit
            logger.warning(
                "no_commits_before_timestamp",
                timestamp=timestamp_str,
                file_path=file_path,
                severity="operational",
            )
            args_first = ["log", "--format=%H", "--reverse", "-1"]
            if file_path:
                args_first.extend(["--", file_path])
            first_commit = _run_git_command(args_first, cwd)
            if not first_commit:
                raise GitHistoryError("No commits found in repository")
            return first_commit

        # Parse "SHA TIMESTAMP" format and return SHA
        sha = output.split()[0]
        logger.debug(
            "found_commit_at_time",
            timestamp=timestamp_str,
            commit=sha[:8],
            file_path=file_path,
        )
        return sha

    except GitHistoryError:
        raise


def get_file_at_commit(file_path: str, commit_sha: str, cwd: str = ".") -> str:
    """Get file content at a specific commit.

    Args:
        file_path: Path to file (relative to repo root)
        commit_sha: Git commit SHA
        cwd: Working directory

    Returns:
        File content as string

    Raises:
        NotAGitRepository: If not in a git repository
        FileNotFound: If file doesn't exist at commit
        GitHistoryError: If git command fails
    """
    try:
        output = _run_git_command(["show", f"{commit_sha}:{file_path}"], cwd)
        logger.debug(
            "retrieved_file_at_commit",
            file=file_path,
            commit=commit_sha[:8],
        )
        return output

    except GitHistoryError as e:
        if "does not exist" in str(e).lower():
            raise FileNotFound(
                f"File {file_path} not found at commit {commit_sha}"
            ) from e
        raise


def get_file_at_timestamp(
    file_path: str, timestamp: datetime | str, cwd: str = "."
) -> str:
    """Get file content as it existed at a specific timestamp.

    This function reconstructs the baseline by:
    1. Finding the commit closest to the timestamp
    2. Retrieving the file content at that commit

    Args:
        file_path: Path to file (relative to repo root)
        timestamp: Datetime or ISO 8601 string
        cwd: Working directory

    Returns:
        File content as string

    Raises:
        NotAGitRepository: If not in a git repository
        FileNotFound: If file didn't exist at timestamp
        GitHistoryError: If git operations fail
    """
    try:
        commit_sha = find_commit_at_time(timestamp, file_path, cwd)
        content = get_file_at_commit(file_path, commit_sha, cwd)
        logger.debug(
            "file_retrieved_at_timestamp",
            file=file_path,
            timestamp=str(timestamp),
            commit=commit_sha[:8],
        )
        return content

    except (NotAGitRepository, FileNotFound, GitHistoryError):
        raise


def get_file_at_head(file_path: str, cwd: str = ".") -> str:
    """Get current file content from HEAD.

    Args:
        file_path: Path to file (relative to repo root)
        cwd: Working directory

    Returns:
        Current file content

    Raises:
        NotAGitRepository: If not in a git repository
        FileNotFound: If file doesn't exist in HEAD
        GitHistoryError: If git command fails
    """
    return get_file_at_commit(file_path, "HEAD", cwd)


def get_last_modified_time(file_path: str, cwd: str = ".") -> datetime | None:
    """Get the timestamp of the last commit that modified a file.

    Args:
        file_path: Path to file (relative to repo root)
        cwd: Working directory

    Returns:
        Datetime of last modification, or None if file not found

    Raises:
        NotAGitRepository: If not in a git repository
        GitHistoryError: If git command fails
    """
    try:
        output = _run_git_command(["log", "-1", "--format=%aI", "--", file_path], cwd)

        if not output:
            logger.debug(
                "file_not_in_history",
                file=file_path,
            )
            return None

        return datetime.fromisoformat(output)

    except GitHistoryError as e:
        if "does not exist" in str(e).lower():
            return None
        raise


def is_git_repository(cwd: str = ".") -> bool:
    """Check if a directory is a git repository.

    Args:
        cwd: Directory to check

    Returns:
        True if directory is a git repository, False otherwise
    """
    try:
        _run_git_command(["rev-parse", "--git-dir"], cwd)
        return True
    except (NotAGitRepository, GitHistoryError):
        return False


def get_repository_root(cwd: str = ".") -> str:
    """Get the root directory of the git repository.

    Args:
        cwd: Working directory

    Returns:
        Path to repository root

    Raises:
        NotAGitRepository: If not in a git repository
        GitHistoryError: If git command fails
    """
    try:
        root = _run_git_command(["rev-parse", "--show-toplevel"], cwd)
        logger.debug("found_repo_root", root=root)
        return root
    except GitHistoryError:
        raise


def get_changed_files_since_commit(ref: str = "HEAD~1", cwd: str = ".") -> set[str]:
    """Get list of files changed since a git reference.

    Args:
        ref: Git reference (default: previous commit)
        cwd: Working directory

    Returns:
        Set of file paths that changed

    Raises:
        NotAGitRepository: If not in a git repository
        GitHistoryError: If git command fails
    """
    try:
        output = _run_git_command(["diff", "--name-only", ref, "HEAD"], cwd)

        if not output:
            return set()

        files = set(output.split("\n"))
        logger.debug(
            "found_changed_files",
            ref=ref,
            count=len(files),
        )
        return files

    except GitHistoryError:
        raise
