"""Unit tests for ValidationCoordinator behavior."""

from types import SimpleNamespace
from typing import Any, cast

import pytest

from roadmap.common.errors.exceptions import RoadmapException
from roadmap.core.services import GitHubIntegrationService
from roadmap.infrastructure.coordination.validation_coordinator import (
    ValidationCoordinator,
)


@pytest.fixture
def coordinator_with_core():
    """Build coordinator with a lightweight core/db remote link stub."""
    remote_links = SimpleNamespace(
        get_all_links_for_backend=lambda _backend: {"A": 1, "B": 2},
        link_issue=lambda *args: True,
        unlink_issue=lambda *_args: True,
    )
    core = SimpleNamespace(db=SimpleNamespace(remote_links=remote_links))
    github_service = cast(
        GitHubIntegrationService,
        SimpleNamespace(get_github_config=lambda: ("t", "o", "r")),
    )
    return ValidationCoordinator(
        github_service=github_service, core=cast(Any, core)
    ), core


def test_get_github_config_passthrough(coordinator_with_core):
    """Coordinator should delegate github config retrieval to service."""
    coordinator, _ = coordinator_with_core
    assert coordinator.get_github_config() == ("t", "o", "r")


def test_collect_remote_link_validation_data_handles_missing_directory(
    tmp_path, coordinator_with_core
):
    """Missing issues dir should still return db data and zero files."""
    coordinator, _ = coordinator_with_core
    data = coordinator.collect_remote_link_validation_data(tmp_path / "missing")

    assert data["total_files"] == 0
    assert data["yaml_remote_ids"] == {}
    assert data["db_links"] == {"A": 1, "B": 2}


def test_build_remote_link_report_detects_missing_extra_and_duplicates(
    coordinator_with_core,
):
    """Report should identify set mismatches and duplicate remote IDs."""
    coordinator, _ = coordinator_with_core

    yaml_remote_ids = {
        "A": {"github": 10},
        "C": {"github": 30},
    }
    db_links = {
        "A": 10,
        "B": 10,
        "D": 40,
    }

    report = coordinator.build_remote_link_report(yaml_remote_ids, db_links)

    assert set(report["missing_in_db"]) == {"C"}
    assert set(report["extra_in_db"]) == {"B", "D"}
    assert report["duplicate_remote_ids"] == {"10": ["A", "B"]}


def test_apply_remote_link_fixes_dry_run_returns_counts_without_mutation(
    coordinator_with_core,
):
    """Dry-run mode should compute counts while skipping db writes."""
    coordinator, core = coordinator_with_core

    link_calls = []
    unlink_calls = []

    core.db.remote_links.link_issue = lambda *args: link_calls.append(args)
    core.db.remote_links.unlink_issue = lambda *args: unlink_calls.append(args)

    yaml_remote_ids = {"X": {"github": 99}}
    report = {
        "missing_in_db": ["X"],
        "extra_in_db": ["Y"],
        "duplicate_remote_ids": {"99": ["X", "Y"]},
    }

    result = coordinator.apply_remote_link_fixes(
        yaml_remote_ids=yaml_remote_ids,
        report=report,
        prune_extra=True,
        dedupe=True,
        dry_run=True,
    )

    assert result == {"fixed_count": 1, "removed_count": 1, "deduped_count": 1}
    assert link_calls == []
    assert unlink_calls == []


def test_collect_remote_link_validation_data_requires_core(tmp_path):
    """Coordinator should fail fast when core-dependent methods are used without core."""
    coordinator = ValidationCoordinator(
        github_service=cast(GitHubIntegrationService, SimpleNamespace()),
        core=None,
    )

    with pytest.raises(RoadmapException, match="requires RoadmapCore"):
        coordinator.collect_remote_link_validation_data(tmp_path)
