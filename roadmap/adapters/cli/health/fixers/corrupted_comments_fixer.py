"""Fixer for corrupted comments (malformed JSON)."""

import json

import structlog

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer

logger = structlog.get_logger()


class CorruptedCommentsFixer(HealthFixer):
    """Sanitizes malformed JSON comments.

    Safety: REVIEW (modifies comment content)

    Attempts to fix or remove comments with invalid JSON.
    """

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "corrupted_comments"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - REVIEW because modifies comment content."""
        return FixSafety.REVIEW

    @property
    def description(self) -> str:
        """Return fixer description."""
        return "Sanitize malformed JSON in comments"

    def scan(self) -> dict:
        """Scan for corrupted comments.

        Returns:
            Dict with found, count, message, details
        """
        corrupted = self._find_corrupted_comments()

        return {
            "found": len(corrupted) > 0,
            "count": len(corrupted),
            "message": f"Found {len(corrupted)} comment(s) with malformed JSON",
            "details": [
                {
                    "entity_type": item["entity_type"],
                    "entity_id": item["entity_id"],
                    "comment_index": item["index"],
                }
                for item in corrupted
            ],
        }

    def dry_run(self) -> FixResult:
        """Preview what comments would be fixed.

        Returns:
            FixResult with dry_run=True
        """
        corrupted = self._find_corrupted_comments()

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would fix {len(corrupted)} corrupted comment(s)",
            affected_items=[
                f"{item['entity_type']}:{item['entity_id']}" for item in corrupted
            ],
            items_count=len(corrupted),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Fix corrupted comments.

        Args:
            force: If True, apply without confirmation

        Returns:
            FixResult with fix results
        """
        corrupted = self._find_corrupted_comments()
        fixed_count = 0

        for item in corrupted:
            try:
                entity_type = item["entity_type"]
                entity_id = item["entity_id"]

                # Get entity and fix comment
                if entity_type == "issue":
                    entity = self.core.issues.get(entity_id)
                elif entity_type == "milestone":
                    entity = self.core.milestones.get(entity_id)
                elif entity_type == "project":
                    entity = self.core.projects.get(entity_id)
                else:
                    continue

                if entity and hasattr(entity, "comments"):
                    # Attempt to sanitize comments
                    fixed = self._sanitize_comments(entity.comments)
                    if fixed is not None:
                        entity.comments = fixed
                        self.core.issues.update(
                            entity
                        ) if entity_type == "issue" else None
                        fixed_count += 1
            except Exception as e:
                logger.debug(
                    "comment_sanitization_failed",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    error=str(e),
                    action="sanitize_comment",
                )

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=False,
            message=f"Fixed {fixed_count}/{len(corrupted)} corrupted comment(s)",
            affected_items=[
                f"{item['entity_type']}:{item['entity_id']}" for item in corrupted
            ],
            items_count=len(corrupted),
            changes_made=fixed_count,
        )

    def _find_corrupted_comments(self) -> list[dict]:
        """Find comments with malformed JSON.

        Returns:
            List of dicts with entity_type, entity_id, index
        """
        corrupted = []

        try:
            # Check issue comments
            for issue in self.core.issues.list():
                if hasattr(issue, "comments") and issue.comments:
                    for i, comment in enumerate(issue.comments):
                        if self._is_corrupted_json(comment):
                            corrupted.append(
                                {
                                    "entity_type": "issue",
                                    "entity_id": issue.id,
                                    "index": i,
                                }
                            )

            # Check milestone comments
            for milestone in self.core.milestones.list():
                if hasattr(milestone, "comments") and milestone.comments:
                    for i, comment in enumerate(milestone.comments):
                        if self._is_corrupted_json(comment):
                            corrupted.append(
                                {
                                    "entity_type": "milestone",
                                    "entity_id": milestone.id,
                                    "index": i,
                                }
                            )

            # Check project comments
            for project in self.core.projects.list():
                if hasattr(project, "comments") and project.comments:
                    for i, comment in enumerate(project.comments):
                        if self._is_corrupted_json(comment):
                            corrupted.append(
                                {
                                    "entity_type": "project",
                                    "entity_id": project.id,
                                    "index": i,
                                }
                            )
        except Exception as e:
            logger.debug("comments_load_failed", error=str(e), action="load_comments")

        return corrupted

    def _is_corrupted_json(self, comment: dict) -> bool:
        """Check if a comment has malformed JSON content.

        Args:
            comment: Comment dict

        Returns:
            True if JSON is malformed
        """
        if not comment or not isinstance(comment, dict):
            return True

        # Try to access and parse comment content
        try:
            content = comment.get("content", "")
            if content and content.startswith("{"):
                json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return True

        return False

    def _sanitize_comments(self, comments: list) -> list | None:
        """Attempt to sanitize a list of comments.

        Args:
            comments: List of comment dicts

        Returns:
            Sanitized comments list or None if failed
        """
        try:
            sanitized = []
            for comment in comments:
                if self._is_corrupted_json(comment):
                    # Try to salvage what we can
                    if isinstance(comment, dict):
                        sanitized.append(
                            {
                                "author": comment.get("author", "unknown"),
                                "content": "[corrupted comment sanitized]",
                                "created_at": comment.get("created_at", ""),
                            }
                        )
                else:
                    sanitized.append(comment)
            return sanitized
        except Exception as e:
            logger.error("comment_sanitization_failed", error=str(e))
            return None
