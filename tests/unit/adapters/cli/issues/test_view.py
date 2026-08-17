"""Contracts for resolving user-facing issue ID prefixes."""

import click
import pytest

from roadmap.adapters.cli.issues.view import _resolve_prefix
from roadmap.domain.types import EntityId


class _IssueIdentities:
    def __init__(self, *identities: str) -> None:
        self._identities = tuple(EntityId(identity) for identity in identities)

    def ids(self) -> tuple[EntityId, ...]:
        return self._identities


def test_complete_identity_wins_even_when_it_prefixes_another_identity() -> None:
    service = _IssueIdentities("abc", "abcdef")

    assert _resolve_prefix(service, "abc") == EntityId("abc")


def test_unique_prefix_resolves_to_complete_identity() -> None:
    service = _IssueIdentities("abcdef", "uvwxyz")

    assert _resolve_prefix(service, "abc") == EntityId("abcdef")


def test_ambiguous_prefix_is_rejected() -> None:
    service = _IssueIdentities("abcdef", "abcxyz")

    with pytest.raises(click.ClickException, match="Ambiguous issue ID prefix"):
        _resolve_prefix(service, "abc")


def test_missing_prefix_is_rejected() -> None:
    service = _IssueIdentities("abcdef")

    with pytest.raises(click.ClickException, match="was not found"):
        _resolve_prefix(service, "missing")
