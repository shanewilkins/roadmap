"""Service for matching remote issues to local issues based on similarity."""

from difflib import SequenceMatcher
from typing import Any

from roadmap.common.logging import get_logger
from roadmap.core.domain.issue import Issue

logger = get_logger(__name__)


class IssueMatchingService:
    """Matches remote issues to local issues using title/content similarity."""

    # Similarity thresholds
    AUTO_LINK_THRESHOLD = 0.90  # 90% - auto-link without prompting
    POTENTIAL_DUPLICATE_THRESHOLD = 0.70  # 70-90% - flag for review
    # <70% - create as new issue

    def __init__(self, local_issues: list[Issue]):
        """Initialize matcher with local issues.

        Args:
            local_issues: List of local Issue objects to match against
        """
        self.local_issues = local_issues
        self.local_issues_by_id = {issue.id: issue for issue in local_issues}

    def find_best_match(
        self, remote_issue: dict[str, Any]
    ) -> tuple[Issue | None, float, str]:
        """Find best matching local issue for a remote issue.

        Args:
            remote_issue: Remote issue data dict with 'title' and optionally 'description'

        Returns:
            Tuple of (matched_issue, similarity_score, match_type)
            where match_type is 'auto_link', 'potential_duplicate', or 'new'
        """
        if not self.local_issues:
            return None, 0.0, "new"

        remote_title = remote_issue.get("title", "").lower().strip()
        if not remote_title:
            return None, 0.0, "new"

        best_match = None
        best_score = 0.0

        for local_issue in self.local_issues:
            score = self._calculate_similarity(remote_title, local_issue)
            if score > best_score:
                best_score = score
                best_match = local_issue

        # Determine match type based on score
        if best_score >= self.AUTO_LINK_THRESHOLD:
            return best_match, best_score, "auto_link"
        elif best_score >= self.POTENTIAL_DUPLICATE_THRESHOLD:
            return best_match, best_score, "potential_duplicate"
        else:
            return None, best_score, "new"

    def find_matches_batch(self, remote_issues: list[dict[str, Any]]) -> dict[str, Any]:
        """Find matches for a batch of remote issues.

        Args:
            remote_issues: List of remote issue dicts

        Returns:
            Dict with keys 'auto_link', 'potential_duplicate', 'new'
            Each containing lists of (remote_issue, local_match, score) tuples
        """
        results = {"auto_link": [], "potential_duplicate": [], "new": []}

        for remote_issue in remote_issues:
            match, score, match_type = self.find_best_match(remote_issue)
            results[match_type].append((remote_issue, match, score))

        return results

    def _calculate_similarity(self, remote_title: str, local_issue: Issue) -> float:
        """Calculate similarity between remote title and local issue.

        Args:
            remote_title: Remote issue title (already lowercased)
            local_issue: Local Issue object

        Returns:
            Similarity score between 0.0 and 1.0
        """
        local_title = local_issue.title.lower().strip() if local_issue.title else ""

        if not local_title:
            return 0.0

        # Primary: exact title match or close title match
        title_score = SequenceMatcher(None, remote_title, local_title).ratio()

        # Secondary: check content/description similarity (lower weight)
        content_score = 0.0
        if local_issue.content:
            remote_content = ""
            local_content = local_issue.content.lower().strip()

            # Use first 200 chars of description for matching
            if len(remote_title) < 100:
                remote_content = remote_title  # For short titles, use the title itself
            else:
                remote_content = remote_title[:200].lower()

            if local_content:
                content_score = (
                    SequenceMatcher(None, remote_content, local_content).ratio() * 0.3
                )  # Lower weight for content

        # Combined score (title weight: 70%, content weight: 30%)
        combined_score = (title_score * 0.7) + content_score

        return combined_score
