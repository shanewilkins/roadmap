"""Classifies GitHub entities (active/archived)."""

from typing import Any, TypeVar

T = TypeVar("T")


class GitHubEntityClassifier:
    """Separates entities into active and archived categories."""

    @staticmethod
    def classify_entity_state(entity: Any) -> bool:
        """Determine if entity is archived.

        Args:
            entity: Entity object to check

        Returns:
            True if archived, False if active

        Note:
            Handles mocks safely by checking isinstance
        """
        is_archived = False
        if hasattr(entity, "archived"):
            archived_attr = getattr(entity, "archived", False)
            # Check if it's an actual boolean value, not a mock
            if isinstance(archived_attr, bool):
                is_archived = archived_attr
        return is_archived

    @classmethod
    def separate_by_state(cls, entities: list[T]) -> tuple[list[T], list[T]]:
        """Separate entities into active and archived.

        Args:
            entities: List of entities to classify

        Returns:
            Tuple of (active_entities, archived_entities)
        """
        active = []
        archived = []

        for entity in entities:
            if cls.classify_entity_state(entity):
                archived.append(entity)
            else:
                active.append(entity)

        return active, archived
