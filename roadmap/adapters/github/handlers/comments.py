"""GitHub Comments handler."""

from roadmap.adapters.github.handlers.base import BaseGitHubHandler
from roadmap.common.datetime_parser import parse_github_datetime
from roadmap.core.domain import Comment


class CommentsHandler(BaseGitHubHandler):
    """Handler for GitHub Comments API operations."""

    def _create_comment_from_response(
        self, comment_data: dict, issue_id: str = ""
    ) -> Comment:
        """Create a Comment object from GitHub API response data.

        Args:
            comment_data: GitHub API comment response
            issue_id: Issue ID (may be empty for standalone comment endpoints)

        Returns:
            Comment object
        """
        return Comment(
            id=comment_data["id"],
            issue_id=issue_id,
            author=comment_data["user"]["login"],
            body=comment_data["body"],
            created_at=parse_github_datetime(comment_data["created_at"]),
            updated_at=parse_github_datetime(comment_data["updated_at"]),
            github_url=comment_data["html_url"],
        )

    def get_issue_comments(self, issue_number: int) -> list[Comment]:
        """Get all comments for a specific issue.

        Handles pagination automatically - returns all comments.

        Args:
            issue_number: GitHub issue number

        Returns:
            List of all Comment objects for the issue
        """
        self._check_repository()

        comments_data = self._paginate_request(
            "GET", f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments"
        )

        comments = []
        for comment_data in comments_data:
            comment = self._create_comment_from_response(
                comment_data, issue_id=str(issue_number)
            )
            comments.append(comment)

        return comments

    def create_issue_comment(self, issue_number: int, body: str) -> Comment:
        """Create a new comment on an issue.

        Args:
            issue_number: GitHub issue number
            body: Comment content (markdown)

        Returns:
            Created Comment object
        """
        self._check_repository()

        data = {"body": body}

        response = self._make_request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
            json=data,
        )

        comment_data = response.json()
        return self._create_comment_from_response(
            comment_data, issue_id=str(issue_number)
        )

    def update_issue_comment(self, comment_id: int, body: str) -> Comment:
        """Update an existing comment.

        Args:
            comment_id: GitHub comment ID
            body: Updated comment content (markdown)

        Returns:
            Updated Comment object
        """
        self._check_repository()

        data = {"body": body}

        response = self._make_request(
            "PATCH",
            f"/repos/{self.owner}/{self.repo}/issues/comments/{comment_id}",
            json=data,
        )

        comment_data = response.json()
        # We don't get issue number from this endpoint
        return self._create_comment_from_response(comment_data, issue_id="")

    def delete_issue_comment(self, comment_id: int) -> None:
        """Delete a comment.

        Args:
            comment_id: GitHub comment ID
        """
        self._check_repository()

        self._make_request(
            "DELETE", f"/repos/{self.owner}/{self.repo}/issues/comments/{comment_id}"
        )
