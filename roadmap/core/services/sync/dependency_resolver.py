"""Dependency resolver for sync operations.

This module provides topological ordering of entities based on foreign key
dependencies to ensure entities are pulled/synced in the correct order.

Entity Dependency Graph:
    Projects (no dependencies)
    └── Milestones (depends on project_id)
        └── Issues (depends on milestone_id, optionally project_id)
            └── Issue Dependencies (depends on other issue IDs)
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class EntityType(str, Enum):
    """Entity types in dependency order."""

    PROJECT = "project"
    MILESTONE = "milestone"
    ISSUE = "issue"


@dataclass
class DependencyNode:
    """Represents a node in the dependency graph."""

    entity_type: EntityType
    entity_id: str
    entity_data: dict[str, Any]
    depends_on: set[str]  # Set of entity IDs this depends on


@dataclass
class ResolutionResult:
    """Result of dependency resolution."""

    ordered_entities: list[tuple[EntityType, str, dict[str, Any]]]
    """List of (entity_type, entity_id, entity_data) in dependency order."""

    circular_dependencies: list[list[str]]
    """List of circular dependency chains detected."""

    missing_dependencies: dict[str, list[str]]
    """Map of entity_id -> list of missing dependency IDs."""

    @property
    def has_errors(self) -> bool:
        """Check if resolution encountered errors."""
        return bool(self.circular_dependencies or self.missing_dependencies)


class DependencyResolver:
    """Resolves entity dependencies and provides topological ordering.

    This class analyzes foreign key relationships between entities and
    determines the correct order for creating them to avoid constraint
    violations.

    Example:
        >>> resolver = DependencyResolver()
        >>> result = resolver.resolve({
        ...     'projects': [{'id': 'p1', 'name': 'Project 1'}],
        ...     'milestones': [{'id': 'm1', 'project_id': 'p1', 'title': 'M1'}],
        ...     'issues': [{'id': 'i1', 'milestone_id': 'm1', 'title': 'Issue'}],
        ... })
        >>> # Result contains entities in order: p1, m1, i1
    """

    def __init__(self):
        """Initialize dependency resolver."""
        self._graph: dict[str, DependencyNode] = {}
        self._entity_type_map: dict[str, EntityType] = {}

    def resolve(
        self,
        entities: dict[str, list[dict[str, Any]]],
        *,
        allow_missing: bool = False,
    ) -> ResolutionResult:
        """Resolve dependencies and return topologically sorted entities.

        Args:
            entities: Dictionary mapping entity type to list of entity dicts.
                Expected keys: 'projects', 'milestones', 'issues'
            allow_missing: If True, continue even with missing dependencies.
                Missing deps will be reported but not cause failure.

        Returns:
            ResolutionResult with ordered entities and any errors found.
        """
        self._graph.clear()
        self._entity_type_map.clear()

        # Build dependency graph
        self._build_graph(entities)

        # Check for missing dependencies
        missing_deps = self._find_missing_dependencies()

        # Detect circular dependencies
        circular_deps = self._detect_circular_dependencies()

        if circular_deps:
            logger.error(
                "circular_dependencies_detected",
                cycles=circular_deps,
                count=len(circular_deps),
            )

        if missing_deps and not allow_missing:
            logger.error(
                "missing_dependencies_detected",
                missing=missing_deps,
                count=sum(len(deps) for deps in missing_deps.values()),
            )

        # Perform topological sort
        ordered = self._topological_sort(allow_missing=allow_missing)

        logger.info(
            "dependency_resolution_complete",
            total_entities=len(ordered),
            projects=sum(1 for et, _, _ in ordered if et == EntityType.PROJECT),
            milestones=sum(1 for et, _, _ in ordered if et == EntityType.MILESTONE),
            issues=sum(1 for et, _, _ in ordered if et == EntityType.ISSUE),
            circular_dependencies=len(circular_deps),
            missing_dependencies=len(missing_deps),
        )

        return ResolutionResult(
            ordered_entities=ordered,
            circular_dependencies=circular_deps,
            missing_dependencies=missing_deps,
        )

    def _build_graph(self, entities: dict[str, list[dict[str, Any]]]) -> None:
        """Build dependency graph from entity data.

        Args:
            entities: Dictionary mapping entity type to list of entity dicts.
        """
        # Process in dependency order: projects first, then milestones, then issues
        for entity_data in entities.get("projects", []):
            entity_id = entity_data.get("id")
            if not entity_id:
                logger.warning("project_missing_id", data=entity_data)
                continue

            node = DependencyNode(
                entity_type=EntityType.PROJECT,
                entity_id=entity_id,
                entity_data=entity_data,
                depends_on=set(),  # Projects have no dependencies
            )
            self._graph[entity_id] = node
            self._entity_type_map[entity_id] = EntityType.PROJECT

        for entity_data in entities.get("milestones", []):
            entity_id = entity_data.get("id")
            if not entity_id:
                logger.warning("milestone_missing_id", data=entity_data)
                continue

            depends_on = set()
            project_id = entity_data.get("project_id")
            if project_id:
                depends_on.add(project_id)

            # Support milestone-to-milestone dependencies
            depends_on_milestone_id = entity_data.get("depends_on_milestone_id")
            if depends_on_milestone_id:
                depends_on.add(depends_on_milestone_id)

            node = DependencyNode(
                entity_type=EntityType.MILESTONE,
                entity_id=entity_id,
                entity_data=entity_data,
                depends_on=depends_on,
            )
            self._graph[entity_id] = node
            self._entity_type_map[entity_id] = EntityType.MILESTONE

        for entity_data in entities.get("issues", []):
            entity_id = entity_data.get("id")
            if not entity_id:
                logger.warning("issue_missing_id", data=entity_data)
                continue

            depends_on = set()

            # Issues depend on milestone (required FK in schema)
            milestone_id = entity_data.get("milestone_id")
            if milestone_id:
                depends_on.add(milestone_id)

            # Issues optionally depend on project (FK with ON DELETE CASCADE)
            project_id = entity_data.get("project_id")
            if project_id:
                depends_on.add(project_id)

            # Note: issue.depends_on (blocking relationships) are handled separately
            # Those are soft dependencies and don't affect FK constraints

            node = DependencyNode(
                entity_type=EntityType.ISSUE,
                entity_id=entity_id,
                entity_data=entity_data,
                depends_on=depends_on,
            )
            self._graph[entity_id] = node
            self._entity_type_map[entity_id] = EntityType.ISSUE

    def _find_missing_dependencies(self) -> dict[str, list[str]]:
        """Find dependencies that don't exist in the graph.

        Returns:
            Dictionary mapping entity_id to list of missing dependency IDs.
        """
        missing: dict[str, list[str]] = {}

        for entity_id, node in self._graph.items():
            missing_deps = []
            for dep_id in node.depends_on:
                if dep_id not in self._graph:
                    missing_deps.append(dep_id)

            if missing_deps:
                missing[entity_id] = missing_deps

        return missing

    def _detect_circular_dependencies(self) -> list[list[str]]:
        """Detect circular dependency chains using DFS.

        Returns:
            List of circular dependency chains (each chain is a list of entity IDs).
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(entity_id: str) -> bool:
            """DFS helper to detect cycles."""
            visited.add(entity_id)
            rec_stack.add(entity_id)
            path.append(entity_id)

            node = self._graph.get(entity_id)
            if node:
                for dep_id in node.depends_on:
                    if dep_id not in self._graph:
                        # Skip missing dependencies
                        continue

                    if dep_id not in visited:
                        if dfs(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        # Found a cycle - extract the cycle from path
                        cycle_start = path.index(dep_id)
                        cycle = path[cycle_start:] + [dep_id]
                        cycles.append(cycle)
                        return True

            path.pop()
            rec_stack.remove(entity_id)
            return False

        for entity_id in self._graph:
            if entity_id not in visited:
                dfs(entity_id)

        return cycles

    def _topological_sort(
        self, *, allow_missing: bool = False
    ) -> list[tuple[EntityType, str, dict[str, Any]]]:
        """Perform topological sort using Kahn's algorithm.

        Args:
            allow_missing: If True, ignore missing dependencies during sort.

        Returns:
            List of (entity_type, entity_id, entity_data) tuples in dependency order.
        """
        # Calculate in-degree for each node
        in_degree: dict[str, int] = defaultdict(int)
        adj_list: dict[str, list[str]] = defaultdict(list)

        for entity_id, node in self._graph.items():
            for dep_id in node.depends_on:
                if not allow_missing and dep_id not in self._graph:
                    # Skip nodes with missing dependencies unless allow_missing=True
                    continue

                if dep_id in self._graph:
                    adj_list[dep_id].append(entity_id)
                    in_degree[entity_id] += 1

        # Initialize queue with nodes that have no dependencies
        queue: deque[str] = deque()
        for entity_id in self._graph:
            if in_degree[entity_id] == 0:
                queue.append(entity_id)

        result: list[tuple[EntityType, str, dict[str, Any]]] = []

        while queue:
            entity_id = queue.popleft()
            node = self._graph[entity_id]

            result.append((node.entity_type, entity_id, node.entity_data))

            # Reduce in-degree for neighbors
            for neighbor_id in adj_list[entity_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        # If allow_missing and we didn't process all nodes, still include them
        if allow_missing and len(result) < len(self._graph):
            processed_ids = {entity_id for _, entity_id, _ in result}
            for entity_id, node in self._graph.items():
                if entity_id not in processed_ids:
                    result.append((node.entity_type, entity_id, node.entity_data))
                    logger.warning(
                        "entity_with_unresolved_dependencies",
                        entity_id=entity_id,
                        entity_type=node.entity_type.value,
                        depends_on=list(node.depends_on),
                    )

        return result
