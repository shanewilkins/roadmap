"""GitHub label synchronization helpers."""

from __future__ import annotations

from typing import Any

from structlog import get_logger

logger = get_logger()


class GitHubLabelSyncService:
    """Encapsulates label capability checks, caching, and creation."""

    def __init__(self, backend: Any):
        """Initialize the label sync service for a backend instance."""
        self.backend = backend
        self.label_cache: set[str] | None = None
        self.label_support: bool | None = None

    def sync_labels_enabled(self) -> bool:
        """Return whether label synchronization is enabled by configuration."""
        config = getattr(self.backend, "config", {}) or {}
        sync_settings = (
            config.get("sync_settings", {}) if isinstance(config, dict) else {}
        )
        return bool(sync_settings.get("sync_labels", True))

    @staticmethod
    def get_label_color(name: str) -> str:
        """Return the configured color hex value for a label name."""
        label_colors = {
            "priority:critical": "FF0000",
            "priority:high": "FF9900",
            "priority:medium": "FFFF00",
            "priority:low": "00FF00",
            "status:todo": "CCCCCC",
            "status:in-progress": "0366D6",
            "status:blocked": "D73A49",
            "status:review": "A371F7",
            "status:done": "28A745",
        }
        return label_colors.get(name, "CCCCCC")

    def get_label_client(self):
        """Return a label API client, or None when unsupported."""
        if self.label_support is False:
            return None

        client = (
            self.backend.get_label_client()
            if hasattr(self.backend, "get_label_client")
            else self.backend.get_api_client()
        )

        if client is None:
            self.label_support = False
            return None

        if self.label_support is None:
            if not (hasattr(client, "get_labels") and hasattr(client, "create_label")):
                logger.warning(
                    "github_label_client_missing_methods",
                    has_get_labels=hasattr(client, "get_labels"),
                    has_create_label=hasattr(client, "create_label"),
                    severity="operational",
                )
                self.label_support = False
                return None
            self.label_support = True

        return client

    def init_label_cache(self, client) -> bool:
        """Populate local label cache from GitHub."""
        if self.label_cache is not None:
            return True

        try:
            existing_labels = client.get_labels()
            self.label_cache = {
                label["name"]
                for label in existing_labels
                if isinstance(label, dict) and label.get("name")
            }
            return True
        except Exception as e:
            logger.warning(
                "github_labels_fetch_failed",
                error=str(e),
                error_type=type(e).__name__,
                severity="operational",
            )
            self.label_cache = set()
            return False

    def ensure_labels_exist(self, labels: list[str]) -> None:
        """Create any missing labels on GitHub when label sync is enabled."""
        if not labels or not self.sync_labels_enabled():
            return

        client = self.get_label_client()
        if client is None:
            return

        if not self.init_label_cache(client):
            return

        label_cache = self.label_cache
        if label_cache is None:
            return

        missing = [label for label in labels if label not in label_cache]
        for label in missing:
            try:
                client.create_label(label, self.get_label_color(label))
                label_cache.add(label)
                logger.info("github_label_created", label=label)
            except Exception as e:
                logger.warning(
                    "github_label_create_failed",
                    label=label,
                    error=str(e),
                    error_type=type(e).__name__,
                    severity="operational",
                )
