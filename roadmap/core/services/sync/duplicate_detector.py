"""Duplicate detection for sync operations.

This module provides duplicate detection strategies to identify issues that may
represent the same entity across local and remote systems. Detects ID collisions,
title duplicates, and content duplicates using various similarity metrics.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum

from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue


class MatchType(str, Enum):
    """Type of duplicate match detected."""

    ID_COLLISION = "id_collision"  # Same ID, different content
    TITLE_EXACT = "title_exact"  # Exact title match
    TITLE_SIMILAR = "title_similar"  # >90% title similarity
    CONTENT_SIMILAR = "content_similar"  # >85% content similarity


class RecommendedAction(str, Enum):
    """Recommended action for handling a duplicate match."""

    AUTO_MERGE = "auto_merge"  # High confidence, can auto-resolve
    MANUAL_REVIEW = "manual_review"  # Requires human judgment
    SKIP = "skip"  # Low confidence, likely false positive


@dataclass
class DuplicateMatch:
    """Represents a potential duplicate between local and remote issues.

    Attributes:
        local_issue: The local Issue object
        remote_issue: The remote SyncIssue object
        match_type: Type of duplicate detected
        confidence: Confidence score (0.0 to 1.0)
        recommended_action: Suggested action for handling this match
        similarity_details: Additional details about the match
    """

    local_issue: Issue
    remote_issue: SyncIssue
    match_type: MatchType
    confidence: float
    recommended_action: RecommendedAction
    similarity_details: dict[str, float | str] | None = None

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )


class DuplicateDetector:
    """Detects potential duplicates between local and remote issues.

    Uses multiple detection strategies:
    - ID collision detection (same GitHub number, different content)
    - Title matching (exact and fuzzy)
    - Content similarity (using SequenceMatcher)
    """

    def __init__(
        self,
        title_similarity_threshold: float = 0.90,
        content_similarity_threshold: float = 0.85,
        auto_resolve_threshold: float = 0.95,
    ) -> None:
        """Initialize duplicate detector with configurable thresholds.

        Args:
            title_similarity_threshold: Minimum similarity for title duplicates (default: 0.90)
            content_similarity_threshold: Minimum similarity for content duplicates (default: 0.85)
            auto_resolve_threshold: Minimum confidence for auto-resolution (default: 0.95)
        """
        self.title_similarity_threshold = title_similarity_threshold
        self.content_similarity_threshold = content_similarity_threshold
        self.auto_resolve_threshold = auto_resolve_threshold

    def detect_all(
        self, local_issues: list[Issue], remote_issues: dict[str, SyncIssue]
    ) -> list[DuplicateMatch]:
        """Run all detection strategies and return all matches.

        Args:
            local_issues: List of local Issue objects
            remote_issues: Dictionary mapping remote IDs to SyncIssue objects

        Returns:
            List of DuplicateMatch objects, sorted by confidence (highest first)
        """
        matches: list[DuplicateMatch] = []

        for local_issue in local_issues:
            # Check for ID collisions first (highest priority)
            id_matches = self._detect_id_collisions(local_issue, remote_issues)
            matches.extend(id_matches)

            # Check for title duplicates
            title_matches = self._detect_title_duplicates(local_issue, remote_issues)
            matches.extend(title_matches)

            # Check for content duplicates (most expensive, do last)
            content_matches = self._detect_content_duplicates(
                local_issue, remote_issues
            )
            matches.extend(content_matches)

        # Remove duplicate matches (same local/remote pair)
        matches = self._deduplicate_matches(matches)

        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)

        return matches

    def _detect_id_collisions(
        self, local_issue: Issue, remote_issues: dict[str, SyncIssue]
    ) -> list[DuplicateMatch]:
        """Detect ID collisions (same GitHub number, different content).

        Args:
            local_issue: Local issue to check
            remote_issues: Dictionary of remote issues

        Returns:
            List of DuplicateMatch objects for ID collisions
        """
        matches: list[DuplicateMatch] = []

        # Check if local issue has a GitHub remote link
        if not local_issue.remote_ids or "github" not in local_issue.remote_ids:
            return matches

        # Extract GitHub issue number
        github_number = local_issue.remote_ids.get("github")
        if not github_number:
            return matches

        # Check if remote has an issue with the same number
        for remote_id, remote_issue in remote_issues.items():
            remote_number = (
                remote_issue.backend_id
                if remote_issue.backend_name == "github"
                else None
            )
            if remote_number == github_number:
                # Found ID collision - same number, check if content differs
                title_similarity = self._calculate_text_similarity(
                    local_issue.title, remote_issue.title
                )
                content_similarity = self._calculate_text_similarity(
                    local_issue.content or "",
                    getattr(remote_issue, "headline", "") or "",
                )

                # If content is significantly different, it's a collision
                if title_similarity < 0.80 or content_similarity < 0.80:
                    matches.append(
                        DuplicateMatch(
                            local_issue=local_issue,
                            remote_issue=remote_issue,
                            match_type=MatchType.ID_COLLISION,
                            confidence=1.0,  # ID collision is definitive
                            recommended_action=RecommendedAction.MANUAL_REVIEW,
                            similarity_details={
                                "github_number": github_number,
                                "title_similarity": title_similarity,
                                "content_similarity": content_similarity,
                            },
                        )
                    )

        return matches

    def _detect_title_duplicates(
        self, local_issue: Issue, remote_issues: dict[str, SyncIssue]
    ) -> list[DuplicateMatch]:
        """Detect title duplicates (exact match or >90% similarity).

        Args:
            local_issue: Local issue to check
            remote_issues: Dictionary of remote issues

        Returns:
            List of DuplicateMatch objects for title duplicates
        """
        matches: list[DuplicateMatch] = []
        local_title = local_issue.title.strip().lower()

        for remote_id, remote_issue in remote_issues.items():
            remote_title = remote_issue.title.strip().lower()

            # Check for exact match
            if local_title == remote_title:
                matches.append(
                    DuplicateMatch(
                        local_issue=local_issue,
                        remote_issue=remote_issue,
                        match_type=MatchType.TITLE_EXACT,
                        confidence=0.98,  # High confidence for exact match
                        recommended_action=RecommendedAction.AUTO_MERGE,
                        similarity_details={
                            "title_similarity": 1.0,
                            "match_reason": "exact_title_match",
                        },
                    )
                )
            else:
                # Check for fuzzy match
                similarity = self._calculate_text_similarity(
                    local_issue.title, remote_issue.title
                )

                if similarity >= self.title_similarity_threshold:
                    # Determine action based on confidence
                    action = (
                        RecommendedAction.AUTO_MERGE
                        if similarity >= self.auto_resolve_threshold
                        else RecommendedAction.MANUAL_REVIEW
                    )

                    matches.append(
                        DuplicateMatch(
                            local_issue=local_issue,
                            remote_issue=remote_issue,
                            match_type=MatchType.TITLE_SIMILAR,
                            confidence=similarity,
                            recommended_action=action,
                            similarity_details={
                                "title_similarity": similarity,
                                "match_reason": "fuzzy_title_match",
                            },
                        )
                    )

        return matches

    def _detect_content_duplicates(
        self, local_issue: Issue, remote_issues: dict[str, SyncIssue]
    ) -> list[DuplicateMatch]:
        """Detect content duplicates (>85% text similarity).

        Args:
            local_issue: Local issue to check
            remote_issues: Dictionary of remote issues

        Returns:
            List of DuplicateMatch objects for content duplicates
        """
        matches: list[DuplicateMatch] = []

        # Skip if local issue has no content
        if not local_issue.content or not local_issue.content.strip():
            return matches

        # Skip if no content to compare
        local_content = local_issue.content.strip() if local_issue.content else ""

        for remote_id, remote_issue in remote_issues.items():
            # Get remote content (try headline or metadata)
            remote_content = ""
            if hasattr(remote_issue, "headline") and remote_issue.headline:
                remote_content = remote_issue.headline.strip()
            elif hasattr(remote_issue, "metadata") and remote_issue.metadata.get(
                "content"
            ):
                remote_content = remote_issue.metadata.get("content", "").strip()

            # Skip if remote issue has no content
            if not remote_content:
                continue

            # Calculate content similarity
            content_similarity = self._calculate_text_similarity(
                local_content, remote_content
            )

            if content_similarity >= self.content_similarity_threshold:
                # Also check title similarity for better confidence
                title_similarity = self._calculate_text_similarity(
                    local_issue.title, remote_issue.title
                )

                # Combined confidence: weighted average (60% content, 40% title)
                combined_confidence = (content_similarity * 0.6) + (
                    title_similarity * 0.4
                )

                # Determine action based on combined confidence
                action = (
                    RecommendedAction.AUTO_MERGE
                    if combined_confidence >= self.auto_resolve_threshold
                    else RecommendedAction.MANUAL_REVIEW
                )

                matches.append(
                    DuplicateMatch(
                        local_issue=local_issue,
                        remote_issue=remote_issue,
                        match_type=MatchType.CONTENT_SIMILAR,
                        confidence=combined_confidence,
                        recommended_action=action,
                        similarity_details={
                            "content_similarity": content_similarity,
                            "title_similarity": title_similarity,
                            "match_reason": "content_similarity",
                        },
                    )
                )

        return matches

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings using SequenceMatcher.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity ratio between 0.0 and 1.0
        """
        # Normalize whitespace and case
        text1 = " ".join(text1.lower().split())
        text2 = " ".join(text2.lower().split())

        # Use SequenceMatcher for similarity calculation
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()

    def _extract_github_number(self, github_link: str) -> str | None:
        """Extract GitHub issue number from a link or ID.

        Args:
            github_link: GitHub issue link or ID (e.g., "https://github.com/owner/repo/issues/123" or "#123")

        Returns:
            GitHub issue number as string, or None if not found
        """
        if not github_link:
            return None

        # Handle direct number format like "#123"
        if github_link.startswith("#"):
            return github_link[1:]

        # Handle full URL format
        parts = github_link.rstrip("/").split("/")
        if len(parts) >= 2 and parts[-2] == "issues":
            return parts[-1]

        return None

    def _deduplicate_matches(
        self, matches: list[DuplicateMatch]
    ) -> list[DuplicateMatch]:
        """Remove duplicate matches for the same local/remote pair.

        Keeps the match with highest confidence.

        Args:
            matches: List of DuplicateMatch objects

        Returns:
            Deduplicated list of matches
        """
        # Group by (local_id, remote_id) pair
        match_map: dict[tuple[str, str], DuplicateMatch] = {}

        for match in matches:
            key = (match.local_issue.id, match.remote_issue.id)

            # Keep match with higher confidence
            if key not in match_map or match.confidence > match_map[key].confidence:
                match_map[key] = match

        return list(match_map.values())
