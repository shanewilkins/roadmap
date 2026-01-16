"""CLI-facing sync service - provides backend creation and testing.

This service wraps the sync backend factory to prevent direct
CLI imports from lower-level adapter modules (layer violation fix).
"""

from typing import Literal

import structlog

from roadmap.adapters.sync.backend_factory import get_sync_backend as _get_backend
from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.infrastructure.coordination.core import RoadmapCore

log = structlog.get_logger()


def get_sync_backend(
    backend_type: Literal["github", "git"],
    core: RoadmapCore,
    config: dict | None = None,
) -> SyncBackendInterface | None:
    """Create a sync backend (CLI-facing wrapper over factory).

    This wrapper provides a clean, CLI-facing interface for backend creation
    without requiring direct imports of the backend factory.

    Args:
        backend_type: Type of backend ('github' or 'git')
        core: RoadmapCore instance
        config: Optional backend configuration

    Returns:
        Backend instance or None if creation fails
    """
    return _get_backend(backend_type, core, config)


def test_backend_connectivity(
    backend: SyncBackendInterface, backend_type: str
) -> tuple[bool, str]:
    """Test backend connectivity.

    Args:
        backend: The backend to test
        backend_type: Type name for logging

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if backend.authenticate():
            return True, f"✅ {backend_type.capitalize()} connectivity verified"
        else:
            return False, f"❌ {backend_type.capitalize()} authentication failed"
    except Exception as e:
        log.error(
            "backend_connectivity_test_failed",
            backend_type=backend_type,
            error=str(e),
        )
        return False, f"❌ Connection test failed: {str(e)}"
