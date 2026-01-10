from collections.abc import Iterable
from typing import Any


class RemoteFetcher:
    """Utility for fetching remote issue data via an adapter.

    Prefer batch APIs (`pull_issues`) when available; fall back to
    per-item APIs (`pull_issue`) otherwise.
    """

    @staticmethod
    def fetch_issue(adapter: Any, issue_id: str) -> Any:
        if adapter is None:
            return None

        if hasattr(adapter, "pull_issue"):
            try:
                return adapter.pull_issue(issue_id)
            except Exception:
                return None

        return None

    @staticmethod
    def fetch_issues(adapter: Any, issue_ids: Iterable[str]) -> list[Any]:
        if adapter is None:
            return []

        ids = list(issue_ids)
        if not ids:
            return []

        if hasattr(adapter, "pull_issues"):
            try:
                return adapter.pull_issues(ids) or []
            except Exception:
                return []

        # Fallback to single calls
        results: list[Any] = []
        for i in ids:
            try:
                r = RemoteFetcher.fetch_issue(adapter, i)
                results.append(r)
            except Exception:
                results.append(None)
        return results
