"""Utilities for generating GitHub URLs on-demand."""


def get_issue_url(owner: str, repo: str, issue_number: int | str) -> str:
    """Generate a GitHub issue URL.

    Args:
        owner: Repository owner
        repo: Repository name
        issue_number: Issue number

    Returns:
        Full GitHub issue URL
    """
    issue_num = int(issue_number) if isinstance(issue_number, str) else issue_number
    return f"https://github.com/{owner}/{repo}/issues/{issue_num}"


def get_milestone_url(owner: str, repo: str, milestone_number: int | str) -> str:
    """Generate a GitHub milestone URL.

    Args:
        owner: Repository owner
        repo: Repository name
        milestone_number: Milestone number

    Returns:
        Full GitHub milestone URL
    """
    milestone_num = (
        int(milestone_number) if isinstance(milestone_number, str) else milestone_number
    )
    return f"https://github.com/{owner}/{repo}/milestone/{milestone_num}"


def get_repo_url(owner: str, repo: str) -> str:
    """Generate a GitHub repository URL.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        Full GitHub repository URL
    """
    return f"https://github.com/{owner}/{repo}"


def parse_github_number(url: str) -> int | None:
    """Extract issue/milestone number from a GitHub URL.

    Args:
        url: GitHub URL (e.g., https://github.com/owner/repo/issues/123)

    Returns:
        Issue/milestone number, or None if not found
    """
    try:
        # Try to extract number from URL
        parts = url.rstrip("/").split("/")
        if parts:
            last_part = parts[-1]
            return int(last_part)
    except (ValueError, IndexError):
        pass
    return None
