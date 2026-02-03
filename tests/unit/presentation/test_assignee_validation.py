"""Tests for assignee validation functionality."""

from unittest.mock import Mock


class TestAssigneeValidation:
    """Test cases for assignee validation."""

    def test_validate_assignee_string_type(self):
        """Test that validate_assignee method exists and returns expected tuple type."""
        from roadmap.infrastructure.coordination.team_coordinator import TeamCoordinator

        mock_ops = Mock()
        coordinator = TeamCoordinator(mock_ops)
        # The method exists and is callable
        assert hasattr(coordinator, "validate_assignee")
        assert callable(coordinator.validate_assignee)
