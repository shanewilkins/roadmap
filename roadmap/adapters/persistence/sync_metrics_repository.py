"""Repository for persisting and querying sync metrics.

This module provides database persistence for sync operation metrics,
allowing historical tracking and analysis of sync operations.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from roadmap.adapters.persistence.database_manager import DatabaseManager
from roadmap.common.logging import get_logger
from roadmap.core.observability.sync_metrics import SyncMetrics

logger = get_logger(__name__)


class SyncMetricsRepository:
    """Repository for sync metrics persistence and queries."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize the repository.

        Args:
            db_manager: DatabaseManager instance for database access
        """
        self.db_manager = db_manager

    def save(self, metrics: SyncMetrics) -> bool:
        """Save sync metrics to database.

        Args:
            metrics: SyncMetrics object to persist

        Returns:
            True if successful, False otherwise
        """
        try:
            record_id = str(uuid.uuid4())
            metrics_dict = metrics.to_dict()
            metrics_json = json.dumps(metrics_dict)

            with self.db_manager.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO sync_metrics (
                        id,
                        operation_id,
                        backend_type,
                        duration_seconds,
                        metrics_json,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        metrics.operation_id,
                        metrics.backend_type,
                        metrics.duration_seconds,
                        metrics_json,
                        datetime.now(UTC).isoformat(),
                    ),
                )

            logger.info(
                "sync_metrics_saved",
                operation_id=metrics.operation_id,
                backend_type=metrics.backend_type,
                duration_seconds=metrics.duration_seconds,
            )
            return True

        except Exception as e:
            logger.error(
                "sync_metrics_save_failed",
                error=str(e),
                operation_id=metrics.operation_id,
                severity="operational",
            )
            return False

    def get_latest(self, backend_type: str | None = None) -> SyncMetrics | None:
        """Get the most recent sync metrics.

        Args:
            backend_type: Optional filter by backend type

        Returns:
            SyncMetrics if found, None otherwise
        """
        try:
            conn = self.db_manager._get_connection()

            query = "SELECT metrics_json FROM sync_metrics"
            params = []

            if backend_type:
                query += " WHERE backend_type = ?"
                params.append(backend_type)

            query += " ORDER BY created_at DESC LIMIT 1"

            cursor = conn.execute(query, params)
            row = cursor.fetchone()

            if not row:
                return None

            metrics_dict = json.loads(row[0])
            return self._dict_to_metrics(metrics_dict)

        except Exception as e:
            logger.error(
                "sync_metrics_get_latest_failed",
                error=str(e),
                backend_type=backend_type,
                severity="operational",
            )
            return None

    def list_by_date(
        self, backend_type: str | None = None, days: int = 7
    ) -> list[SyncMetrics]:
        """List sync metrics from the last N days.

        Args:
            backend_type: Optional filter by backend type
            days: Number of days to look back (default: 7)

        Returns:
            List of SyncMetrics objects
        """
        try:
            conn = self.db_manager._get_connection()
            cutoff_date = (datetime.now(UTC) - timedelta(days=days)).isoformat()

            query = "SELECT metrics_json FROM sync_metrics WHERE created_at >= ?"
            params = [cutoff_date]

            if backend_type:
                query += " AND backend_type = ?"
                params.append(backend_type)

            query += " ORDER BY created_at DESC"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            metrics_list = []
            for row in rows:
                try:
                    metrics_dict = json.loads(row[0])
                    metrics = self._dict_to_metrics(metrics_dict)
                    metrics_list.append(metrics)
                except Exception as e:
                    logger.warning(
                        "sync_metrics_deserialization_failed",
                        error=str(e),
                        severity="operational",
                    )

            return metrics_list

        except Exception as e:
            logger.error(
                "sync_metrics_list_by_date_failed",
                error=str(e),
                backend_type=backend_type,
                days=days,
                severity="operational",
            )
            return []

    def get_by_operation_id(self, operation_id: str) -> SyncMetrics | None:
        """Get metrics for a specific operation ID.

        Args:
            operation_id: The operation ID to look up

        Returns:
            SyncMetrics if found, None otherwise
        """
        try:
            conn = self.db_manager._get_connection()

            cursor = conn.execute(
                "SELECT metrics_json FROM sync_metrics WHERE operation_id = ? LIMIT 1",
                (operation_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            metrics_dict = json.loads(row[0])
            return self._dict_to_metrics(metrics_dict)

        except Exception as e:
            logger.error(
                "sync_metrics_get_by_operation_id_failed",
                error=str(e),
                operation_id=operation_id,
                severity="operational",
            )
            return None

    def get_statistics(
        self, backend_type: str | None = None, days: int = 30
    ) -> dict[str, Any]:
        """Get aggregate statistics for sync metrics.

        Args:
            backend_type: Optional filter by backend type
            days: Number of days to analyze (default: 30)

        Returns:
            Dictionary with statistics
        """
        try:
            conn = self.db_manager._get_connection()
            cutoff_date = (datetime.now(UTC) - timedelta(days=days)).isoformat()

            query = "SELECT metrics_json FROM sync_metrics WHERE created_at >= ?"
            params = [cutoff_date]

            if backend_type:
                query += " AND backend_type = ?"
                params.append(backend_type)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                return {
                    "total_syncs": 0,
                    "avg_duration_seconds": 0.0,
                    "total_duplicates_detected": 0,
                    "total_conflicts_detected": 0,
                    "total_errors": 0,
                }

            total_duration = 0.0
            total_duplicates = 0
            total_conflicts = 0
            total_errors = 0
            total_syncs = 0

            for row in rows:
                try:
                    metrics_dict = json.loads(row[0])
                    total_duration += metrics_dict.get("duration_seconds", 0.0)
                    total_duplicates += metrics_dict.get("duplicates_detected", 0)
                    total_conflicts += metrics_dict.get("conflicts_detected", 0)
                    total_errors += metrics_dict.get("errors_count", 0)
                    total_syncs += 1
                except Exception as e:
                    logger.warning(
                        "sync_metrics_stats_parse_failed",
                        error=str(e),
                        severity="operational",
                    )

            return {
                "total_syncs": total_syncs,
                "avg_duration_seconds": (
                    total_duration / total_syncs if total_syncs > 0 else 0.0
                ),
                "total_duplicates_detected": total_duplicates,
                "total_conflicts_detected": total_conflicts,
                "total_errors": total_errors,
                "backends": backend_type or "all",
                "period_days": days,
            }

        except Exception as e:
            logger.error(
                "sync_metrics_get_statistics_failed",
                error=str(e),
                backend_type=backend_type,
                days=days,
                severity="operational",
            )
            return {}

    def delete_old_metrics(self, days: int = 90) -> int:
        """Delete metrics older than N days.

        Args:
            days: Number of days to keep (default: 90)

        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = (datetime.now(UTC) - timedelta(days=days)).isoformat()

            with self.db_manager.transaction() as conn:
                cursor = conn.execute(
                    "DELETE FROM sync_metrics WHERE created_at < ?",
                    (cutoff_date,),
                )
                deleted_count = cursor.rowcount

            logger.info(
                "sync_metrics_old_records_deleted",
                deleted_count=deleted_count,
                days=days,
            )
            return deleted_count

        except Exception as e:
            logger.error(
                "sync_metrics_delete_old_failed",
                error=str(e),
                days=days,
                severity="operational",
            )
            return 0

    @staticmethod
    def _dict_to_metrics(metrics_dict: dict[str, Any]) -> SyncMetrics:
        """Convert dictionary back to SyncMetrics object.

        Args:
            metrics_dict: Dictionary from metrics_json

        Returns:
            SyncMetrics object
        """
        # Extract main fields
        metrics = SyncMetrics(
            operation_id=metrics_dict.get("operation_id", ""),
            backend_type=metrics_dict.get("backend_type", ""),
        )

        # Set all tracked fields from dictionary
        for key, value in metrics_dict.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)

        return metrics
