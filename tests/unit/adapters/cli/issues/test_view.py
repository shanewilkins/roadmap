"""Contracts for resolving user-facing issue ID prefixes."""

import click
import pytest

from roadmap.adapters.cli.issues.resolution import resolve_issue_id
from roadmap.domain.types import EntityId


class _IssueIdentities:
    def __init__(self, *identities: str) -> None:
        self._identities = tuple(EntityId(identity) for identity in identities)

    def ids(self) -> tuple[EntityId, ...]:
        return self._identities


class _Core:
    def __init__(self, *identities: str) -> None:
        self.issue_queries = _IssueIdentities(*identities)


def test_complete_identity_wins_even_when_it_prefixes_another_identity() -> None:
    core = _Core("abc", "abcdef")

    assert resolve_issue_id(core, "abc") == EntityId("abc")


def test_unique_prefix_resolves_to_complete_identity() -> None:
    core = _Core("abcdef", "uvwxyz")

    assert resolve_issue_id(core, "abc") == EntityId("abcdef")


def test_ambiguous_prefix_is_rejected() -> None:
    core = _Core("abcdef", "abcxyz")

    with pytest.raises(click.ClickException, match="Ambiguous issue ID prefix"):
        resolve_issue_id(core, "abc")


def test_missing_prefix_is_rejected() -> None:
    core = _Core("abcdef")

    with pytest.raises(click.ClickException, match="was not found"):
        resolve_issue_id(core, "missing")
