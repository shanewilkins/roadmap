"""GitHub configuration management utilities."""

import yaml
from structlog import get_logger

from roadmap.common.console import get_console
from roadmap.common.constants import SyncBackend
from roadmap.core.utils.git_remote_parser import get_github_from_git_remote
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger()
console = get_console()


class GitHubConfigManager:
    """Manages GitHub configuration in roadmap config file."""

    def __init__(self, core: RoadmapCore):
        """Initialize GitHubConfigManager.

        Args:
            core: Core roadmap instance.
        """
        self.core = core
        self.config_file = core.roadmap_dir / "config.yaml"

    def save_github_config(
        self, github_repo: str, sync_backend: SyncBackend = SyncBackend.GITHUB
    ) -> None:
        """Save GitHub repository configuration.

        Args:
            github_repo: GitHub repository (owner/repo)
            sync_backend: Backend to use (SyncBackend.GITHUB or SyncBackend.GIT)

        Raises:
            ValueError: If github_repo is invalid format
        """
        # Validate repository format
        if not github_repo or "/" not in github_repo:
            log = logger.bind(github_repo=github_repo, operation="save_github_config")
            log.error("invalid_github_repo_format")
            raise ValueError(
                f"Invalid GitHub repository format: '{github_repo}'. "
                "Expected format: 'owner/repo'"
            )

        try:
            if self.config_file.exists():
                with open(self.config_file) as f:
                    loaded = yaml.safe_load(f)
                    config = loaded if isinstance(loaded, dict) else {}
            else:
                config: dict = {}

            config["github"] = {
                "repository": github_repo,
                "enabled": True,
                "sync_enabled": True,
                "sync_backend": sync_backend.value,
                "webhook_secret": None,
                "sync_settings": {
                    "bidirectional": True,
                    "auto_close": True,
                    "sync_labels": True,
                    "sync_milestones": True,
                },
            }

            with open(self.config_file, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            log = logger.bind(
                github_repo=github_repo,
                sync_backend=sync_backend.value,
                operation="save_github_config",
            )
            log.info("github_config_saved")
            get_console().print("⚙️  Configuration saved")

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            log = logger.bind(
                github_repo=github_repo,
                sync_backend=sync_backend.value,
                error=str(e),
                operation="save_github_config",
            )
            log.error("github_config_save_failed")
            raise

    def auto_detect_and_update(self) -> tuple[str | None, str | None]:
        """Auto-detect GitHub owner/repo from git remote and update config if needed.

        Returns:
            Tuple of (owner, repo) or (None, None) if not detected or disabled
        """
        # Check if auto-detection is enabled in config
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = yaml.safe_load(f) or {}
                    github_config = config.get("github", {})
                    sync_settings = github_config.get("sync_settings", {})

                    # Check if auto-detection is disabled
                    if not sync_settings.get("auto_detect_from_git", True):
                        return None, None

                    # If owner/repo already set, don't override
                    if github_config.get("repository"):
                        return None, None
            except Exception as e:
                logger.debug("config_read_failed", error=str(e))

        # Try to auto-detect from git remote
        owner, repo = get_github_from_git_remote(self.core.root_path)

        if owner and repo:
            try:
                github_repo = f"{owner}/{repo}"
                logger.info(
                    "github_auto_detected",
                    owner=owner,
                    repo=repo,
                    repository=github_repo,
                )

                # Update config with detected values
                if self.config_file.exists():
                    with open(self.config_file) as f:
                        config = yaml.safe_load(f) or {}
                else:
                    config = {}

                if "github" not in config:
                    config["github"] = {}

                config["github"]["repository"] = github_repo
                config["github"]["enabled"] = True

                with open(self.config_file, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                return owner, repo

            except Exception as e:
                logger.debug("github_auto_config_failed", error=str(e))

        return None, None
