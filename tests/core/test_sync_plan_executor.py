from typing import Any

from roadmap.core.services.sync_plan import (
    CreateLocalAction,
    LinkAction,
    PullAction,
    PushAction,
    ResolveConflictAction,
    SyncPlan,
    UpdateBaselineAction,
)
from roadmap.core.services.sync_plan_executor import SyncPlanExecutor


class FakeAdapter:
    def __init__(self):
        self.pushed = []
        self.pulled = []

    def push_issue(self, issue_payload):
        self.pushed.append(issue_payload)
        return True

    def pull_issue(self, issue_id):
        self.pulled.append(issue_id)
        return True

    def resolve_conflict(self, issue_id, resolution):
        return True


class FakeIssueService:
    def __init__(self):
        self.created = []

    def create_issue(self, data):
        new = type("Issue", (), {"id": f"i-{len(self.created)+1}"})()
        self.created.append((new, data))
        return new


class FakeCore:
    def __init__(self):
        self.issue_service = FakeIssueService()
        self.remote_link_repo: Any = None
        self.db = None


def make_plan():
    plan = SyncPlan()
    plan.add(CreateLocalAction(remote_id="r1", remote_payload={"title": "remote 1"}))
    plan.add(LinkAction(issue_id="i-1", backend_name="github", remote_id="r1"))
    plan.add(PushAction(issue_id="i-1", issue_payload={"title": "local"}))
    plan.add(PullAction(issue_id="r2", remote_payload={"title": "remote 2"}))
    plan.add(UpdateBaselineAction(baseline_snapshot={"issues": {}}))
    plan.add(ResolveConflictAction(issue_id="i-1", resolution={"use_local": True}))
    return plan


def test_execute_dry_run_no_side_effects():
    adapter = FakeAdapter()
    core = FakeCore()
    executor = SyncPlanExecutor(transport_adapter=adapter, core=core)
    plan = make_plan()

    report = executor.execute(plan, dry_run=True)

    # Dry-run should not apply pushes/pulls
    assert report.issues_pushed == 0
    assert report.issues_pulled == 0
    # Core should not have created any issues
    assert core.issue_service.created == []


def test_execute_apply_invokes_adapter_and_core():
    adapter = FakeAdapter()
    core = FakeCore()

    # Provide a dummy remote_link_repo to make linking call-through return True
    class DummyRepo:
        def link_issue(self, local_issue_id, backend_name, remote_issue_id):
            return True

    core.remote_link_repo = DummyRepo()

    executor = SyncPlanExecutor(transport_adapter=adapter, core=core)
    plan = make_plan()

    report = executor.execute(plan, dry_run=False)

    # Push and pull actions should be applied and counted
    assert report.issues_pushed == 1
    assert report.issues_pulled == 1
    # Core issue service should have created one issue
    assert len(core.issue_service.created) == 1
