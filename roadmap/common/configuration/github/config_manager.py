"""GitHub configuration management utilities."""

import yaml
from structlog import get_logger

from roadmap.common.console import get_console
from roadmap.common.constants import SyncBackend
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger()
console = get_console()


class GitHubConfigManager:
    """Manages GitHub configuration in roadmap config file."""

    def __init__(self, core: RoadmapCore):
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
