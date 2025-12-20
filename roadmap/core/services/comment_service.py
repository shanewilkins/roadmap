"""Comment management service for entities (Issues, Projects, Milestones)."""

import uuid
from datetime import datetime

from roadmap.common.errors.exceptions import ValidationError
from roadmap.core.domain import Comment


class CommentService:
    """Service for managing comments on entities."""

    @staticmethod
    def generate_comment_id() -> int:
        """Generate a unique comment ID.

        Returns:
            A unique comment ID
        """
        return int(str(int(uuid.uuid4().int))[:15])

    @staticmethod
    def create_comment(
        author: str,
        body: str,
        entity_id: str | None = None,
        in_reply_to: int | None = None,
    ) -> Comment:
        """Create a new comment.

        Args:
            author: Author name/username
            body: Comment body (markdown)
            entity_id: Optional entity ID the comment is on
            in_reply_to: Optional ID of comment this replies to (for threading)

        Returns:
            New Comment instance

        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate inputs
        if not author or not author.strip():
            raise ValidationError(
                domain_message="Comment author cannot be empty",
                user_message="Comment author cannot be empty",
            )

        if not body or not body.strip():
            raise ValidationError(
                domain_message="Comment body cannot be empty",
                user_message="Comment body cannot be empty",
            )

        now = datetime.now()

        return Comment(
            id=CommentService.generate_comment_id(),
            issue_id=entity_id or "",
            author=author.strip(),
            body=body.strip(),
            created_at=now,
            updated_at=now,
            in_reply_to=in_reply_to,
        )

    @staticmethod
    def validate_comment_thread(comments: list[Comment]) -> list[str]:
        """Validate comment threads for errors.

        Checks for:
        - Duplicate comment IDs
        - Invalid in_reply_to references
        - Circular references
        - Valid datetime fields

        Args:
            comments: List of comments to validate

        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        comment_ids = set()

        for comment in comments:
            # Check for duplicate IDs
            if comment.id in comment_ids:
                errors.append(f"Duplicate comment ID: {comment.id}")
            comment_ids.add(comment.id)

            # Check for invalid datetime fields
            if not isinstance(comment.created_at, datetime):
                errors.append(
                    f"Comment {comment.id}: created_at is not a valid datetime"
                )
            if not isinstance(comment.updated_at, datetime):
                errors.append(
                    f"Comment {comment.id}: updated_at is not a valid datetime"
                )

            # Check for empty author
            if not comment.author or not comment.author.strip():
                errors.append(f"Comment {comment.id}: author cannot be empty")

            # Check for empty body
            if not comment.body or not comment.body.strip():
                errors.append(f"Comment {comment.id}: body cannot be empty")

            # Validate in_reply_to reference
            if (
                comment.in_reply_to is not None
                and comment.in_reply_to not in comment_ids
            ):
                # Only warn if the comment isn't the first one and has an invalid reply-to
                if comment_ids:  # Only if we've seen other comments
                    errors.append(
                        f"Comment {comment.id}: in_reply_to references non-existent comment {comment.in_reply_to}"
                    )

        # Check for circular references
        seen_chains = {}
        for comment in comments:
            if comment.in_reply_to is None:
                continue

            chain = set()
            current_id = comment.id
            max_depth = len(comments) + 1  # Prevent infinite loops

            while current_id in seen_chains and max_depth > 0:
                if current_id in chain:
                    errors.append(f"Comment {comment.id}: circular reference detected")
                    break
                chain.add(current_id)
                current_id = next(
                    (c.in_reply_to for c in comments if c.id == current_id),
                    None,
                )
                max_depth -= 1

        return errors

    @staticmethod
    def build_comment_threads(
        comments: list[Comment],
    ) -> dict[int | None, list[Comment]]:
        """Build comment thread hierarchy from flat list.

        Groups comments by their parent (in_reply_to) for display.

        Args:
            comments: List of comments

        Returns:
            Dictionary mapping parent comment ID -> list of replies
        """
        threads: dict[int | None, list[Comment]] = {}

        for comment in comments:
            parent_id = comment.in_reply_to
            if parent_id not in threads:
                threads[parent_id] = []
            threads[parent_id].append(comment)

        # Sort by created_at within each thread
        for thread in threads.values():
            thread.sort(key=lambda c: c.created_at)

        return threads

    @staticmethod
    def format_comment_for_display(comment: Comment, indent: int = 0) -> str:
        """Format a comment for CLI display.

        Args:
            comment: Comment to format
            indent: Indentation level (for threaded replies)

        Returns:
            Formatted comment string
        """
        indent_str = "  " * indent
        timestamp = comment.created_at.strftime("%Y-%m-%d %H:%M")
        return f"{indent_str}💬 {comment.author} ({timestamp}):\n{indent_str}   {comment.body}"
