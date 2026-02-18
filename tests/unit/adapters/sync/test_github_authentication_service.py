"""Tests for GitHub authentication service behavior."""

from __future__ import annotations

from roadmap.adapters.sync.backends.services.github_authentication_service import (
    GitHubAuthenticationService,
)


def test_authenticate_returns_false_without_token() -> None:
    service = GitHubAuthenticationService(config={"owner": "o", "repo": "r"})

    assert service.authenticate() is False


def test_authenticate_returns_false_on_client_init_import_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_authentication_service.GitHubClientWrapper",
        lambda _token: (_ for _ in ()).throw(ImportError("missing dep")),
    )
    service = GitHubAuthenticationService(
        config={"token": "tkn", "owner": "o", "repo": "r"}
    )

    assert service.authenticate() is False


def test_authenticate_returns_false_on_auth_error_codes(monkeypatch) -> None:
    class _Client:
        def fetch_issue(self, *_args):
            raise RuntimeError("401 unauthorized")

    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_authentication_service.GitHubClientWrapper",
        lambda _token: _Client(),
    )
    service = GitHubAuthenticationService(
        config={"token": "tkn", "owner": "o", "repo": "r"}
    )

    assert service.authenticate() is False


def test_authenticate_returns_true_on_non_auth_exception(monkeypatch) -> None:
    class _Client:
        def fetch_issue(self, *_args):
            raise RuntimeError("404 not found")

    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_authentication_service.GitHubClientWrapper",
        lambda _token: _Client(),
    )
    service = GitHubAuthenticationService(
        config={"token": "tkn", "owner": "o", "repo": "r"}
    )

    assert service.authenticate() is True


def test_authenticate_returns_true_on_success(monkeypatch) -> None:
    class _Client:
        def fetch_issue(self, *_args):
            return {"number": 1}

    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_authentication_service.GitHubClientWrapper",
        lambda _token: _Client(),
    )
    service = GitHubAuthenticationService(
        config={"token": "tkn", "owner": "o", "repo": "r"}
    )

    assert service.authenticate() is True


def test_authenticate_returns_false_on_generic_client_init_exception(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_authentication_service.GitHubClientWrapper",
        lambda _token: (_ for _ in ()).throw(RuntimeError("init boom")),
    )
    service = GitHubAuthenticationService(
        config={"token": "tkn", "owner": "o", "repo": "r"}
    )

    assert service.authenticate() is False


def test_authenticate_returns_false_when_outer_exception_triggered(monkeypatch) -> None:
    class _Client:
        def fetch_issue(self, *_args):
            return {"number": 1}

    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_authentication_service.GitHubClientWrapper",
        lambda _token: _Client(),
    )
    service = GitHubAuthenticationService(
        config={"token": "tkn", "owner": None, "repo": "r"}
    )

    assert service.authenticate() is False
