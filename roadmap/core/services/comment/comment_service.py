"""Comment management service for entities (Issues, Projects, Milestones)."""

import uuid
from datetime import UTC, datetime

from roadmap.common.errors.exceptions import ValidationError
from roadmap.common.observability.instrumentation import traced
from roadmap.core.domain import Comment
from roadmap.infrastructure.logging.error_logging import (
    log_validation_error,
)


class CommentService:
    """Service for managing comments on entities."""

    @staticmethod
    def generate_comment_id() -> int:
        """Generate a unique comment ID.

        Returns:
            A unique comment ID
        """
        uid = uuid.uuid4()
        return int(str(uid.int)[:15])

    @staticmethod
    @traced("create_comment")
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
            error = ValidationError(
                domain_message="Comment author cannot be empty",
                user_message="Comment author cannot be empty",
            )
            log_validation_error(
                error,
                entity_type="Comment",
                field_name="author",
                proposed_value=author,
            )
            raise error

        if not body or not body.strip():
            error = ValidationError(
                domain_message="Comment body cannot be empty",
                user_message="Comment body cannot be empty",
            )
            log_validation_error(
                error,
                entity_type="Comment",
                field_name="body",
                proposed_value=body,
            )
            raise error

        now = datetime.now(UTC)

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
    @traced("validate_comment_thread")
    @staticmethod
    def _validate_comment_field(comment: Comment) -> list[str]:
        """Validate individual comment fields.

        Args:
            comment: Comment to validate

        Returns:
            List of field validation errors
        """
        errors = []

        if not isinstance(comment.created_at, datetime):
            errors.append(f"Comment {comment.id}: created_at is not a valid datetime")
        if not isinstance(comment.updated_at, datetime):
            errors.append(f"Comment {comment.id}: updated_at is not a valid datetime")

        if not comment.author or not comment.author.strip():
            errors.append(f"Comment {comment.id}: author cannot be empty")

        if not comment.body or not comment.body.strip():
            errors.append(f"Comment {comment.id}: body cannot be empty")

        return errors

    @staticmethod
    def _validate_duplicate_ids(comments: list[Comment]) -> tuple[list[str], set[str]]:
        """Validate for duplicate comment IDs.

        Args:
            comments: List of comments to check

        Returns:
            Tuple of (error_messages, comment_ids_set)
        """
        errors = []
        comment_ids = set()

        for comment in comments:
            if comment.id in comment_ids:
                errors.append(f"Duplicate comment ID: {comment.id}")
            comment_ids.add(comment.id)

        return errors, comment_ids

    @staticmethod
    def _validate_reply_references(
        comments: list[Comment], comment_ids: set[str]
    ) -> list[str]:
        """Validate in_reply_to references point to existing comments.

        Args:
            comments: List of comments
            comment_ids: Set of known comment IDs

        Returns:
            List of reference validation errors
        """
        errors = []

        for comment in comments:
            if (
                comment.in_reply_to is not None
                and comment.in_reply_to not in comment_ids
            ):
                if comment_ids:
                    errors.append(
                        f"Comment {comment.id}: in_reply_to references non-existent comment {comment.in_reply_to}"
                    )

        return errors

    @staticmethod
    def _validate_circular_references(comments: list[Comment]) -> list[str]:
        """Validate for circular references in reply chain.

        Args:
            comments: List of comments

        Returns:
            List of circular reference errors
        """
        errors = []

        for comment in comments:
            if comment.in_reply_to is None:
                continue

            chain = set()
            current_id = comment.in_reply_to
            max_depth = len(comments) + 1

            while current_id is not None and max_depth > 0:
                if current_id == comment.id:
                    errors.append(f"Comment {comment.id}: circular reference detected")
                    break
                if current_id in chain:
                    break
                chain.add(current_id)
                current_comment = next(
                    (c for c in comments if c.id == current_id), None
                )
                current_id = current_comment.in_reply_to if current_comment else None
                max_depth -= 1

        return errors

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

        # Check for duplicate IDs
        dup_errors, comment_ids = CommentService._validate_duplicate_ids(comments)
        errors.extend(dup_errors)

        # Check field validity
        for comment in comments:
            field_errors = CommentService._validate_comment_field(comment)
            errors.extend(field_errors)

        # Check reply references
        ref_errors = CommentService._validate_reply_references(comments, comment_ids)
        errors.extend(ref_errors)

        # Check for circular references
        circular_errors = CommentService._validate_circular_references(comments)
        errors.extend(circular_errors)

        return errors

    @staticmethod
    @traced("build_comment_threads")
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
    @traced("format_comment_for_display")
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
