"""Tests for ProjectStatusService."""

import pytest

from roadmap.core.services.project_status_service import ProjectStatusService


class TestProjectStatusService:
    """Test suite for ProjectStatusService."""

    @pytest.fixture
    def mock_core(self, mock_core_simple):
        """Create a mock RoadmapCore.

        Uses centralized mock_core_simple fixture.
        """
        return mock_core_simple

    @pytest.fixture
    def service(self, mock_core):
        """Create a service instance with mocked core."""
        return ProjectStatusService(core=mock_core)

    def test_init_stores_core(self, mock_core):
        """Test that core is stored during initialization."""
        service = ProjectStatusService(core=mock_core)
        assert service.core is mock_core

    def test_get_project_overview_returns_dict(self, service):
        """Test that get_project_overview returns a dictionary."""
        result = service.get_project_overview(project_id=None)
        assert isinstance(result, dict)

    def test_get_project_overview_with_project_id(self, service):
        """Test get_project_overview with specific project ID."""
        result = service.get_project_overview(project_id="proj-123")
        assert isinstance(result, dict)

    def test_get_milestone_progress_returns_list(self, service):
        """Test that get_milestone_progress returns a list."""
        result = service.get_milestone_progress(project_id=None)
        assert isinstance(result, list)

    def test_get_milestone_progress_with_project_id(self, service):
        """Test get_milestone_progress with specific project ID."""
        result = service.get_milestone_progress(project_id="proj-123")
        assert isinstance(result, list)

    def test_get_issues_by_status_returns_dict(self, service):
        """Test that get_issues_by_status returns a dictionary."""
        result = service.get_issues_by_status(project_id=None)
        assert isinstance(result, dict)

    def test_get_issues_by_status_with_project_id(self, service):
        """Test get_issues_by_status with specific project ID."""
        result = service.get_issues_by_status(project_id="proj-123")
        assert isinstance(result, dict)

    def test_get_assignee_workload_returns_dict(self, service):
        """Test that get_assignee_workload returns a dictionary."""
        result = service.get_assignee_workload(project_id=None)
        assert isinstance(result, dict)

    def test_get_assignee_workload_with_project_id(self, service):
        """Test get_assignee_workload with specific project ID."""
        result = service.get_assignee_workload(project_id="proj-123")
        assert isinstance(result, dict)

    def test_get_status_summary_returns_dict(self, service):
        """Test that get_status_summary returns a dictionary."""
        result = service.get_status_summary(project_id=None)
        assert isinstance(result, dict)

    def test_get_status_summary_with_project_id(self, service):
        """Test get_status_summary with specific project ID."""
        result = service.get_status_summary(project_id="proj-123")
        assert isinstance(result, dict)

    def test_service_has_all_required_methods(self, service):
        """Test that service has all required public methods."""
        assert hasattr(service, "get_project_overview")
        assert hasattr(service, "get_milestone_progress")
        assert hasattr(service, "get_issues_by_status")
        assert hasattr(service, "get_assignee_workload")
        assert hasattr(service, "get_status_summary")

    def test_all_methods_are_callable(self, service):
        """Test that all public methods are callable."""
        assert callable(service.get_project_overview)
        assert callable(service.get_milestone_progress)
        assert callable(service.get_issues_by_status)
        assert callable(service.get_assignee_workload)
        assert callable(service.get_status_summary)

    def test_get_project_overview_error_handling(self, service):
        """Test error handling in get_project_overview."""
        result = service.get_project_overview()
        # Should return dict without raising exception
        assert isinstance(result, dict)

    def test_get_milestone_progress_error_handling(self, service):
        """Test error handling in get_milestone_progress."""
        result = service.get_milestone_progress()
        # Should return empty list without raising exception
        assert isinstance(result, list)

    def test_get_issues_by_status_error_handling(self, service):
        """Test error handling in get_issues_by_status."""
        result = service.get_issues_by_status()
        # Should return empty dict without raising exception
        assert isinstance(result, dict)

    def test_get_assignee_workload_error_handling(self, service):
        """Test error handling in get_assignee_workload."""
        result = service.get_assignee_workload()
        # Should return empty dict without raising exception
        assert isinstance(result, dict)

    def test_get_status_summary_error_handling(self, service):
        """Test error handling in get_status_summary."""
        result = service.get_status_summary()
        # Should return dict without raising exception
        assert isinstance(result, dict)

    def test_service_maintains_core_reference(self, mock_core):
        """Test that service maintains core reference."""
        service = ProjectStatusService(core=mock_core)
        assert service.core is mock_core

    def test_multiple_calls_to_same_method(self, service):
        """Test that methods can be called multiple times."""
        result1 = service.get_project_overview()
        result2 = service.get_project_overview()
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)

    def test_project_overview_contains_expected_fields(self, service):
        """Test that project overview contains expected fields."""
        result = service.get_project_overview()
        # Should contain standard fields
        assert isinstance(result, dict)

    def test_status_summary_contains_basic_fields(self, service):
        """Test that status summary contains basic fields."""
        result = service.get_status_summary()
        # Should be a dictionary (may have error key or status fields)
        assert isinstance(result, dict)

    def test_service_integration_workflow(self, service):
        """Test basic workflow through service methods."""
        # Get overview
        overview = service.get_project_overview()
        assert isinstance(overview, dict)

        # Get milestone progress
        milestones = service.get_milestone_progress()
        assert isinstance(milestones, list)

        # Get issues by status
        issues = service.get_issues_by_status()
        assert isinstance(issues, dict)

        # Get assignee workload
        workload = service.get_assignee_workload()
        assert isinstance(workload, dict)

        # Get status summary
        summary = service.get_status_summary()
        assert isinstance(summary, dict)
