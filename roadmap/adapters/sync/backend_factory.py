"""Factory for creating sync backend instances based on configuration."""

from typing import Literal

import structlog

from roadmap.adapters.sync.backends.github_sync_backend import GitHubSyncBackend
from roadmap.adapters.sync.backends.vanilla_git_sync_backend import (
    VanillaGitSyncBackend,
)
from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.infrastructure.core import RoadmapCore

log = structlog.get_logger()


def get_sync_backend(
    backend_type: Literal["github", "git"],
    core: RoadmapCore,
    config: dict | None = None,
) -> SyncBackendInterface | None:
    """Create and return a sync backend instance.

    Args:
        backend_type: Type of backend to create ('github' or 'git')
        core: RoadmapCore instance
        config: Configuration dict for the backend

    Returns:
        Backend instance implementing SyncBackendInterface, or None if creation fails

    Raises:
        ValueError: If backend_type is invalid
    """
    config_dict = config or {}

    if backend_type == "github":
        log.info("sync_backend_creating", backend_type="github")
        return GitHubSyncBackend(core, config_dict)
    elif backend_type == "git":
        try:
            log.info("sync_backend_creating", backend_type="git")
            return VanillaGitSyncBackend(core, config_dict)
        except (ValueError, RuntimeError) as e:
            # VanillaGitSyncBackend raises on init failure (not in git repo, etc.)
            log.warning(
                "sync_backend_creation_failed",
                backend_type="git",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None
    else:
        raise ValueError(
            f"Invalid backend type: {backend_type}. Must be 'github' or 'git'"
        )


def detect_backend_from_config(config: dict) -> Literal["github", "git"]:
    """Detect the appropriate backend from configuration.

    Args:
        config: Configuration dict from .roadmap/config.json or .github/config.json

    Returns:
        Backend type to use ('github' or 'git')
    """
    # If explicitly specified in config, use that
    if config.get("backend") in ("github", "git"):
        backend = config["backend"]
        log.info("backend_detected_explicit", backend=backend)
        return backend

    # If GitHub config present, prefer GitHub backend
    if config.get("github") and (
        config["github"].get("owner") and config["github"].get("repo")
    ):
        log.info(
            "backend_detected_github_config",
            has_owner=bool(config["github"].get("owner")),
            has_repo=bool(config["github"].get("repo")),
        )
        return "github"

    # Default to vanilla git backend
    log.info("backend_detected_default", backend="git")
    return "git"


def get_backend_for_config(
    core: RoadmapCore, config: dict | None = None
) -> SyncBackendInterface | None:
    """Create backend based on auto-detected config.

    Convenience function that detects the appropriate backend type
    and creates an instance.

    Args:
        core: RoadmapCore instance
        config: Configuration dict (optional)

    Returns:
        Backend instance, or None if creation fails
    """
    config = config or {}
    backend_type = detect_backend_from_config(config)
    log.debug("backend_factory_creating_instance", backend_type=backend_type)
    return get_sync_backend(backend_type, core, config)
