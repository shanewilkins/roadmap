"""Repository for managing issue-to-backend remote ID mappings.

Provides fast lookups and mutations for remote backend IDs stored in the
issue_remote_links database table. This enables efficient sync operations
without scanning YAML files.
"""

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class RemoteLinkRepository:
    """Handles issue remote link database operations.

    Provides CRUD operations for tracking which issues are linked to
    which remote backend IDs (e.g., GitHub issue numbers, GitLab MRs, etc).
    """

    def __init__(self, get_connection, transaction):
        """Initialize repository with database connection methods.

        Args:
            get_connection: Callable that returns sqlite3 Connection
            transaction: Context manager for database transactions
        """
        self._get_connection = get_connection
        self._transaction = transaction

    def link_issue(
        self, issue_uuid: str, backend_name: str, remote_id: str | int
    ) -> bool:
        """Link an issue to a remote backend ID.

        Args:
            issue_uuid: Local issue UUID
            backend_name: Backend name (e.g., 'github', 'gitlab')
            remote_id: Remote ID in that backend (string or int)

        Returns:
            True if link created/updated, False if error
        """
        try:
            remote_id_str = str(remote_id)
            with self._transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO issue_remote_links
                    (issue_uuid, backend_name, remote_id)
                    VALUES (?, ?, ?)
                """,
                    (issue_uuid, backend_name, remote_id_str),
                )
            logger.debug(
                "Linked issue to remote backend",
                issue_uuid=issue_uuid,
                backend_name=backend_name,
                remote_id=remote_id_str,
            )
            return True
        except Exception as e:
            logger.warning(
                "Failed to link issue",
                issue_uuid=issue_uuid,
                backend_name=backend_name,
                remote_id=str(remote_id),
                error_type=type(e).__name__,
                error_message=str(e),
                error_details=repr(e),
            )
            return False

    def unlink_issue(self, issue_uuid: str, backend_name: str) -> bool:
        """Unlink an issue from a remote backend.

        Args:
            issue_uuid: Local issue UUID
            backend_name: Backend name

        Returns:
            True if unlinked, False if error or not found
        """
        try:
            with self._transaction() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM issue_remote_links
                    WHERE issue_uuid = ? AND backend_name = ?
                """,
                    (issue_uuid, backend_name),
                )
            if cursor.rowcount > 0:
                logger.debug(
                    "Unlinked issue from remote backend",
                    issue_uuid=issue_uuid,
                    backend_name=backend_name,
                )
                return True
            return False
        except Exception as e:
            logger.warning(
                "Failed to unlink issue",
                issue_uuid=issue_uuid,
                backend_name=backend_name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return False

    def get_remote_id(self, issue_uuid: str, backend_name: str) -> str | int | None:
        """Get the remote ID for an issue on a specific backend.

        Args:
            issue_uuid: Local issue UUID
            backend_name: Backend name (e.g., 'github')

        Returns:
            Remote ID (as string) or None if not linked
        """
        try:
            conn = self._get_connection()
            row = conn.execute(
                """
                SELECT remote_id FROM issue_remote_links
                WHERE issue_uuid = ? AND backend_name = ?
            """,
                (issue_uuid, backend_name),
            ).fetchone()
            if row:
                # Try to convert to int if it looks like one
                remote_id = row["remote_id"]
                try:
                    return int(remote_id)
                except (ValueError, TypeError):
                    return remote_id
            return None
        except Exception as e:
            logger.warning(
                "Failed to get remote ID",
                issue_uuid=issue_uuid,
                backend_name=backend_name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return None

    def get_issue_uuid(self, backend_name: str, remote_id: str | int) -> str | None:
        """Reverse lookup: get local issue UUID from remote backend ID.

        Args:
            backend_name: Backend name (e.g., 'github')
            remote_id: Remote ID in that backend

        Returns:
            Issue UUID or None if not found
        """
        try:
            remote_id_str = str(remote_id)
            conn = self._get_connection()
            row = conn.execute(
                """
                SELECT issue_uuid FROM issue_remote_links
                WHERE backend_name = ? AND remote_id = ?
            """,
                (backend_name, remote_id_str),
            ).fetchone()
            if row:
                return row["issue_uuid"]
            return None
        except Exception as e:
            logger.warning(
                "Failed to get issue UUID",
                backend_name=backend_name,
                remote_id=str(remote_id),
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return None

    def get_all_links_for_issue(self, issue_uuid: str) -> dict[str, str | int]:
        """Get all remote links for an issue (all backends).

        Args:
            issue_uuid: Local issue UUID

        Returns:
            Dict mapping backend_name -> remote_id
        """
        try:
            conn = self._get_connection()
            rows = conn.execute(
                """
                SELECT backend_name, remote_id FROM issue_remote_links
                WHERE issue_uuid = ?
            """,
                (issue_uuid,),
            ).fetchall()
            result = {}
            for row in rows:
                backend_name = row["backend_name"]
                remote_id_str = row["remote_id"]
                # Try to convert to int if it looks like one
                try:
                    result[backend_name] = int(remote_id_str)
                except (ValueError, TypeError):
                    result[backend_name] = remote_id_str
            return result
        except Exception as e:
            logger.warning(
                "Failed to get all links for issue",
                issue_uuid=issue_uuid,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return {}

    def get_all_links_for_backend(self, backend_name: str) -> dict[str, str | int]:
        """Get all remote links for a specific backend.

        Args:
            backend_name: Backend name (e.g., 'github')

        Returns:
            Dict mapping issue_uuid -> remote_id
        """
        try:
            conn = self._get_connection()
            rows = conn.execute(
                """
                SELECT issue_uuid, remote_id FROM issue_remote_links
                WHERE backend_name = ?
            """,
                (backend_name,),
            ).fetchall()
            result = {}
            for row in rows:
                issue_uuid = row["issue_uuid"]
                remote_id_str = row["remote_id"]
                # Try to convert to int if it looks like one
                try:
                    result[issue_uuid] = int(remote_id_str)
                except (ValueError, TypeError):
                    result[issue_uuid] = remote_id_str
            return result
        except Exception as e:
            logger.warning(
                "Failed to get all links for backend",
                backend_name=backend_name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return {}

    def validate_link(
        self, issue_uuid: str, backend_name: str, remote_id: str | int
    ) -> bool:
        """Check if a link is valid (exists and matches remote_id).

        Args:
            issue_uuid: Local issue UUID
            backend_name: Backend name
            remote_id: Expected remote ID

        Returns:
            True if link exists and matches, False otherwise
        """
        try:
            existing_id = self.get_remote_id(issue_uuid, backend_name)
            if existing_id is None:
                return False
            # Compare as strings to handle int/str variations
            return str(existing_id) == str(remote_id)
        except Exception as e:
            logger.warning(
                "Failed to validate link",
                issue_uuid=issue_uuid,
                backend_name=backend_name,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return False

    def bulk_import_from_yaml(
        self, issues_with_remote_ids: dict[str, dict[str, str | int]]
    ) -> int:
        """Bulk import remote links from Issue objects with remote_ids.

        This is typically called during initialization to sync existing
        remote_ids from YAML files into the database.

        Args:
            issues_with_remote_ids: Dict mapping issue_uuid -> dict of backend_name -> remote_id

        Returns:
            Number of links successfully imported
        """
        count = 0
        try:
            with self._transaction() as conn:
                for issue_uuid, remote_ids_dict in issues_with_remote_ids.items():
                    if not remote_ids_dict:
                        continue
                    for backend_name, remote_id in remote_ids_dict.items():
                        try:
                            remote_id_str = str(remote_id)
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO issue_remote_links
                                (issue_uuid, backend_name, remote_id)
                                VALUES (?, ?, ?)
                            """,
                                (issue_uuid, backend_name, remote_id_str),
                            )
                            count += 1
                        except Exception as e:
                            logger.debug(
                                "Failed to import link",
                                issue_uuid=issue_uuid,
                                backend_name=backend_name,
                                remote_id=remote_id_str,
                                error_type=type(e).__name__,
                                error_message=str(e),
                            )
            logger.info("Bulk imported remote links", count=count)
            return count
        except Exception as e:
            logger.error(
                "Bulk import of remote links failed",
                count_imported=count,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return count

    def clear_all(self) -> bool:
        """Clear all remote links (useful for resetting/testing).

        Returns:
            True if successful, False if error
        """
        try:
            with self._transaction() as conn:
                conn.execute("DELETE FROM issue_remote_links")
            logger.info("Cleared all remote links")
            return True
        except Exception as e:
            logger.error(
                "Failed to clear all remote links",
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return False
