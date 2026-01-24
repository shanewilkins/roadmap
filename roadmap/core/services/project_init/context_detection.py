"""Service for detecting project context from git and file system."""

import json
import re
import subprocess
from pathlib import Path

import structlog

logger = structlog.get_logger()


class ProjectContextDetectionService:
    """Service for detecting project context from git and file system."""

    @staticmethod
    def detect_project_context() -> dict:
        """Detect project context from git repository and directory structure.

        Returns:
            Dictionary with detected context:
            - git_repo: Repository in owner/repo format if detected
            - project_name: Project name from git, package files, or directory
            - git_user: Git user name if available
            - has_git: Whether in a git repository
        """
        context = {
            "git_repo": None,
            "project_name": None,
            "git_user": None,
            "has_git": False,
        }

        try:
            # Check if we're in a git repository
            git_check = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            context["has_git"] = git_check.returncode == 0

            if context["has_git"]:
                ProjectContextDetectionService._detect_git_repo(context)
                ProjectContextDetectionService._detect_git_user(context)

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass

        # Fallback to directory name if no git repo detected
        if not context["project_name"]:
            context["project_name"] = Path.cwd().name

        # Try to detect from package files
        if not context["project_name"] or context["project_name"] == ".":
            ProjectContextDetectionService._detect_from_package_files(context)

        return context

    @staticmethod
    def _detect_git_repo(context: dict) -> None:
        """Detect git repository and populate context."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                origin_url = result.stdout.strip()
                # Parse GitHub repository from URL
                if "github.com" in origin_url:
                    # Handle both SSH and HTTPS URLs
                    if origin_url.startswith("git@github.com:"):
                        repo_part = origin_url.replace("git@github.com:", "").replace(
                            ".git", ""
                        )
                    elif "github.com/" in origin_url:
                        repo_part = origin_url.split("github.com/")[1].replace(
                            ".git", ""
                        )
                    else:
                        repo_part = None

                    if repo_part and "/" in repo_part:
                        context["git_repo"] = repo_part
                        context["project_name"] = repo_part.split("/")[1]
        except Exception as e:
            logger.debug(
                "git_context_detection_failed",
                operation="detect_git_context",
                error=str(e),
                action="Continuing with partial context",
            )

    @staticmethod
    def _detect_git_user(context: dict) -> None:
        """Detect git user name and populate context."""
        try:
            user_result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if user_result.returncode == 0:
                context["git_user"] = user_result.stdout.strip()
        except Exception as e:
            logger.debug(
                "git_user_detection_failed",
                operation="detect_git_user",
                error=str(e),
                action="Skipping git user detection",
            )

    @staticmethod
    def _detect_from_package_files(context: dict) -> None:
        """Try to detect project name from package files."""
        for config_file in ["pyproject.toml", "package.json", "Cargo.toml"]:
            if Path(config_file).exists():
                try:
                    content = Path(config_file).read_text()
                    if config_file == "pyproject.toml":
                        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            context["project_name"] = match.group(1)
                            break
                    elif config_file == "package.json":
                        data = json.loads(content)
                        if "name" in data:
                            context["project_name"] = data["name"]
                            break
                except Exception as e:
                    logger.debug(
                        "package_file_parse_failed",
                        operation="parse_package_file",
                        file=config_file,
                        error=str(e),
                        action="Trying next config file",
                    )
