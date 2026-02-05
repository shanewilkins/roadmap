"""Utility for parsing GitHub information from git remote URLs."""

import re
import subprocess
from pathlib import Path

from structlog import get_logger

logger = get_logger()


def parse_github_remote(remote_url: str) -> tuple[str | None, str | None]:
    """Parse GitHub owner and repo from a git remote URL.

    Supports both SSH and HTTPS formats:
    - git@github.com:owner/repo.git
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo

    Args:
        remote_url: Git remote URL string

    Returns:
        Tuple of (owner, repo) or (None, None) if not a valid GitHub URL
    """
    if not remote_url or "github.com" not in remote_url:
        return None, None

    # Match SSH format: git@github.com:owner/repo.git
    ssh_match = re.search(r"github\.com:([^/]+)/([^/.]+)", remote_url)
    if ssh_match:
        owner = ssh_match.group(1)
        repo = ssh_match.group(2)
        return owner, repo

    # Match HTTPS format: https://github.com/owner/repo.git or https://github.com/owner/repo
    https_match = re.search(r"github\.com/([^/]+)/([^/.]+)", remote_url)
    if https_match:
        owner = https_match.group(1)
        repo = https_match.group(2)
        return owner, repo

    return None, None


def get_github_from_git_remote(
    repo_path: Path | None = None,
) -> tuple[str | None, str | None]:
    """Auto-detect GitHub owner and repo from git remote origin.

    Args:
        repo_path: Path to git repository (defaults to current directory)

    Returns:
        Tuple of (owner, repo) or (None, None) if not detected
    """
    try:
        cwd = str(repo_path) if repo_path else None
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )

        if result.returncode == 0 and result.stdout.strip():
            remote_url = result.stdout.strip()
            owner, repo = parse_github_remote(remote_url)

            if owner and repo:
                logger.info(
                    "github_detected_from_remote",
                    owner=owner,
                    repo=repo,
                    remote_url=remote_url,
                )
                return owner, repo

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug("git_remote_detection_failed", error=str(e))

    return None, None
