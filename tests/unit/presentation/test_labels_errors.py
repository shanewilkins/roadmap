"""Error path tests for labels module.

Tests focus on:
- API request failures and error handling
- Label creation/update/deletion with various errors
- Repository validation failures
- Label parsing edge cases
- Exception handling in setup operations
"""

from unittest.mock import Mock, patch

import pytest
import requests

from roadmap.adapters.github.handlers.base import GitHubAPIError
from roadmap.adapters.github.handlers.labels import LabelHandler
from roadmap.core.domain import Priority, Status

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session():
    """Fixture providing a mock requests session."""
    return Mock(spec=requests.Session)


@pytest.fixture
def label_handler(mock_session):
    """Fixture providing a LabelHandler with mocked session."""
    return LabelHandler(session=mock_session, owner="test_owner", repo="test_repo")


class TestLabelHandlerRepositoryValidation:
    """Test repository validation in LabelHandler."""

    import pytest

    @pytest.mark.parametrize(
        "method, args, kwargs",
        [
            ("create_label", ("test-label", "FF0000"), {}),
            ("get_labels", (), {}),
        ],
    )
    def test_label_handler_repository_validation_param(self, method, args, kwargs):
        session = Mock(spec=requests.Session)
        handler = LabelHandler(session=session, owner=None, repo=None)
        with pytest.raises(GitHubAPIError):
            getattr(handler, method)(*args, **kwargs)


class TestLabelHandlerAPIErrors:
    """Test API error handling in LabelHandler."""

    @pytest.mark.parametrize(
        "method, args, kwargs, response_json, expected_name",
        [
            (
                "create_label",
                ("test-label", "#FF0000"),
                {},
                {"name": "test", "color": "FF0000"},
                "test",
            ),
            (
                "update_label",
                ("old-label",),
                {"color": "#FF0000"},
                {"name": "updated", "color": "FF0000"},
                "updated",
            ),
            (
                "update_label",
                ("old-label",),
                {
                    "new_name": "new-label",
                    "color": "FF0000",
                    "description": "Updated description",
                },
                {
                    "name": "new-label",
                    "color": "FF0000",
                    "description": "Updated description",
                },
                "new-label",
            ),
            (
                "update_label",
                ("label",),
                {"new_name": None, "color": None, "description": None},
                {"name": "unchanged"},
                "unchanged",
            ),
        ],
    )
    def test_label_handler_api_errors_param(
        self, label_handler, method, args, kwargs, response_json, expected_name
    ):
        with patch.object(label_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = response_json
            mock_request.return_value = mock_response
            result = getattr(label_handler, method)(*args, **kwargs)
            assert result["name"] == expected_name


class TestLabelConversion:
    """Test label conversion functions."""

    def test_priority_to_labels_all_priorities(self, label_handler):
        """Test priority_to_labels for all priority levels."""
        assert label_handler.priority_to_labels(Priority.CRITICAL) == [
            "priority:critical"
        ]
        assert label_handler.priority_to_labels(Priority.HIGH) == ["priority:high"]
        assert label_handler.priority_to_labels(Priority.MEDIUM) == ["priority:medium"]
        assert label_handler.priority_to_labels(Priority.LOW) == ["priority:low"]

    def test_priority_to_labels_invalid(self, label_handler):
        """Test priority_to_labels with invalid priority."""
        result = label_handler.priority_to_labels(None)
        assert result == []

    def test_status_to_labels_all_statuses(self, label_handler):
        """Test status_to_labels for all status values."""
        assert label_handler.status_to_labels(Status.TODO) == ["status:todo"]
        assert label_handler.status_to_labels(Status.IN_PROGRESS) == [
            "status:in-progress"
        ]
        assert label_handler.status_to_labels(Status.BLOCKED) == ["status:blocked"]
        assert label_handler.status_to_labels(Status.REVIEW) == ["status:review"]
        assert label_handler.status_to_labels(Status.CLOSED) == ["status:done"]

    def test_status_to_labels_invalid(self, label_handler):
        """Test status_to_labels with invalid status."""
        result = label_handler.status_to_labels(None)
        assert result == []


class TestLabelsParsing:
    """Test label parsing from issue labels."""

    def test_labels_to_priority_from_string_labels(self, label_handler):
        """Test labels_to_priority with string labels."""
        labels = ["priority:high", "other-label"]
        result = label_handler.labels_to_priority(labels)
        assert result == Priority.HIGH

    def test_labels_to_priority_from_dict_labels(self, label_handler):
        """Test labels_to_priority with dict labels (with 'name' key)."""
        labels = [{"name": "priority:critical"}, {"name": "other"}]
        result = label_handler.labels_to_priority(labels)
        assert result == Priority.CRITICAL

    def test_labels_to_priority_mixed_types(self, label_handler):
        """Test labels_to_priority with mixed string and dict labels."""
        labels = ["other-label", {"name": "priority:medium"}]
        result = label_handler.labels_to_priority(labels)
        assert result == Priority.MEDIUM

    def test_labels_to_priority_no_match(self, label_handler):
        """Test labels_to_priority returns None when no priority found."""
        labels = ["label1", "label2"]
        result = label_handler.labels_to_priority(labels)
        assert result is None

    def test_labels_to_priority_empty_list(self, label_handler):
        """Test labels_to_priority with empty labels list."""
        result = label_handler.labels_to_priority([])
        assert result is None

    def test_labels_to_priority_first_match(self, label_handler):
        """Test labels_to_priority returns first matching priority."""
        labels = ["priority:low", "priority:high"]
        result = label_handler.labels_to_priority(labels)
        assert result == Priority.LOW

    def test_labels_to_status_from_string_labels(self, label_handler):
        """Test labels_to_status with string labels."""
        labels = ["status:todo", "other-label"]
        result = label_handler.labels_to_status(labels)
        assert result == Status.TODO

    def test_labels_to_status_from_dict_labels(self, label_handler):
        """Test labels_to_status with dict labels."""
        labels = [{"name": "status:in-progress"}, {"name": "other"}]
        result = label_handler.labels_to_status(labels)
        assert result == Status.IN_PROGRESS

    def test_labels_to_status_mixed_types(self, label_handler):
        """Test labels_to_status with mixed label types."""
        labels = ["other-label", {"name": "status:blocked"}]
        result = label_handler.labels_to_status(labels)
        assert result == Status.BLOCKED

    def test_labels_to_status_no_match(self, label_handler):
        """Test labels_to_status returns None when no status found."""
        labels = ["priority:high", "other"]
        result = label_handler.labels_to_status(labels)
        assert result is None

    def test_labels_to_status_closed_mapping(self, label_handler):
        """Test labels_to_status maps 'status:done' to Status.CLOSED."""
        labels = ["status:done"]
        result = label_handler.labels_to_status(labels)
        assert result == Status.CLOSED

    def test_labels_to_status_empty_list(self, label_handler):
        """Test labels_to_status with empty labels list."""
        result = label_handler.labels_to_status([])
        assert result is None

    def test_labels_to_status_first_match(self, label_handler):
        """Test labels_to_status returns first matching status."""
        labels = ["status:review", "status:todo"]
        result = label_handler.labels_to_status(labels)
        assert result == Status.REVIEW

    def test_labels_to_priority_dict_without_name(self, label_handler):
        """Test labels_to_priority with dict label missing 'name' key."""
        labels = [{"color": "FF0000"}]
        result = label_handler.labels_to_priority(labels)
        assert result is None

    def test_labels_to_status_dict_without_name(self, label_handler):
        """Test labels_to_status with dict label missing 'name' key."""
        labels = [{"color": "FF0000"}]
        result = label_handler.labels_to_status(labels)
        assert result is None


class TestDefaultLabelsSetup:
    """Test setup_default_labels operation."""

    def test_setup_creates_new_labels(self, label_handler):
        """Test setup_default_labels creates missing labels."""
        with patch.object(label_handler, "get_labels") as mock_get:
            with patch.object(label_handler, "create_label") as mock_create:
                mock_get.return_value = []

                label_handler.setup_default_labels()

                # Should attempt to create all 9 default labels (4 priority + 5 status)
                assert mock_create.call_count == 9

    def test_setup_skips_existing_labels(self, label_handler):
        """Test setup_default_labels skips existing labels."""
        with patch.object(label_handler, "get_labels") as mock_get:
            with patch.object(label_handler, "create_label") as mock_create:
                # Return existing priority labels
                mock_get.return_value = [
                    {"name": "priority:critical"},
                    {"name": "priority:high"},
                    {"name": "priority:medium"},
                    {"name": "priority:low"},
                ]

                label_handler.setup_default_labels()

                # Should create only 5 status labels
                assert mock_create.call_count == 5

    def test_setup_handles_create_exception(self, label_handler):
        """Test setup_default_labels handles creation exceptions."""
        with patch.object(label_handler, "get_labels") as mock_get:
            with patch.object(label_handler, "create_label") as mock_create:
                mock_get.return_value = []
                # Simulate race condition where label already exists
                mock_create.side_effect = Exception("Label already exists")

                # Should not raise, silently continue
                label_handler.setup_default_labels()

                assert mock_create.call_count == 9

    def test_setup_all_labels_existing(self, label_handler):
        """Test setup_default_labels when all labels already exist."""
        with patch.object(label_handler, "get_labels") as mock_get:
            with patch.object(label_handler, "create_label") as mock_create:
                all_labels = [
                    {"name": "priority:critical"},
                    {"name": "priority:high"},
                    {"name": "priority:medium"},
                    {"name": "priority:low"},
                    {"name": "status:todo"},
                    {"name": "status:in-progress"},
                    {"name": "status:blocked"},
                    {"name": "status:review"},
                    {"name": "status:done"},
                ]
                mock_get.return_value = all_labels

                label_handler.setup_default_labels()

                # Should not create any labels
                mock_create.assert_not_called()

    def test_setup_partial_existing(self, label_handler):
        """Test setup_default_labels with some labels existing."""
        with patch.object(label_handler, "get_labels") as mock_get:
            with patch.object(label_handler, "create_label") as mock_create:
                # Only priority labels exist
                mock_get.return_value = [
                    {"name": "priority:critical"},
                    {"name": "priority:high"},
                    {"name": "priority:medium"},
                    {"name": "priority:low"},
                ]

                label_handler.setup_default_labels()

                # Should create exactly 5 status labels
                assert mock_create.call_count == 5


class TestLabelHandlerEdgeCases:
    """Test edge cases in label handling."""

    def test_get_labels_empty_response(self, label_handler):
        """Test get_labels with empty response."""
        with patch.object(label_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_request.return_value = mock_response

            result = label_handler.get_labels()
            assert result == []

    def test_label_description_special_characters(self, label_handler):
        """Test label description with special characters."""
        with patch.object(label_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"name": "test"}
            mock_request.return_value = mock_response

            description = "Test with special chars: @#$%^&*()"
            result = label_handler.create_label("test", "FF0000", description)
            assert result["name"] == "test"

    def test_color_with_multiple_hashes(self, label_handler):
        """Test color parsing with multiple hash symbols."""
        with patch.object(label_handler, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = {"name": "test", "color": "FF0000"}
            mock_request.return_value = mock_response

            # lstrip removes all leading #
            result = label_handler.create_label("test", "##FF0000")
            assert result["name"] == "test"

    def test_delete_label_calls_correct_endpoint(self, label_handler):
        """Test delete_label calls the correct API endpoint."""
        with patch.object(label_handler, "_make_request") as mock_request:
            label_handler.delete_label("test-label")

            # Verify DELETE was called with correct endpoint
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "DELETE"
            assert "test-label" in call_args[0][1]
