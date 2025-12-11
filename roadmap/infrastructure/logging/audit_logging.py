"""Audit logging utilities for tracking user actions and data changes.

Provides utilities to log auditable events with before/after state,
user identification, and change tracking for compliance and debugging.
"""

from datetime import datetime

from roadmap.common.logging import get_logger
from roadmap.infrastructure.logging.decorators import get_current_user

logger = get_logger(__name__)


def log_entity_created(
    entity_type: str,
    entity_id: str,
    entity_data: dict,
    reason: str | None = None,
) -> None:
    """Log entity creation for audit trail.

    Args:
        entity_type: Type of entity (issue, milestone, project)
        entity_id: ID of the created entity
        entity_data: Data of the created entity
        reason: Optional reason for creation
    """
    user = get_current_user()
    logger.info(
        "audit_entity_created",
        action="create",
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        entity_data=entity_data,
        reason=reason,
        timestamp=datetime.utcnow().isoformat(),
    )


def log_entity_updated(
    entity_type: str,
    entity_id: str,
    before_state: dict,
    after_state: dict,
    changed_fields: list[str] | None = None,
    reason: str | None = None,
) -> None:
    """Log entity update for audit trail.

    Args:
        entity_type: Type of entity
        entity_id: ID of the entity
        before_state: Entity state before update
        after_state: Entity state after update
        changed_fields: List of fields that changed (if known)
        reason: Reason for the update
    """
    user = get_current_user()

    # Calculate changed fields if not provided
    if changed_fields is None:
        changed_fields = [
            field
            for field in before_state
            if before_state.get(field) != after_state.get(field)
        ]

    logger.info(
        "audit_entity_updated",
        action="update",
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        before_state=before_state,
        after_state=after_state,
        changed_fields=changed_fields,
        reason=reason,
        timestamp=datetime.utcnow().isoformat(),
    )


def log_entity_deleted(
    entity_type: str,
    entity_id: str,
    entity_data: dict,
    deletion_method: str = "permanent",
    reason: str | None = None,
) -> None:
    """Log entity deletion for audit trail and recovery.

    Args:
        entity_type: Type of entity
        entity_id: ID of the deleted entity
        entity_data: Data of the deleted entity (for recovery)
        deletion_method: Method of deletion (permanent, archive, soft-delete)
        reason: Reason for deletion
    """
    user = get_current_user()
    logger.info(
        "audit_entity_deleted",
        action="delete",
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        deletion_method=deletion_method,
        entity_data=entity_data,
        reason=reason,
        timestamp=datetime.utcnow().isoformat(),
    )


def log_entity_archived(
    entity_type: str,
    entity_id: str,
    archive_location: str,
    retention_days: int | None = None,
    reason: str | None = None,
) -> None:
    """Log entity archival for audit trail.

    Args:
        entity_type: Type of entity
        entity_id: ID of the archived entity
        archive_location: Location where entity was archived
        retention_days: Days before archive cleanup
        reason: Reason for archival
    """
    user = get_current_user()
    logger.info(
        "audit_entity_archived",
        action="archive",
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        archive_location=archive_location,
        retention_days=retention_days,
        reason=reason,
        timestamp=datetime.utcnow().isoformat(),
    )


def log_entity_restored(
    entity_type: str,
    entity_id: str,
    from_location: str,
    to_location: str,
    reason: str | None = None,
) -> None:
    """Log entity restoration from archive for audit trail.

    Args:
        entity_type: Type of entity
        entity_id: ID of the restored entity
        from_location: Location it was restored from
        to_location: Location it was restored to
        reason: Reason for restoration
    """
    user = get_current_user()
    logger.info(
        "audit_entity_restored",
        action="restore",
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        from_location=from_location,
        to_location=to_location,
        reason=reason,
        timestamp=datetime.utcnow().isoformat(),
    )


def log_bulk_action(
    action: str,
    entity_type: str,
    count: int,
    selection_criteria: dict | None = None,
    reason: str | None = None,
) -> None:
    """Log bulk operations affecting multiple entities.

    Args:
        action: Action performed (archive, delete, update)
        entity_type: Type of entities
        count: Number of entities affected
        selection_criteria: Criteria used to select entities
        reason: Reason for the bulk action
    """
    user = get_current_user()
    logger.info(
        "audit_bulk_action",
        action=action,
        entity_type=entity_type,
        count=count,
        user=user,
        selection_criteria=selection_criteria,
        reason=reason,
        timestamp=datetime.utcnow().isoformat(),
    )


def log_state_transition(
    entity_type: str,
    entity_id: str,
    from_state: str,
    to_state: str,
    reason: str | None = None,
) -> None:
    """Log entity state transitions (status changes).

    Args:
        entity_type: Type of entity
        entity_id: ID of the entity
        from_state: Previous state/status
        to_state: New state/status
        reason: Reason for state change
    """
    user = get_current_user()
    logger.info(
        "audit_state_transition",
        entity_type=entity_type,
        entity_id=entity_id,
        user=user,
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        timestamp=datetime.utcnow().isoformat(),
    )


def generate_audit_report(
    entity_type: str,
    entity_id: str | None = None,
    user: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> dict:
    """Generate audit report for entity or user activity.

    Args:
        entity_type: Type of entity to report on
        entity_id: Specific entity ID (optional)
        user: Specific user to report on (optional)
        start_time: Report start time (optional)
        end_time: Report end time (optional)

    Returns:
        Report parameters (actual filtering done at log analysis level)
    """
    report = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "user": user,
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "generated_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        "audit_report_requested",
        **report,
    )

    return report
