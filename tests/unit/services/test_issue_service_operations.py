"""Phase 8 Batch 4: Comprehensive tests for IssueService.

Tests focus on:
- Issue creation with validation and defaults
- Issue listing with filtering (milestone, status, assignee)
- Getting specific issues
- Updating issue fields
- Deleting issues
- Business logic validation
- Cache invalidation

Uses real service with real repository (tmp_path).
Minimal mocking - testing actual service behavior.
"""


from roadmap.common.constants import IssueType, Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models import IssueCreateServiceParams, IssueUpdateServiceParams
from roadmap.core.services.issue.issue_service import IssueService


class TestIssueServiceCreate:
    """Test creating issues through the service."""

    def test_create_minimal_issue(self, p8_yaml_issue_repository):
        """Service should create issue with minimal parameters."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="New Issue",
            priority="medium",
            issue_type="other",
        )

        issue = service.create_issue(params)

        assert issue.title == "New Issue"
        assert issue.priority == Priority.MEDIUM
        assert issue.issue_type == IssueType.OTHER
        assert issue.id  # Should have auto-generated ID

    def test_create_with_all_parameters(self, p8_yaml_issue_repository):
        """Service should create issue with all parameters."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="Full Feature",
            priority="high",
            issue_type="feature",
            milestone="v1.0",
            labels=["backend", "api"],
            assignee="alice@example.com",
            estimate=16.0,
            depends_on=["issue-1"],
            blocks=["issue-2"],
            content="Detailed description",
        )

        issue = service.create_issue(params)

        assert issue.title == "Full Feature"
        assert issue.priority == Priority.HIGH
        assert issue.issue_type == IssueType.FEATURE
        assert issue.milestone == "v1.0"
        assert issue.labels == ["backend", "api"]
        assert issue.assignee == "alice@example.com"
        assert issue.estimated_hours == 16.0
        assert issue.depends_on == ["issue-1"]
        assert issue.blocks == ["issue-2"]

    def test_created_issue_persisted_to_repository(self, p8_yaml_issue_repository):
        """Created issue should be saved to repository."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="Persistent Issue", priority="medium", issue_type="other"
        )
        created = service.create_issue(params)

        # Verify it's in the repository
        retrieved = p8_yaml_issue_repository.get(created.id)
        assert retrieved is not None
        assert retrieved.title == "Persistent Issue"

    def test_create_with_default_priority(self, p8_yaml_issue_repository):
        """Service should default priority to MEDIUM."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="Test",
            priority="",  # Empty string
            issue_type="other",
        )

        issue = service.create_issue(params)

        assert issue.priority == Priority.MEDIUM

    def test_create_with_default_type(self, p8_yaml_issue_repository):
        """Service should default issue type to OTHER."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="Test",
            priority="medium",
            issue_type="",  # Empty string
        )

        issue = service.create_issue(params)

        assert issue.issue_type == IssueType.OTHER

    def test_create_with_string_priority(self, p8_yaml_issue_repository):
        """Service should convert string priorities to enum."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="Test",
            priority="high",
            issue_type="other",
        )

        issue = service.create_issue(params)

        assert issue.priority == Priority.HIGH
        assert isinstance(issue.priority, Priority)

    def test_create_with_default_content(self, p8_yaml_issue_repository):
        """Service should generate default content if not provided."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="My Issue",
            priority="medium",
            issue_type="other",
        )

        issue = service.create_issue(params)

        assert issue.content is not None
        assert "My Issue" in issue.content
        assert "Description" in issue.content


class TestIssueServiceGet:
    """Test retrieving issues through the service."""

    def test_get_existing_issue(self, p8_populated_issue_repository):
        """Service should retrieve existing issue."""
        service = IssueService(p8_populated_issue_repository)

        issue = service.get_issue("issue-1")

        assert issue is not None
        assert issue.id == "issue-1"
        assert issue.title == "Build feature A"

    def test_get_nonexistent_issue_returns_none(self, p8_yaml_issue_repository):
        """Service should return None for non-existent issue."""
        service = IssueService(p8_yaml_issue_repository)

        issue = service.get_issue("nonexistent")

        assert issue is None


class TestIssueServiceList:
    """Test listing issues through the service."""

    def test_list_all_issues(self, p8_populated_issue_repository):
        """Service should list all active issues."""
        service = IssueService(p8_populated_issue_repository)

        issues = service.list_issues()

        assert len(issues) == 4
        assert all(isinstance(i, Issue) for i in issues)

    def test_list_filter_by_milestone(self, p8_populated_issue_repository):
        """Service should filter issues by milestone."""
        service = IssueService(p8_populated_issue_repository)

        issues = service.list_issues(milestone="v1.0")

        assert len(issues) == 2
        assert all(i.milestone == "v1.0" for i in issues)

    def test_list_filter_by_status(self, p8_populated_issue_repository):
        """Service should filter issues by status."""
        service = IssueService(p8_populated_issue_repository)

        issues = service.list_issues(status=Status.TODO)

        assert len(issues) == 3
        assert all(i.status == Status.TODO for i in issues)

    def test_list_filter_by_assignee(self, p8_populated_issue_repository):
        """Service should filter issues by assignee."""
        service = IssueService(p8_populated_issue_repository)

        # First create an assigned issue
        from roadmap.core.models import IssueCreateServiceParams

        params = IssueCreateServiceParams(
            title="Assigned Task",
            priority="medium",
            issue_type="other",
            assignee="bob@example.com",
        )
        service.create_issue(params)

        issues = service.list_issues(assignee="bob@example.com")

        assert len(issues) == 1
        assert issues[0].assignee == "bob@example.com"

    def test_list_with_multiple_filters(self, p8_populated_issue_repository):
        """Service should apply multiple filters together."""
        service = IssueService(p8_populated_issue_repository)

        issues = service.list_issues(milestone="v1.0", status=Status.TODO)

        assert len(issues) == 1
        assert issues[0].id == "issue-1"

    def test_list_empty_result(self, p8_populated_issue_repository):
        """Service should return empty list when no matches."""
        service = IssueService(p8_populated_issue_repository)

        issues = service.list_issues(milestone="v99.0")

        assert issues == []


class TestIssueServiceUpdate:
    """Test updating issues through the service."""

    def test_update_issue_title(self, p8_yaml_issue_repository):
        """Service should update issue title."""
        service = IssueService(p8_yaml_issue_repository)

        # Create
        create_params = IssueCreateServiceParams(
            title="Original",
            priority="medium",
            issue_type="other",
        )
        created = service.create_issue(create_params)

        # Update
        update_params = IssueUpdateServiceParams(
            issue_id=created.id,
            title="Updated Title",
        )
        updated = service.update_issue(update_params)

        assert updated is not None
        assert updated.title == "Updated Title"

    def test_update_issue_status(self, p8_yaml_issue_repository):
        """Service should update issue status."""
        service = IssueService(p8_yaml_issue_repository)

        create_params = IssueCreateServiceParams(
            title="Test",
            priority="medium",
            issue_type="other",
            milestone="v1.0",
        )
        created = service.create_issue(create_params)

        update_params = IssueUpdateServiceParams(
            issue_id=created.id,
            status=Status.IN_PROGRESS,
        )
        updated = service.update_issue(update_params)

        assert updated is not None
        assert updated.status == Status.IN_PROGRESS

    def test_update_multiple_fields(self, p8_yaml_issue_repository):
        """Service should update multiple fields at once."""
        service = IssueService(p8_yaml_issue_repository)

        create_params = IssueCreateServiceParams(
            title="Original",
            priority="low",
            issue_type="other",
        )
        created = service.create_issue(create_params)

        update_params = IssueUpdateServiceParams(
            issue_id=created.id,
            title="Updated",
            priority=Priority.HIGH,
            assignee="alice@example.com",
            milestone="v2.0",
        )
        updated = service.update_issue(update_params)

        assert updated is not None
        assert updated.title == "Updated"
        assert updated.priority == Priority.HIGH
        assert updated.assignee == "alice@example.com"
        assert updated.milestone == "v2.0"

    def test_update_persists_to_repository(self, p8_yaml_issue_repository):
        """Updated issue should be persisted to repository."""
        service = IssueService(p8_yaml_issue_repository)

        create_params = IssueCreateServiceParams(
            title="Original",
            priority="medium",
            issue_type="other",
        )
        created = service.create_issue(create_params)

        update_params = IssueUpdateServiceParams(
            issue_id=created.id,
            title="Persisted Update",
        )
        service.update_issue(update_params)

        # Verify in repository
        retrieved = p8_yaml_issue_repository.get(created.id)
        assert retrieved.title == "Persisted Update"


class TestIssueServiceDelete:
    """Test deleting issues through the service."""

    def test_delete_issue(self, p8_yaml_issue_repository):
        """Service should delete issue."""
        service = IssueService(p8_yaml_issue_repository)

        create_params = IssueCreateServiceParams(
            title="To Delete",
            priority="medium",
            issue_type="other",
        )
        created = service.create_issue(create_params)

        # Delete
        service.delete_issue(created.id)

        # Verify deleted
        retrieved = service.get_issue(created.id)
        assert retrieved is None

    def test_delete_removes_from_repository(self, p8_yaml_issue_repository):
        """Deleted issue should be removed from repository."""
        service = IssueService(p8_yaml_issue_repository)

        create_params = IssueCreateServiceParams(
            title="Test",
            priority="medium",
            issue_type="other",
        )
        created = service.create_issue(create_params)

        service.delete_issue(created.id)

        # Verify in repository
        retrieved = p8_yaml_issue_repository.get(created.id)
        assert retrieved is None


class TestIssueServiceRelationships:
    """Test issue relationships through the service."""

    def test_create_with_dependencies(self, p8_yaml_issue_repository):
        """Service should create issue with dependencies."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="Feature B",
            priority="medium",
            issue_type="other",
            depends_on=["issue-1", "issue-2"],
            blocks=["issue-3"],
        )
        issue = service.create_issue(params)

        assert issue.depends_on == ["issue-1", "issue-2"]
        assert issue.blocks == ["issue-3"]

    def test_update_preserves_dependencies(self, p8_yaml_issue_repository):
        """Service should preserve dependencies when updating other fields."""
        service = IssueService(p8_yaml_issue_repository)

        # Create with dependencies
        create_params = IssueCreateServiceParams(
            title="Test",
            priority="medium",
            issue_type="other",
            depends_on=["other-issue"],
        )
        created = service.create_issue(create_params)

        # Update other field
        update_params = IssueUpdateServiceParams(
            issue_id=created.id,
            assignee="alice@example.com",
        )
        updated = service.update_issue(update_params)

        # Dependencies should be preserved
        assert updated is not None
        assert updated.depends_on == ["other-issue"]
        assert updated.assignee == "alice@example.com"


class TestIssueServiceValidation:
    """Test service validation and error handling."""

    def test_create_with_invalid_priority_string(self, p8_yaml_issue_repository):
        """Service should handle invalid priority string gracefully."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="Test",
            priority="invalid_priority",
            issue_type="other",
        )
        issue = service.create_issue(params)

        # Should default to MEDIUM for invalid values
        assert issue.priority == Priority.MEDIUM

    def test_create_with_invalid_type_string(self, p8_yaml_issue_repository):
        """Service should handle invalid issue type string gracefully."""
        service = IssueService(p8_yaml_issue_repository)

        params = IssueCreateServiceParams(
            title="Test",
            priority="medium",
            issue_type="invalid_type",
        )
        issue = service.create_issue(params)

        # Should default to OTHER for invalid values
        assert issue.issue_type == IssueType.OTHER


class TestIssueServiceWorkflows:
    """Test realistic issue service workflows."""

    def test_workflow_create_update_retrieve(self, p8_yaml_issue_repository):
        """Test realistic workflow: create, update, retrieve."""
        service = IssueService(p8_yaml_issue_repository)

        # Create
        create_params = IssueCreateServiceParams(
            title="Feature Request",
            priority="high",
            issue_type="feature",
            milestone="v1.0",
        )
        created = service.create_issue(create_params)

        # Update
        update_params = IssueUpdateServiceParams(
            issue_id=created.id,
            status=Status.IN_PROGRESS,
            assignee="alice@example.com",
        )
        updated = service.update_issue(update_params)

        # Retrieve
        retrieved = service.get_issue(created.id)

        assert retrieved is not None
        assert retrieved.status == Status.IN_PROGRESS
        assert retrieved.assignee == "alice@example.com"
        assert retrieved.milestone == "v1.0"

    def test_workflow_create_list_filter(self, p8_yaml_issue_repository):
        """Test workflow: create multiple, list and filter."""
        service = IssueService(p8_yaml_issue_repository)

        # Create several issues
        for i in range(3):
            params = IssueCreateServiceParams(
                title=f"Issue {i}",
                priority="medium",
                issue_type="other",
                milestone="v1.0" if i < 2 else "v2.0",
            )
            service.create_issue(params)

        # List all
        all_issues = service.list_issues()
        assert len(all_issues) == 3

        # Filter by milestone
        v1_issues = service.list_issues(milestone="v1.0")
        assert len(v1_issues) == 2

    def test_workflow_complete_issue_lifecycle(self, p8_yaml_issue_repository):
        """Test complete issue lifecycle."""
        service = IssueService(p8_yaml_issue_repository)

        # 1. Create
        create_params = IssueCreateServiceParams(
            title="Task",
            priority="medium",
            issue_type="other",
        )
        issue = service.create_issue(create_params)
        assert issue.status == Status.TODO

        # 2. Assign and update
        update_params = IssueUpdateServiceParams(
            issue_id=issue.id,
            assignee="dev@example.com",
        )
        service.update_issue(update_params)

        # 3. Start work
        update_params = IssueUpdateServiceParams(
            issue_id=issue.id,
            status=Status.IN_PROGRESS,
        )
        service.update_issue(update_params)

        # 4. Verify progress
        progress = service.get_issue(issue.id)
        assert progress is not None
        assert progress.status == Status.IN_PROGRESS
        assert progress.assignee == "dev@example.com"

        # 5. Complete
        update_params = IssueUpdateServiceParams(
            issue_id=issue.id,
            status=Status.CLOSED,
        )
        service.update_issue(update_params)

        # 6. Delete
        service.delete_issue(issue.id)
        deleted = service.get_issue(issue.id)
        assert deleted is None


class TestIssueServiceCaching:
    """Test service caching behavior."""

    def test_list_returns_consistent_results(self, p8_yaml_issue_repository):
        """Repeated list calls should return consistent results."""
        service = IssueService(p8_yaml_issue_repository)

        # Create some issues
        for i in range(3):
            params = IssueCreateServiceParams(
                title=f"Issue {i}",
                priority="medium",
                issue_type="other",
            )
            service.create_issue(params)

        # List multiple times
        list1 = service.list_issues()
        list2 = service.list_issues()

        assert len(list1) == len(list2) == 3
        assert [i.id for i in list1] == [i.id for i in list2]

    def test_create_invalidates_cache(self, p8_yaml_issue_repository):
        """Creating new issue should invalidate list cache."""
        service = IssueService(p8_yaml_issue_repository)

        # Get initial count
        initial = service.list_issues()
        initial_count = len(initial)

        # Create new issue
        params = IssueCreateServiceParams(
            title="New",
            priority="medium",
            issue_type="other",
        )
        service.create_issue(params)

        # List should reflect the new count
        updated = service.list_issues()
        assert len(updated) == initial_count + 1


class TestIssueServiceIntegration:
    """Integration tests with repository."""

    def test_service_repository_integration(self, p8_yaml_issue_repository):
        """Service should properly integrate with repository."""
        service = IssueService(p8_yaml_issue_repository)

        # Create via service
        create_params = IssueCreateServiceParams(
            title="Integration Test",
            priority="medium",
            issue_type="other",
            milestone="v1.0",
        )
        created = service.create_issue(create_params)

        # Verify via repository
        repo_issue = p8_yaml_issue_repository.get(created.id)
        assert repo_issue.title == created.title
        assert repo_issue.milestone == created.milestone

        # Update via service
        update_params = IssueUpdateServiceParams(
            issue_id=created.id,
            status=Status.IN_PROGRESS,
        )
        updated = service.update_issue(update_params)

        assert updated is not None

        # Verify via repository
        repo_updated = p8_yaml_issue_repository.get(created.id)
        assert repo_updated.status == Status.IN_PROGRESS
        assert repo_updated.status == updated.status

    def test_service_with_populated_repository(self, p8_populated_issue_repository):
        """Service should work with pre-populated repository."""
        service = IssueService(p8_populated_issue_repository)

        # List existing
        issues = service.list_issues()
        assert len(issues) == 4

        # Filter existing
        v1_issues = service.list_issues(milestone="v1.0")
        assert len(v1_issues) == 2

        # Get existing
        issue = service.get_issue("issue-1")
        assert issue is not None
        assert issue.title == "Build feature A"
