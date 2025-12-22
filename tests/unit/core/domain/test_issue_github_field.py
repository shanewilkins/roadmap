"""Tests for Issue model GitHub issue field validation."""

import pytest

from roadmap.core.domain.issue import Issue


class TestGitHubIssueValidation:
    """Tests for github_issue field validation."""

    def test_github_issue_valid_integer(self):
        """Test creating issue with valid GitHub issue number."""
        issue = Issue(title="Test", github_issue=123)
        assert issue.github_issue == 123

    def test_github_issue_valid_none(self):
        """Test creating issue with no GitHub issue link."""
        issue = Issue(title="Test")
        assert issue.github_issue is None

    def test_github_issue_valid_large_number(self):
        """Test creating issue with large GitHub issue number."""
        issue = Issue(title="Test", github_issue=999999)
        assert issue.github_issue == 999999

    def test_github_issue_string_to_int(self):
        """Test that string GitHub issue number is converted to int."""
        issue = Issue(title="Test", github_issue="456")
        assert issue.github_issue == 456
        assert isinstance(issue.github_issue, int)

    def test_github_issue_zero_raises_error(self):
        """Test that zero GitHub issue number raises error."""
        with pytest.raises(ValueError, match="positive integer"):
            Issue(title="Test", github_issue=0)

    def test_github_issue_negative_raises_error(self):
        """Test that negative GitHub issue number raises error."""
        with pytest.raises(ValueError, match="positive integer"):
            Issue(title="Test", github_issue=-123)

    def test_github_issue_invalid_string_raises_error(self):
        """Test that non-numeric string raises error."""
        with pytest.raises(ValueError, match="must be an integer"):
            Issue(title="Test", github_issue="not-a-number")

    def test_github_issue_float_string_raises_error(self):
        """Test that float string raises error."""
        with pytest.raises(ValueError, match="must be an integer"):
            Issue(title="Test", github_issue="123.45")

    def test_github_issue_explicit_none(self):
        """Test explicitly setting github_issue to None."""
        issue = Issue(title="Test", github_issue=None)
        assert issue.github_issue is None

    def test_github_issue_update(self):
        """Test updating github_issue after creation."""
        issue = Issue(title="Test")
        assert issue.github_issue is None

        issue.github_issue = 789
        assert issue.github_issue == 789

    def test_github_issue_with_other_fields(self):
        """Test github_issue works alongside other fields."""
        issue = Issue(
            title="Complete Issue",
            assignee="john",
            milestone="v1.0",
            github_issue=456,
        )
        assert issue.github_issue == 456
        assert issue.assignee == "john"
        assert issue.milestone == "v1.0"

    def test_github_issue_model_dump(self):
        """Test that github_issue is included in model dump."""
        issue = Issue(title="Test", github_issue=789)
        data = issue.model_dump()
        assert data["github_issue"] == 789

    def test_github_issue_model_dump_none(self):
        """Test that None github_issue is in model dump."""
        issue = Issue(title="Test")
        data = issue.model_dump()
        assert "github_issue" in data
        assert data["github_issue"] is None

    def test_github_issue_json_serialization(self):
        """Test that github_issue serializes to JSON correctly."""
        issue = Issue(title="Test", github_issue=321)
        json_str = issue.model_dump_json()
        assert '"github_issue":321' in json_str

    def test_github_issue_json_deserialization(self):
        """Test that github_issue deserializes from JSON correctly."""
        json_str = '{"title": "Test", "github_issue": 654}'
        issue = Issue.model_validate_json(json_str)
        assert issue.github_issue == 654

    def test_github_issue_validation_in_dict(self):
        """Test validation works when creating from dict."""
        data = {"title": "Test", "github_issue": 999}
        issue = Issue(**data)
        assert issue.github_issue == 999

    def test_github_issue_validation_string_in_dict(self):
        """Test string conversion works in dict creation."""
        data = {"title": "Test", "github_issue": "888"}
        issue = Issue(**data)  # type: ignore
        assert issue.github_issue == 888

    def test_github_issue_validation_error_in_dict(self):
        """Test validation error in dict creation."""
        data = {"title": "Test", "github_issue": -50}
        with pytest.raises(ValueError):
            Issue(**data)
