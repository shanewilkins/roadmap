"""Duplicate detection for sync operations.

This module provides duplicate detection strategies to identify issues that may
represent the same entity across local and remote systems. Detects ID collisions,
title duplicates, and content duplicates using various similarity metrics.
"""

import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum

import structlog

from roadmap.common.union_find import UnionFind
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue

logger = structlog.get_logger()


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

        NOTE: This method expects deduplicated input sets (via local_self_dedup and
        remote_self_dedup) before being called for cross-comparison. Without dedup
        preprocessing, title matching can produce thousands of spurious matches.

        Args:
            local_issues: List of deduplicated local Issue objects
            remote_issues: Dictionary mapping remote IDs to deduplicated SyncIssue objects

        Returns:
            List of DuplicateMatch objects, sorted by confidence (highest first)
        """
        matches: list[DuplicateMatch] = []

        for local_issue in local_issues:
            # Check for ID collisions first (highest priority)
            # This catches: same GitHub issue number with different local ID
            id_matches = self._detect_id_collisions(local_issue, remote_issues)
            matches.extend(id_matches)

            # Title matching: now safe because input should be deduplicated via
            # local_self_dedup() and remote_self_dedup() in the orchestrator.
            # With deduplicated canonical sets (~100 issues each), this is O(100²) = 10K comparisons.
            # Without dedup, with 1800+ issues each, this would be O(3M+) and produce 80K+ false positives.
            title_matches = self._detect_title_duplicates(local_issue, remote_issues)
            matches.extend(title_matches)

            # NOTE: Content duplicate detection disabled - too expensive even with dedup
            # content_matches = self._detect_content_duplicates(
            #     local_issue, remote_issues
            # )
            # matches.extend(content_matches)

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
        for _remote_id, remote_issue in remote_issues.items():
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
        """Detect title duplicates (exact and fuzzy matching).

        NOTE: This method works well only when called with deduplicated inputs.
        Without dedup preprocessing, fuzzy matching can produce thousands of
        spurious matches with large datasets.

        Args:
            local_issue: Local issue to check
            remote_issues: Dictionary of remote issues

        Returns:
            List of DuplicateMatch objects for title duplicates
        """
        matches: list[DuplicateMatch] = []
        local_title = local_issue.title.strip().lower()

        for _remote_id, remote_issue in remote_issues.items():
            remote_title = remote_issue.title.strip().lower()

            # Check for exact match first
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
                continue

            # Check for fuzzy title match using SequenceMatcher
            # Safe to do here because input should be deduplicated
            similarity = SequenceMatcher(None, local_title, remote_title).ratio()

            if similarity >= self.title_similarity_threshold:
                matches.append(
                    DuplicateMatch(
                        local_issue=local_issue,
                        remote_issue=remote_issue,
                        match_type=MatchType.TITLE_SIMILAR,
                        confidence=similarity,
                        recommended_action=RecommendedAction.MANUAL_REVIEW,
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

        for _remote_id, remote_issue in remote_issues.items():
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

    def local_self_dedup(self, local_issues: list[Issue]) -> list[Issue]:
        """Deduplicate local issues by grouping canonical duplicates.

        Uses union-find to efficiently cluster duplicate issues within the local
        set. This reduces the number of issues before cross-comparing with remote.

        Args:
            local_issues: List of local issues to deduplicate.

        Returns:
            List of canonical representative issues (one per equivalence class).

        Performance:
            - Creates union-find: O(n)
            - Pairwise comparisons: O(n²) with early termination
            - Dedup output: O(n)
        """
        start_time = time.time()
        input_count = len(local_issues)

        if input_count == 0:
            return []

        # Build union-find with issue IDs
        issue_by_id = {id(issue): issue for issue in local_issues}
        uf = UnionFind(list(issue_by_id.keys()))

        id_collision_count = 0
        title_match_count = 0

        # Pairwise comparison for duplicates
        for i, issue1 in enumerate(local_issues):
            for issue2 in local_issues[i + 1 :]:
                # Check ID collision (same GitHub ID = definitely duplicate)
                github_id_1 = issue1.remote_ids.get("github")
                github_id_2 = issue2.remote_ids.get("github")
                if github_id_1 and github_id_1 == github_id_2:
                    uf.union(id(issue1), id(issue2))
                    id_collision_count += 1
                    continue

                # Check exact title match (strong indicator of duplicate)
                if issue1.title == issue2.title:
                    uf.union(id(issue1), id(issue2))
                    title_match_count += 1

        # Extract canonical representatives
        representatives = uf.get_representatives()
        canonical_issues = [
            issue_by_id[rep_id] for rep_id in representatives if rep_id in issue_by_id
        ]

        output_count = len(canonical_issues)
        elapsed_time = time.time() - start_time

        logger.info(
            "local_self_dedup: input=%d, id_collisions=%d, title_matches=%d, "
            "output=%d, time=%.2fs, reduction=%.1f%%",
            input_count,
            id_collision_count,
            title_match_count,
            output_count,
            elapsed_time,
            ((input_count - output_count) / input_count * 100)
            if input_count > 0
            else 0,
        )

        return canonical_issues

    def remote_self_dedup(
        self, remote_issues: dict[str, "SyncIssue"]
    ) -> dict[str, "SyncIssue"]:
        """Deduplicate remote issues by grouping canonical duplicates.

        Uses union-find to efficiently cluster duplicate issues within the remote
        set. This reduces the number of issues before comparing with local.

        Args:
            remote_issues: Dict of remote issue IDs to SyncIssue objects.

        Returns:
            Dict of canonical remote issues (one per equivalence class).

        Performance:
            - Creates union-find: O(n)
            - Pairwise comparisons: O(n²) with early termination
            - Dedup output: O(n)
        """
        start_time = time.time()
        input_count = len(remote_issues)

        if input_count == 0:
            return {}

        # Build union-find with remote issue IDs (strings)
        remote_id_list = list(remote_issues.keys())
        uf = UnionFind(remote_id_list)

        id_collision_count = 0
        title_match_count = 0

        # Pairwise comparison for duplicates
        for i, rid1 in enumerate(remote_id_list):
            for rid2 in remote_id_list[i + 1 :]:
                issue1 = remote_issues[rid1]
                issue2 = remote_issues[rid2]

                # Check ID collision (same backend ID = definitely duplicate)
                if issue1.backend_id and issue1.backend_id == issue2.backend_id:
                    uf.union(rid1, rid2)
                    id_collision_count += 1
                    continue

                # Check exact title match (strong indicator of duplicate)
                if issue1.title == issue2.title:
                    uf.union(rid1, rid2)
                    title_match_count += 1

        # Extract canonical representatives
        representatives = uf.get_representatives()
        canonical_remote = {rep_id: remote_issues[rep_id] for rep_id in representatives}

        output_count = len(canonical_remote)
        elapsed_time = time.time() - start_time

        logger.info(
            "remote_self_dedup: input=%d, id_collisions=%d, title_matches=%d, "
            "output=%d, time=%.2fs, reduction=%.1f%%",
            input_count,
            id_collision_count,
            title_match_count,
            output_count,
            elapsed_time,
            ((input_count - output_count) / input_count * 100)
            if input_count > 0
            else 0,
        )

        return canonical_remote
