from roadmap.core.services.sync_plan import (
    CreateLocalAction,
    LinkAction,
    PullAction,
    PushAction,
    ResolveConflictAction,
    SyncPlan,
    UpdateBaselineAction,
)


def test_actions_and_plan_describe():
    push = PushAction(issue_id="ISSUE-1", issue_payload={"title": "T1"})
    pull = PullAction(issue_id="ISSUE-2", remote_payload={"title": "Remote"})
    create = CreateLocalAction(remote_id="R123", remote_payload={"title": "New"})
    link = LinkAction(issue_id="ISSUE-1", backend_name="github", remote_id="42")
    update = UpdateBaselineAction(baseline_snapshot={"ISSUE-1": {"status": "todo"}})
    resolve = ResolveConflictAction(issue_id="ISSUE-2", resolution={"status": "todo"})

    plan = SyncPlan()
    plan.add(push)
    plan.add(pull)
    plan.add(create)
    plan.add(link)
    plan.add(update)
    plan.add(resolve)

    descriptions = plan.describe()
    assert any(d.startswith("push:") or d.startswith("push") for d in descriptions)
    assert any("ISSUE-1" in d for d in descriptions)
    assert plan.to_dict()["metadata"] == {}
