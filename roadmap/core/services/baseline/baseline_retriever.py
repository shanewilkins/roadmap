"""Baseline snapshot retrieval from remote sources."""

from typing import Any

import structlog

BaselineSnapshot = dict[str, Any]

logger = structlog.get_logger()


class BaselineRetriever:
    """Retrieve the current sync baseline from available stores.

    Prefers `core.db.get_sync_baseline()` when available, then a provided
    `db_session.get_sync_baseline()`. If neither is present, returns an
    empty baseline snapshot.
    """

    @staticmethod
    def get_current_baseline(
        core: Any = None, db_session: Any = None
    ) -> BaselineSnapshot:
        """Get the current sync baseline from available stores.

        Tries multiple sources in order: core.db, db_session, or empty dict.

        Args:
            core: Optional core instance with db attribute.
            db_session: Optional database session.

        Returns:
            Baseline snapshot dictionary.
        """
        if (
            core is not None
            and getattr(core, "db", None)
            and hasattr(core.db, "get_sync_baseline")
        ):
            try:
                return core.db.get_sync_baseline() or {}
            except Exception as e:
                logger.debug(
                    "get_sync_baseline_failed",
                    operation="get_sync_baseline",
                    error=str(e),
                    action="Using fallback empty dict",
                )
                return {}

        if db_session is not None and hasattr(db_session, "get_sync_baseline"):
            try:
                return db_session.get_sync_baseline() or {}
            except Exception as e:
                logger.debug(
                    "get_sync_baseline_db_failed",
                    operation="get_sync_baseline_db_session",
                    error=str(e),
                    action="Using empty baseline",
                )
                return {}

        return {}
