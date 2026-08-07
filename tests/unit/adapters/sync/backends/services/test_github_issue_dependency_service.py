"""Unit tests for GitHubIssueDependencyService behavior."""

from __future__ import annotations

from types import SimpleNamespace

from roadmap.adapters.sync.backends.services.github_issue_dependency_service import (
    GitHubIssueDependencyService,
)
from roadmap.core.interfaces import SyncReport


def test_analyze_issue_dependencies_tracks_missing_and_milestones() -> None:
    service = GitHubIssueDependencyService()
    report = SyncReport()

    remote_issues = {
        "10": SimpleNamespace(id="10", milestone="v1"),
        "20": SimpleNamespace(id="20", milestone=None),
    }
    remote_milestones = {
        1: SimpleNamespace(name="v1"),
        2: SimpleNamespace(name="v2"),
    }

    issues_to_pull, milestones_needed, updated_report = (
        service.analyze_issue_dependencies(
            issue_ids=["_remote_10", "20", "99"],
            all_remote_issues=remote_issues,
            all_remote_milestones=remote_milestones,
            report=report,
        )
    )

    assert len(issues_to_pull) == 2
    assert issues_to_pull[0][0] == "_remote_10"
    assert issues_to_pull[0][1] == "10"
    assert issues_to_pull[1][1] == "20"
    assert milestones_needed == {1}
    assert updated_report.errors["99"] == "Issue not found on remote"


def test_find_milestone_number_returns_none_when_not_found() -> None:
    service = GitHubIssueDependencyService()

    result = service.find_milestone_number(
        "missing",
        {1: SimpleNamespace(name="v1")},
    )

    assert result is None
