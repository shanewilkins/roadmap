"""Gateway to sync adapter layer for core services.

This module mediates all core service access to sync adapter implementations,
ensuring proper layer separation between Core and Adapters layers.

All imports from roadmap.adapters.sync are localized to this module.
Core services import from this gateway instead of directly from adapters.
"""

from typing import Any, Literal


class SyncGateway:
    """Gateway for sync adapter operations.

    Provides a centralized interface for core services to access sync
    backend and orchestration functionality without direct adapter imports.
    """

    @staticmethod
    def get_sync_backend(
        backend_type: Literal["github", "git"], core: Any, config: Any
    ) -> Any:
        """Get a sync backend for the specified type.

        Args:
            backend_type: Type of backend (e.g., "github", "git")
            core: Core context object
            config: Configuration for the backend

        Returns:
            Backend instance or None if not available
        """
        from roadmap.adapters.sync.backend_factory import get_sync_backend

        return get_sync_backend(backend_type, core, config)

    @staticmethod
    def create_sync_cache_orchestrator(
        core: Any,
        backend: Any,
        conflict_resolver: Any = None,
        state_comparator: Any = None,
        show_progress: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Create a sync cache orchestrator for three-way merge sync operations.

        Args:
            core: Core context object
            backend: Sync backend instance
            conflict_resolver: Resolver for sync conflicts (optional)
            state_comparator: Comparator for sync states (optional)
            show_progress: Whether to show progress during sync (default: True)
            **kwargs: Additional keyword arguments passed to orchestrator

        Returns:
            SyncCacheOrchestrator instance
        """
        from roadmap.adapters.sync.sync_cache_orchestrator import (
            SyncCacheOrchestrator,
        )

        return SyncCacheOrchestrator(
            core,
            backend,
            conflict_resolver=conflict_resolver,
            state_comparator=state_comparator,
            show_progress=show_progress,
            **kwargs,
        )

    @staticmethod
    def link_issue_in_database(
        repo: Any, local_id: str, backend: Any, remote_id: str
    ) -> bool:
        """Link an issue in the database for sync tracking.

        Args:
            repo: Database repository
            local_id: Local issue identifier
            backend: Sync backend
            remote_id: Remote issue identifier

        Returns:
            True if linking was successful
        """
        from roadmap.adapters.sync.services.sync_linking_service import (
            SyncLinkingService,
        )

        return SyncLinkingService.link_issue_in_database(
            repo, local_id, backend, remote_id
        )
