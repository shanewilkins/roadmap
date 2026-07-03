"""Tests for GitHubEntityClassifier."""

from unittest.mock import MagicMock

from roadmap.core.services.github.github_entity_classifier import GitHubEntityClassifier


class _Entity:
    def __init__(self, archived):
        self.archived = archived


class _NoArchivedAttr:
    pass


def test_classify_entity_state_true_for_bool_true():
    """Classifier should return True for archived=True."""
    assert GitHubEntityClassifier.classify_entity_state(_Entity(True)) is True


def test_classify_entity_state_false_for_missing_attr():
    """Missing archived attribute should be treated as active."""
    assert GitHubEntityClassifier.classify_entity_state(_NoArchivedAttr()) is False


def test_classify_entity_state_false_for_non_bool_archived():
    """Non-bool archived values should not be considered archived."""
    entity = _Entity(MagicMock(name="not_bool"))
    assert GitHubEntityClassifier.classify_entity_state(entity) is False


def test_separate_by_state_partitions_mixed_entities():
    """Entities should be split by archived state in stable order."""
    active_1 = _Entity(False)
    archived_1 = _Entity(True)
    active_2 = _NoArchivedAttr()

    active, archived = GitHubEntityClassifier.separate_by_state(
        [active_1, archived_1, active_2]
    )

    assert active == [active_1, active_2]
    assert archived == [archived_1]


def test_separate_by_state_handles_all_archived_and_all_active():
    """Edge cases with fully archived or fully active lists should work."""
    all_archived = [_Entity(True), _Entity(True)]
    active, archived = GitHubEntityClassifier.separate_by_state(all_archived)
    assert active == []
    assert archived == all_archived

    all_active = [_Entity(False), _NoArchivedAttr()]
    active, archived = GitHubEntityClassifier.separate_by_state(all_active)
    assert active == all_active
    assert archived == []
