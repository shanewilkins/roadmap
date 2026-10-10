"""Complete pagination and bounded failed extraction before local ingestion."""

import json
import subprocess
from unittest.mock import patch

import pytest

from roadmap.adapters.outbound.github.issues import GhIssueSource
from roadmap.application.failures import ApplicationFailure
from roadmap.application.use_cases.github_import import validate_source
from tests.integration.cli.test_cli_github_import import payload


def test_source_reads_all_pages_and_rechecks_issue_with_get_only():
    comment = {
        "id": 9,
        "body": "Second page",
        "user": None,
        "created_at": "2026-10-10T00:00:00Z",
        "updated_at": "2026-10-10T00:00:00Z",
        "html_url": "https://github.com/owner/repo/issues/1#issuecomment-9",
    }
    value = payload(comments=[comment])
    responses = [value["issue"], [[], [comment]], [[], []], value["issue"]]
    with patch(
        "roadmap.adapters.outbound.github.issues.subprocess.run",
        side_effect=[
            subprocess.CompletedProcess([], 0, json.dumps(item), "")
            for item in responses
        ],
    ) as runner:
        [source] = GhIssueSource().fetch("owner/repo", (1,))
    assert json.loads(source.payload)["comments"] == [comment]
    assert runner.call_count == 4
    for call in runner.call_args_list:
        args = call.args[0]
        assert args[:4] == ["gh", "api", "--hostname", "github.com"]
        assert "--method" not in args and "--input" not in args
        assert call.kwargs["timeout"] == 60
    assert "--paginate" in runner.call_args_list[1].args[0]
    assert "--slurp" in runner.call_args_list[2].args[0]


@pytest.mark.parametrize("stage", [0, 1, 2, 3])
def test_failed_fetch_is_visible_and_returns_no_partial_result(stage):
    value = payload()
    responses = [value["issue"], [[]], [[]], value["issue"]]
    calls: list[subprocess.CompletedProcess[str] | Exception] = [
        subprocess.CompletedProcess([], 0, json.dumps(item), "") for item in responses
    ]
    calls[stage] = subprocess.TimeoutExpired("gh", 60)
    with (
        patch(
            "roadmap.adapters.outbound.github.issues.subprocess.run", side_effect=calls
        ),
        pytest.raises(ApplicationFailure, match="no local import performed"),
    ):
        GhIssueSource().fetch("owner/repo", (1,))


def test_changed_issue_during_fetch_and_missing_comments_are_refused():
    value = payload()
    with (
        patch.object(
            GhIssueSource,
            "_api",
            side_effect=[
                value["issue"],
                [[]],
                [[]],
                {**value["issue"], "title": "Changed"},
            ],
        ),
        pytest.raises(ApplicationFailure, match="changed during extraction"),
    ):
        GhIssueSource().fetch("owner/repo", (1,))
    value["issue"]["comments"] = 1
    with pytest.raises(ApplicationFailure, match="incomplete"):
        validate_source("owner/repo", 1, value)


def test_fingerprint_is_stable_under_page_order_and_object_key_order():
    base = {
        "user": None,
        "created_at": "2026-10-10T00:00:00Z",
        "updated_at": "2026-10-10T00:00:00Z",
        "html_url": "https://github.com/owner/repo/issues/1",
    }
    comments = [
        {**base, "id": 2, "body": "Later"},
        {**base, "id": 1, "body": "Earlier"},
    ]
    first = validate_source("owner/repo", 1, payload(comments=comments))
    second = validate_source(
        "owner/repo", 1, payload(comments=list(reversed(comments)))
    )
    assert first.fingerprint == second.fingerprint
