"""Stable regression envelope for the supported small-team dataset."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from time import perf_counter

from roadmap.adapters.outbound.persistence.diagnostics import (
    FilesystemWorkspaceDiagnostics,
)
from roadmap.adapters.outbound.persistence.documents import (
    DocumentEnvelope,
    DocumentRepository,
    serialize_document,
)
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.domain.aggregates import Issue
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    Priority,
    RetentionState,
    Timestamp,
    Title,
)
from tests.fixtures.integration_helpers import IntegrationTestBase

DATASET_SIZE = 500
MAX_SECONDS = {
    "projection_rebuild": 8.0,
    "filtered_lookup": 3.0,
    "daily_and_board": 8.0,
    "dependency_analysis": 8.0,
    "health_scan": 12.0,
    "json_export": 1.0,
}


def _measure(operation):
    started = perf_counter()
    result = operation()
    return result, perf_counter() - started


def _populate(roadmap_dir, milestone_id: EntityId) -> None:
    now = Timestamp(datetime(2026, 8, 26, 12, tzinfo=UTC))
    repository = DocumentRepository(roadmap_dir)
    for index in range(DATASET_SIZE):
        identity = EntityId(f"perf-{index:04d}")
        if index < 400:
            status = (
                IssueStatus.TODO,
                IssueStatus.IN_PROGRESS,
                IssueStatus.BLOCKED,
                IssueStatus.REVIEW,
            )[index % 4]
            retention = RetentionState.VISIBLE
        elif index < 450:
            status = IssueStatus.CLOSED
            retention = RetentionState.VISIBLE
        else:
            status = IssueStatus.CLOSED
            retention = RetentionState.ARCHIVED
        dependency = (EntityId(f"perf-{index - 1:04d}"),) if index else ()
        issue = Issue(
            identity,
            now,
            now,
            retention,
            title=Title(f"Performance issue {index:04d}"),
            priority=Priority.HIGH if index % 5 == 0 else Priority.MEDIUM,
            status=status,
            relations=IssueRelations(milestone_id, dependency),
            assignee="benchmark-user",
            estimated_hours=1.0,
        )
        path = repository.default_path("issue", issue)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(serialize_document(DocumentEnvelope("issue", issue, path, {})))


def test_supported_small_team_performance_envelope(cli_runner, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    IntegrationTestBase.init_roadmap(cli_runner)
    IntegrationTestBase.create_milestone(cli_runner, "performance-envelope")
    milestone = IntegrationTestBase.get_roadmap_core().milestones.get(
        "performance-envelope"
    )
    assert milestone is not None

    roadmap_dir = tmp_path / ".roadmap"
    _populate(roadmap_dir, milestone.id)
    repository = DocumentRepository(roadmap_dir)
    projection = SQLiteProjection(roadmap_dir / "db/projection.db", repository)
    timings = {}

    _, timings["projection_rebuild"] = _measure(projection.rebuild)
    rows, timings["filtered_lookup"] = _measure(lambda: projection.query("issue"))

    planning = IntegrationTestBase.get_roadmap_core().planning
    planning_views, timings["daily_and_board"] = _measure(
        lambda: (
            planning.daily_summary("benchmark-user"),
            planning.milestone(str(milestone.id)),
        )
    )
    critical_path, timings["dependency_analysis"] = _measure(
        lambda: planning.critical_path(
            milestone=str(milestone.id), include_closed=False
        )
    )
    diagnostics = FilesystemWorkspaceDiagnostics(repository, projection)
    health, timings["health_scan"] = _measure(diagnostics.scan)
    exported, timings["json_export"] = _measure(
        lambda: json.dumps(rows, ensure_ascii=False, sort_keys=True)
    )

    assert len(rows) == DATASET_SIZE
    assert planning_views[1].issue_count == 450
    assert planning_views[0].current_user == "benchmark-user"
    assert critical_path.critical_path
    assert health.exit_code == 0
    assert len(json.loads(exported)) == DATASET_SIZE
    assert {
        name: round(duration, 3)
        for name, duration in timings.items()
        if duration > MAX_SECONDS[name]
    } == {}, f"performance envelope exceeded: {timings}"
