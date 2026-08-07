"""Unit tests for GitHubLabelSyncService behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from roadmap.adapters.sync.backends.services.github_label_sync_service import (
    GitHubLabelSyncService,
)


def _build_backend(config: dict[str, Any] | None = None) -> Any:
    return SimpleNamespace(config=config or {})


def test_sync_labels_enabled_defaults_true() -> None:
    service = GitHubLabelSyncService(_build_backend())

    assert service.sync_labels_enabled() is True


def test_sync_labels_enabled_reads_config_flag() -> None:
    service = GitHubLabelSyncService(
        _build_backend({"sync_settings": {"sync_labels": False}})
    )

    assert service.sync_labels_enabled() is False


def test_get_label_client_disables_support_for_missing_methods() -> None:
    backend = _build_backend()
    backend.get_api_client = lambda: object()
    service = GitHubLabelSyncService(backend)

    client = service.get_label_client()

    assert client is None
    assert service.label_support is False


def test_get_label_client_uses_backend_label_client_when_available() -> None:
    client = SimpleNamespace(get_labels=lambda: [], create_label=lambda *_args: None)
    backend = _build_backend()
    backend.get_label_client = lambda: client
    service = GitHubLabelSyncService(backend)

    result = service.get_label_client()

    assert result is client
    assert service.label_support is True


def test_init_label_cache_populates_names_and_skips_invalid() -> None:
    service = GitHubLabelSyncService(_build_backend())
    client = SimpleNamespace(
        get_labels=lambda: [
            {"name": "status:todo"},
            {"name": "priority:high"},
            {"id": 123},
            "invalid",
        ]
    )

    success = service.init_label_cache(client)

    assert success is True
    assert service.label_cache == {"status:todo", "priority:high"}


def test_init_label_cache_returns_false_on_fetch_error() -> None:
    service = GitHubLabelSyncService(_build_backend())
    client = SimpleNamespace(
        get_labels=lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    success = service.init_label_cache(client)

    assert success is False
    assert service.label_cache == set()


def test_ensure_labels_exist_creates_only_missing_labels() -> None:
    created: list[tuple[str, str]] = []
    client = SimpleNamespace(
        get_labels=lambda: [{"name": "status:todo"}],
        create_label=lambda name, color: created.append((name, color)),
    )
    backend = _build_backend({"sync_settings": {"sync_labels": True}})
    backend.get_label_client = lambda: client
    service = GitHubLabelSyncService(backend)

    service.ensure_labels_exist(["status:todo", "priority:critical"])

    assert created == [("priority:critical", "FF0000")]
    assert service.label_cache == {"status:todo", "priority:critical"}


def test_ensure_labels_exist_skips_when_disabled() -> None:
    backend = _build_backend({"sync_settings": {"sync_labels": False}})
    backend.get_label_client = lambda: (_ for _ in ()).throw(AssertionError)
    service = GitHubLabelSyncService(backend)

    service.ensure_labels_exist(["priority:high"])

    assert service.label_cache is None
