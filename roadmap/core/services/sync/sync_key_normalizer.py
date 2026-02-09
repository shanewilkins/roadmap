"""Helpers for normalizing remote keys to local UUIDs.

This module encapsulates the mapping logic previously embedded in
`SyncStateComparator._normalize_remote_keys`, allowing focused testing and
re-use by other components.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import structlog

logger = structlog.get_logger()


def _build_remote_id_mapping(
    local: dict[str, Any],
    backend: Any,
    remote_link_repo: Any,
    logger: Any | None = None,
) -> tuple[dict[str, str], bool]:
    """Build reverse mapping from remote ID to local UUID.

    Returns:
        (remote_id_to_local_uuid dict, db_lookup_used bool)
    """
    remote_id_to_local_uuid: dict[str, str] = {}
    db_lookup_available = False
    backend_name = backend.get_backend_name()

    # Try database lookup first
    if remote_link_repo:
        db_lookup_available = True
        db_links = remote_link_repo.get_all_links_for_backend(backend_name)
        for issue_uuid, remote_id in db_links.items():
            remote_id_key = str(remote_id)
            remote_id_to_local_uuid[remote_id_key] = issue_uuid
        if logger is not None:
            try:
                logger.debug(
                    "loaded_remote_links_from_database",
                    backend=backend_name,
                    link_count=len(remote_id_to_local_uuid),
                )
            except Exception as logging_error:
                logger.error(
                    "logger_failed",
                    operation="log_remote_links_loaded",
                    error=str(logging_error),
                )

    # Supplement from YAML if DB is missing entries
    if not db_lookup_available or len(remote_id_to_local_uuid) < len(local):
        for local_uuid, local_issue in local.items():
            remote_ids = getattr(local_issue, "remote_ids", None)
            if remote_ids and backend_name in remote_ids:
                remote_id = remote_ids[backend_name]
                remote_id_key = str(remote_id)
                if remote_id_key not in remote_id_to_local_uuid:
                    remote_id_to_local_uuid[remote_id_key] = local_uuid
                    if logger is not None:
                        try:
                            logger.debug(
                                "loaded_remote_id_from_yaml",
                                remote_id=remote_id_key,
                                local_uuid=local_uuid,
                                backend=backend_name,
                            )
                        except Exception as logging_error:
                            logger.error(
                                "logger_failed",
                                operation="log_loaded_remote_id_from_yaml",
                                error=str(logging_error),
                            )

    return remote_id_to_local_uuid, db_lookup_available


def _apply_remote_normalization(
    remote: Mapping[str, Any],
    remote_id_to_local_uuid: dict[str, str],
    backend_name: str,
    logger: Any | None = None,
) -> tuple[dict[str, Any], int]:
    """Apply ID mapping to normalize remote issues.

    Returns:
        (normalized_remote dict, count of unmatched)
    """
    normalized_remote: dict[str, Any] = {}
    unmatched_count = 0

    # Partition remote issues into matched and unmatched
    for remote_key, remote_issue in remote.items():
        remote_key_str = str(remote_key)
        if remote_key_str in remote_id_to_local_uuid:
            local_uuid = remote_id_to_local_uuid[remote_key_str]
            normalized_remote[local_uuid] = remote_issue
            if logger is not None:
                try:
                    logger.debug(
                        "normalized_remote_key",
                        original_key=remote_key_str,
                        normalized_to=local_uuid,
                    )
                except Exception as logging_error:
                    logger.error(
                        "logger_failed",
                        operation="log_normalized_remote_key",
                        error=str(logging_error),
                    )
        else:
            prefixed_key = f"_remote_{remote_key}"
            normalized_remote[prefixed_key] = remote_issue
            unmatched_count += 1
            if logger is not None:
                try:
                    logger.debug(
                        "new_remote_issue",
                        remote_key=str(remote_key),
                        prefixed_key=prefixed_key,
                    )
                except Exception as logging_error:
                    logger.error(
                        "logger_failed",
                        operation="log_new_remote_issue",
                        error=str(logging_error),
                    )

    return normalized_remote, unmatched_count


def normalize_remote_keys(
    local: dict[str, Any],
    remote: Mapping[str, Any],
    backend: Any | None,
    logger: Any | None = None,
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    """Normalize remote issue keys to match local issue UUIDs.

    Returns (local, normalized_remote) where `normalized_remote` is keyed by
    local UUIDs where a mapping exists, and unmatched remote keys are
    preserved with a `_remote_{key}` prefix.
    """
    if backend is None:
        return local, remote

    backend_name = backend.get_backend_name()
    remote_link_repo = getattr(backend, "remote_link_repo", None)

    # Build ID mapping from DB + YAML
    remote_id_to_local_uuid, db_lookup_available = _build_remote_id_mapping(
        local, backend, remote_link_repo, logger
    )

    # Apply mapping to normalize remote
    normalized_remote, unmatched_count = _apply_remote_normalization(
        remote, remote_id_to_local_uuid, backend_name, logger
    )

    if logger is not None:
        try:
            logger.info(
                "remote_keys_normalized",
                original_remote_count=len(remote),
                normalized_count=len(normalized_remote),
                matched=len(remote) - unmatched_count,
                unmatched=unmatched_count,
                backend=backend_name,
                db_lookup_used=db_lookup_available,
            )
            if unmatched_count > 0 and not db_lookup_available:
                logger.warning(
                    "remote_keys_unmatched_no_db_links",
                    unmatched=unmatched_count,
                    backend=backend_name,
                    hint="remote issues appear unlinked to local IDs",
                )
        except Exception as logging_error:
            logger.error(
                "logger_failed",
                operation="log_remote_keys_normalized",
                error=str(logging_error),
            )

    return local, normalized_remote
