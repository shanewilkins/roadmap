"""Bounded GitHub publication through the user's gh authentication."""

import json
import subprocess  # nosec B404
from typing import Any

from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.use_cases.github_publish import ClosurePublication


def _issue_state(issue: Any, publication: ClosurePublication) -> str:
    expected_url = (
        f"https://github.com/{publication.repository}/issues/{publication.number}"
    )
    if (
        not isinstance(issue, dict)
        or "pull_request" in issue
        or issue.get("state") not in {"open", "closed"}
        or issue.get("number") != publication.number
        or str(issue.get("html_url", "")).casefold() != expected_url.casefold()
    ):
        raise ApplicationFailure(
            FailureCategory.INVALID_REQUEST,
            "GitHub target identity/state does not match the requested issue",
        )
    return issue["state"]


def _has_evidence(pages: Any, marker: str) -> bool:
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise ApplicationFailure(
            FailureCategory.INVALID_REQUEST, "Invalid GitHub comments response"
        )
    comments = [comment for page in pages for comment in page]
    if any(
        not isinstance(comment, dict) or not isinstance(comment.get("body"), str)
        for comment in comments
    ):
        raise ApplicationFailure(
            FailureCategory.INVALID_REQUEST, "Invalid GitHub comment record"
        )
    return any(marker in comment["body"] for comment in comments)


class GhClosurePublisher:
    """No shell, local receipts, reopening, or general reconciliation."""

    def _api(
        self,
        endpoint: str,
        *,
        payload: dict[str, str] | None = None,
        paginate: bool = False,
        method: str = "POST",
    ) -> Any:
        arguments = ["gh", "api", "--hostname", "github.com", endpoint]
        if payload is not None:
            arguments.extend(["--method", method, "--input", "-"])
        if paginate:
            arguments.extend(["--paginate", "--slurp"])
        try:
            result = subprocess.run(  # nosec B603
                arguments,
                input=json.dumps(payload) if payload is not None else None,
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
            return json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            raise ApplicationFailure(
                FailureCategory.STORAGE_UNAVAILABLE,
                f"GitHub publication failed at {endpoint}; correct authentication/access or retry. Earlier publications may have succeeded.",
            ) from error

    def publish(self, publication: ClosurePublication) -> str:
        endpoint = f"repos/{publication.repository}/issues/{publication.number}"
        issue = self._api(endpoint)
        if _issue_state(issue, publication) == "closed":
            return "already-closed"
        pages = self._api(f"{endpoint}/comments?per_page=100", paginate=True)
        if not _has_evidence(pages, publication.marker):
            self._api(f"{endpoint}/comments", payload={"body": publication.comment})
        result = self._api(
            endpoint,
            method="PATCH",
            payload={"state": "closed", "state_reason": publication.disposition},
        )
        if not isinstance(result, dict) or result.get("state") != "closed":
            raise ApplicationFailure(
                FailureCategory.STORAGE_UNAVAILABLE,
                "GitHub did not confirm issue closure; retry publication",
            )
        return "closed"
