"""Real transport argv, pagination, and interrupted publication retry."""

import json
import subprocess
from unittest.mock import patch

import pytest

from roadmap.adapters.outbound.github import GhClosurePublisher
from roadmap.application.failures import ApplicationFailure
from roadmap.application.use_cases.github_publish import ClosurePublication

PUBLICATION = ClosurePublication(
    "local",
    "owner/repo",
    3756,
    "not_planned",
    "https://github.com/owner/repo/blob/abc/.roadmap/issues/local.md",
    "<!-- marker -->",
    "<!-- marker -->\nVerified not reproducible",
)


def response(value):
    if isinstance(value, dict) and "state" in value:
        value = {
            "number": 3756,
            "html_url": "https://github.com/owner/repo/issues/3756",
            **value,
        }
    return subprocess.CompletedProcess([], 0, json.dumps(value), "")


def test_transport_paginates_posts_json_and_closes_with_disposition():
    with patch(
        "roadmap.adapters.outbound.github.subprocess.run",
        side_effect=[
            response({"state": "open"}),
            response([[], []]),
            response({"id": 1}),
            response({"state": "closed"}),
        ],
    ) as run:
        assert GhClosurePublisher().publish(PUBLICATION) == "closed"
    calls = run.call_args_list
    assert calls[0].args[0][:4] == ["gh", "api", "--hostname", "github.com"]
    assert calls[1].args[0][-2:] == ["--paginate", "--slurp"]
    assert json.loads(calls[2].kwargs["input"]) == {"body": PUBLICATION.comment}
    assert "POST" in calls[2].args[0]
    assert "PATCH" in calls[3].args[0]
    assert json.loads(calls[3].kwargs["input"]) == {
        "state": "closed",
        "state_reason": "not_planned",
    }
    assert all(call.kwargs["timeout"] == 60 for call in calls)


def test_failed_close_after_comment_retries_without_duplicate_comment():
    failure = subprocess.CalledProcessError(1, "gh")
    with patch(
        "roadmap.adapters.outbound.github.subprocess.run",
        side_effect=[
            response({"state": "open"}),
            response([[]]),
            response({"id": 1}),
            failure,
            response({"state": "open"}),
            response([[], [{"body": PUBLICATION.comment}]]),
            response({"state": "closed"}),
            response({"state": "closed"}),
        ],
    ) as run:
        publisher = GhClosurePublisher()
        with pytest.raises(ApplicationFailure, match="retry"):
            publisher.publish(PUBLICATION)
        assert publisher.publish(PUBLICATION) == "closed"
        assert publisher.publish(PUBLICATION) == "already-closed"
    assert sum("POST" in call.args[0] for call in run.call_args_list) == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"pull_request": {}, "state": "open"},
        {"state": "unknown"},
        [],
        {"state": "open", "number": 1},
        {"state": "open", "html_url": "https://github.com/other/repo/issues/3756"},
    ],
)
def test_non_issue_target_is_rejected_before_writes(bad):
    with patch(
        "roadmap.adapters.outbound.github.subprocess.run", return_value=response(bad)
    ) as run:
        with pytest.raises(ApplicationFailure):
            GhClosurePublisher().publish(PUBLICATION)
        assert run.call_count == 1


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError(),
        subprocess.TimeoutExpired("gh", 60),
        subprocess.CalledProcessError(1, "gh"),
    ],
)
def test_transport_failure_is_visible(error):
    with patch("roadmap.adapters.outbound.github.subprocess.run", side_effect=error):
        with pytest.raises(ApplicationFailure, match="GitHub publication failed"):
            GhClosurePublisher().publish(PUBLICATION)


@pytest.mark.parametrize("pages", [{}, [None], [[{}]], [[{"body": None}]]])
def test_invalid_comments_stop_before_writes(pages):
    with patch(
        "roadmap.adapters.outbound.github.subprocess.run",
        side_effect=[
            response({"state": "open"}),
            response(pages),
        ],
    ) as run:
        with pytest.raises(ApplicationFailure, match="Invalid GitHub comment"):
            GhClosurePublisher().publish(PUBLICATION)
        assert run.call_count == 2


def test_unconfirmed_close_fails_visibly():
    with patch(
        "roadmap.adapters.outbound.github.subprocess.run",
        side_effect=[
            response({"state": "open"}),
            response([[{"body": PUBLICATION.comment}]]),
            response({"state": "open"}),
        ],
    ):
        with pytest.raises(ApplicationFailure, match="did not confirm"):
            GhClosurePublisher().publish(PUBLICATION)


def test_malformed_remote_json_fails_visibly():
    with patch(
        "roadmap.adapters.outbound.github.subprocess.run",
        return_value=subprocess.CompletedProcess([], 0, "not JSON", ""),
    ):
        with pytest.raises(ApplicationFailure, match="GitHub publication failed"):
            GhClosurePublisher().publish(PUBLICATION)
