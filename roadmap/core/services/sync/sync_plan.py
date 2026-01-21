"""Lightweight Action and SyncPlan models for incremental sync refactor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Action:
    """Base action representing a single mutating operation to be applied by the Executor.

    This class is intentionally simple: it is a serializable carrier of the
    operation type and any payload necessary to perform it. Executors will
    implement the actual semantics of applying each action type.
    """

    action_type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def describe(self) -> str:
        """Human-readable description useful for dry-run previews."""
        # Keep concise and deterministic for testing
        payload_preview = {k: self.payload.get(k) for k in sorted(self.payload.keys())}
        return f"{self.action_type}: {payload_preview}"


@dataclass
class PushAction(Action):
    """Action to push a local issue to a remote backend."""

    def __init__(self, issue_id: str, issue_payload: Any = None):
        """Initialize PushAction.

        Args:
            issue_id: ID of the issue to push.
            issue_payload: Payload data for the issue.
        """
        super().__init__(
            action_type="push",
            payload={"issue_id": issue_id, "issue": issue_payload or {}},
        )


@dataclass
class PullAction(Action):
    """Action to pull remote changes for a local issue."""

    def __init__(self, issue_id: str, remote_payload: Any = None):
        """Initialize PullAction.

        Args:
            issue_id: ID of the issue to pull.
            remote_payload: Remote payload data.
        """
        super().__init__(
            action_type="pull",
            payload={"issue_id": issue_id, "remote": remote_payload or {}},
        )


@dataclass
class CreateLocalAction(Action):
    """Action to create a local issue from a remote entity."""

    def __init__(self, remote_id: str, remote_payload: Any = None):
        """Initialize CreateLocalAction.

        Args:
            remote_id: Remote ID of the issue.
            remote_payload: Remote payload data.
        """
        super().__init__(
            action_type="create_local",
            payload={"remote_id": remote_id, "remote": remote_payload or {}},
        )


@dataclass
class LinkAction(Action):
    """Action to link a local issue with a remote issue."""

    def __init__(self, issue_id: str, backend_name: str, remote_id: str):
        """Initialize LinkAction.

        Args:
            issue_id: Local issue ID.
            backend_name: Name of the backend.
            remote_id: Remote ID to link to.
        """
        super().__init__(
            action_type="link",
            payload={
                "issue_id": issue_id,
                "backend": backend_name,
                "remote_id": remote_id,
            },
        )


@dataclass
class UpdateBaselineAction(Action):
    """Action to update the baseline snapshot."""

    def __init__(self, baseline_snapshot: dict[str, Any]):
        """Initialize UpdateBaselineAction.

        Args:
            baseline_snapshot: Baseline snapshot to update.
        """
        super().__init__(
            action_type="update_baseline", payload={"baseline": baseline_snapshot}
        )


@dataclass
class ResolveConflictAction(Action):
    """Action to resolve a sync conflict for an issue."""

    def __init__(self, issue_id: str, resolution: dict[str, Any]):
        """Initialize ResolveConflictAction.

        Args:
            issue_id: ID of the issue with conflict.
            resolution: Resolution data for the conflict.
        """
        super().__init__(
            action_type="resolve_conflict",
            payload={"issue_id": issue_id, "resolution": resolution},
        )


@dataclass
class SyncPlan:
    """A collection of `Action`s representing the plan produced by the Analyzer.

    The `SyncPlan` is intentionally minimal: it stores ordered actions and a
    small metadata map that presenters or executors can consume.
    """

    actions: list[Action] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, action: Action) -> None:
        """Add an action to the sync plan.

        Args:
            action: The action to add.
        """
        self.actions.append(action)

    def describe(self) -> list[str]:
        """Get textual descriptions of all actions in the plan.

        Returns:
            List of action descriptions.
        """
        return [a.describe() for a in self.actions]

    def to_dict(self) -> dict[str, Any]:
        """Convert the sync plan to a dictionary representation.

        Returns:
            Dictionary with actions and metadata.
        """
        return {
            "actions": [
                {"type": a.action_type, "payload": a.payload} for a in self.actions
            ],
            "metadata": self.metadata,
        }
