"""Unit tests for DependencyResolver service."""

from unittest.mock import Mock

import pytest

from roadmap.core.services.sync.dependency_resolver import (
    DependencyResolver,
    EntityType,
    ResolutionResult,
)


class TestDependencyResolver:
    """Test suite for DependencyResolver class."""

    def test_simple_project_milestone_issue_chain(self):
        """Test basic dependency chain: Project -> Milestone -> Issue."""
        resolver = DependencyResolver()
        entities = {
            "projects": [{"id": "p1", "name": "Project 1"}],
            "milestones": [
                {
                    "id": "m1",
                    "project_id": "p1",
                    "title": "Milestone 1",
                }
            ],
            "issues": [
                {
                    "id": "i1",
                    "milestone_id": "m1",
                    "title": "Issue 1",
                }
            ],
        }

        result = resolver.resolve(entities)

        assert not result.has_errors
        assert len(result.ordered_entities) == 3
        assert result.ordered_entities[0][0] == EntityType.PROJECT
        assert result.ordered_entities[0][1] == "p1"
        assert result.ordered_entities[1][0] == EntityType.MILESTONE
        assert result.ordered_entities[1][1] == "m1"
        assert result.ordered_entities[2][0] == EntityType.ISSUE
        assert result.ordered_entities[2][1] == "i1"

    def test_multiple_projects_and_milestones(self):
        """Test multiple projects each with their own milestones."""
        resolver = DependencyResolver()
        entities = {
            "projects": [
                {"id": "p1", "name": "Project 1"},
                {"id": "p2", "name": "Project 2"},
            ],
            "milestones": [
                {"id": "m1", "project_id": "p1", "title": "M1"},
                {"id": "m2", "project_id": "p2", "title": "M2"},
                {"id": "m3", "project_id": "p1", "title": "M3"},
            ],
            "issues": [],
        }

        result = resolver.resolve(entities)

        assert not result.has_errors
        assert len(result.ordered_entities) == 5

        # All projects should come before any milestones
        project_positions = [
            i
            for i, (et, _, _) in enumerate(result.ordered_entities)
            if et == EntityType.PROJECT
        ]
        milestone_positions = [
            i
            for i, (et, _, _) in enumerate(result.ordered_entities)
            if et == EntityType.MILESTONE
        ]

        assert max(project_positions) < min(milestone_positions)

    def test_milestone_depends_on_milestone(self):
        """Test milestone dependencies between milestones (not yet implemented)."""
        # NOTE: Milestone-to-milestone dependencies are not yet implemented
        # This test is a placeholder for when that feature is added (Task 12)
        pytest.skip(
            "Milestone-to-milestone dependencies not yet implemented in DependencyResolver"
        )

    def test_missing_milestone_dependency(self):
        """Test detection of missing milestone dependency (not yet implemented)."""
        # NOTE: Milestone-to-milestone dependencies are not yet implemented
        pytest.skip(
            "Milestone-to-milestone dependencies not yet implemented in DependencyResolver"
        )

    def test_missing_project_dependency(self):
        """Test detection of missing project dependency."""
        resolver = DependencyResolver()
        entities = {
            "projects": [],
            "milestones": [
                {
                    "id": "m1",
                    "project_id": "missing_p",
                    "title": "M1",
                }
            ],
            "issues": [],
        }

        result = resolver.resolve(entities)

        assert result.has_errors
        assert "m1" in result.missing_dependencies
        assert "missing_p" in result.missing_dependencies["m1"]

    def test_allow_missing_dependencies_flag(self):
        """Test that allow_missing flag allows resolution to continue."""
        resolver = DependencyResolver()
        entities = {
            "projects": [],
            "milestones": [
                {
                    "id": "m1",
                    "project_id": "missing_p",
                    "title": "M1",
                }
            ],
            "issues": [],
        }

        result = resolver.resolve(entities, allow_missing=True)

        # Should have missing deps reported but still return ordered entities
        assert result.has_errors
        assert "m1" in result.missing_dependencies
        assert len(result.ordered_entities) > 0

    def test_circular_dependency_detection_two_milestones(self):
        """Test detection of circular dependency between two milestones (not yet implemented)."""
        # NOTE: Milestone-to-milestone dependencies are not yet implemented
        pytest.skip(
            "Milestone-to-milestone dependencies not yet implemented in DependencyResolver"
        )

    def test_circular_dependency_detection_three_milestones(self):
        """Test detection of circular dependency chain (not yet implemented)."""
        # NOTE: Milestone-to-milestone dependencies are not yet implemented
        pytest.skip(
            "Milestone-to-milestone dependencies not yet implemented in DependencyResolver"
        )

    def test_self_referencing_milestone(self):
        """Test detection of milestone depending on itself (not yet implemented)."""
        # NOTE: Milestone-to-milestone dependencies are not yet implemented
        pytest.skip(
            "Milestone-to-milestone dependencies not yet implemented in DependencyResolver"
        )

    def test_complex_dependency_graph(self):
        """Test complex dependency graph with multiple branches."""
        resolver = DependencyResolver()
        entities = {
            "projects": [
                {"id": "p1", "name": "Project 1"},
                {"id": "p2", "name": "Project 2"},
            ],
            "milestones": [
                # Project 1 milestones (no milestone-to-milestone deps yet)
                {"id": "m1", "project_id": "p1", "title": "M1"},
                {"id": "m2", "project_id": "p1", "title": "M2"},
                {"id": "m3", "project_id": "p1", "title": "M3"},
                {"id": "m4", "project_id": "p1", "title": "M4"},
                # Project 2 milestones (independent)
                {"id": "m5", "project_id": "p2", "title": "M5"},
            ],
            "issues": [
                {"id": "i1", "milestone_id": "m1", "title": "Issue 1"},
                {"id": "i2", "milestone_id": "m4", "title": "Issue 2"},
            ],
        }

        result = resolver.resolve(entities)

        assert not result.has_errors
        assert len(result.ordered_entities) == 9

        # Find positions
        positions = {}
        for i, (et, eid, _) in enumerate(result.ordered_entities):
            positions[eid] = i

        # Verify project comes before its milestones
        assert positions["p1"] < positions["m1"]
        assert positions["p2"] < positions["m5"]

        # Verify milestones come before their issues
        assert positions["m1"] < positions["i1"]
        assert positions["m4"] < positions["i2"]

    def test_empty_entities_dict(self):
        """Test resolution with empty entities."""
        resolver = DependencyResolver()
        result = resolver.resolve({})

        assert not result.has_errors
        assert len(result.ordered_entities) == 0
        assert len(result.circular_dependencies) == 0
        assert len(result.missing_dependencies) == 0

    def test_entities_with_missing_ids(self):
        """Test that entities without IDs are skipped."""
        resolver = DependencyResolver()
        entities = {
            "projects": [
                {"name": "Project without ID"},  # Missing id
                {"id": "p1", "name": "Project 1"},
            ],
            "milestones": [
                {"title": "Milestone without ID"},  # Missing id
                {"id": "m1", "project_id": "p1", "title": "M1"},
            ],
            "issues": [],
        }

        result = resolver.resolve(entities)

        assert not result.has_errors
        # Should only have entities with valid IDs
        assert len(result.ordered_entities) == 2
        ids = [eid for _, eid, _ in result.ordered_entities]
        assert "p1" in ids
        assert "m1" in ids

    def test_milestone_without_project(self):
        """Test milestone without project_id dependency."""
        resolver = DependencyResolver()
        entities = {
            "projects": [],
            "milestones": [
                {
                    "id": "m1",
                    # No project_id
                    "title": "Standalone milestone",
                }
            ],
            "issues": [],
        }

        result = resolver.resolve(entities, allow_missing=True)

        # Should work - milestone can exist without project
        assert len(result.ordered_entities) == 1
        assert result.ordered_entities[0][1] == "m1"

    def test_issue_depends_on_milestone(self):
        """Test that issues properly depend on their milestones."""
        resolver = DependencyResolver()
        entities = {
            "projects": [{"id": "p1", "name": "Project 1"}],
            "milestones": [
                {"id": "m1", "project_id": "p1", "title": "M1"},
                {"id": "m2", "project_id": "p1", "title": "M2"},
            ],
            "issues": [
                {"id": "i1", "milestone_id": "m1", "title": "Issue 1"},
                {"id": "i2", "milestone_id": "m2", "title": "Issue 2"},
                {"id": "i3", "milestone_id": "m1", "title": "Issue 3"},
            ],
        }

        result = resolver.resolve(entities)

        assert not result.has_errors
        assert len(result.ordered_entities) == 6

        # Find positions
        positions = {}
        for i, (_, eid, _) in enumerate(result.ordered_entities):
            positions[eid] = i

        # All issues should come after their milestones
        assert positions["m1"] < positions["i1"]
        assert positions["m1"] < positions["i3"]
        assert positions["m2"] < positions["i2"]

    def test_resolution_result_properties(self):
        """Test ResolutionResult properties."""
        result = ResolutionResult(
            ordered_entities=[],
            circular_dependencies=[],
            missing_dependencies={},
        )
        assert not result.has_errors

        result_with_circular = ResolutionResult(
            ordered_entities=[],
            circular_dependencies=[["m1", "m2"]],
            missing_dependencies={},
        )
        assert result_with_circular.has_errors

        result_with_missing = ResolutionResult(
            ordered_entities=[],
            circular_dependencies=[],
            missing_dependencies={"m1": ["p1"]},
        )
        assert result_with_missing.has_errors
