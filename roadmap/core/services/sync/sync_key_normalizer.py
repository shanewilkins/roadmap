"""Helpers for normalizing remote keys to local UUIDs.

This module encapsulates the mapping logic previously embedded in
`SyncStateComparator._normalize_remote_keys`, allowing focused testing and
re-use by other components.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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
    normalized_remote: dict[str, Any] = {}

    # Build reverse mapping: remote_id -> local_uuid
    remote_id_to_local_uuid: dict[str, str] = {}
    db_lookup_available = False

    remote_link_repo = getattr(backend, "remote_link_repo", None)
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
            except Exception:
                pass

    # Supplement from local issues (YAML or in-memory) if DB is missing entries
    if not db_lookup_available or len(remote_id_to_local_uuid) < len(local):
        for local_uuid, local_issue in local.items():
            if (
                getattr(local_issue, "remote_ids", None)
                and backend_name in local_issue.remote_ids
            ):
                remote_id = local_issue.remote_ids[backend_name]
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
                        except Exception:
                            pass

    unmatched_remote: list[tuple[str, Any]] = []
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
                        source="database" if db_lookup_available else "yaml",
                    )
                except Exception:
                    pass
        else:
            unmatched_remote.append((remote_key, remote_issue))

    for remote_key, remote_issue in unmatched_remote:
        prefixed_key = f"_remote_{remote_key}"
        normalized_remote[prefixed_key] = remote_issue
        if logger is not None:
            try:
                logger.debug(
                    "new_remote_issue",
                    remote_key=str(remote_key),
                    prefixed_key=prefixed_key,
                )
            except Exception:
                pass

    if logger is not None:
        try:
            logger.info(
                "remote_keys_normalized",
                original_remote_count=len(remote),
                normalized_count=len(normalized_remote),
                matched=len(remote) - len(unmatched_remote),
                unmatched=len(unmatched_remote),
                backend=backend_name,
                db_lookup_used=db_lookup_available,
            )
        except Exception:
            pass

    return local, normalized_remote
