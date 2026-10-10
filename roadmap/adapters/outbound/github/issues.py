"""Read selected issues and every comments/timeline page through gh; never write GitHub."""

import json
import subprocess  # nosec B404
from typing import Any

from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.use_cases.github_import import (
    GitHubSource,
    invalid,
    validate_source,
)


class GhIssueSource:
    def _api(self, endpoint: str, *, paginate: bool = False) -> Any:
        arguments = ["gh", "api", "--hostname", "github.com", endpoint]
        if paginate:
            arguments.extend(["--paginate", "--slurp"])
        try:
            result = subprocess.run(
                arguments, capture_output=True, text=True, check=True, timeout=60
            )  # nosec B603
            return json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            raise ApplicationFailure(
                FailureCategory.STORAGE_UNAVAILABLE,
                f"GitHub extraction failed at {endpoint}; no local import performed. Check gh authentication/access and retry.",
            ) from error

    def _pages(self, endpoint: str) -> list[dict[str, Any]]:
        pages = self._api(endpoint, paginate=True)
        if not isinstance(pages, list) or any(
            not isinstance(page, list) for page in pages
        ):
            raise invalid("Invalid paginated GitHub response; no import performed")
        return [item for page in pages for item in page]

    def fetch(
        self, repository: str, numbers: tuple[int, ...]
    ) -> tuple[GitHubSource, ...]:
        sources = []
        for number in numbers:
            endpoint = f"repos/{repository}/issues/{number}"
            before = self._api(endpoint)
            comments = self._pages(endpoint + "/comments?per_page=100")
            timeline = self._pages(endpoint + "/timeline?per_page=100")
            after = self._api(endpoint)
            if before != after:
                raise invalid(
                    "GitHub issue changed during extraction; retry the entire batch"
                )
            sources.append(
                validate_source(
                    repository,
                    number,
                    {"issue": after, "comments": comments, "timeline": timeline},
                )
            )
        return tuple(sources)
