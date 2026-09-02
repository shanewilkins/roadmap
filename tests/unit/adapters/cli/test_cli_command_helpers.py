"""Unit tests for shared CLI command helpers.

These exercise the real Click context/exit machinery and plain dataclass
stand-ins instead of mocks, so a test failure reflects an actual behavior
change rather than a broken mock expectation.
"""

from dataclasses import dataclass
from typing import Any

import click
import pytest

from roadmap.adapters.inbound.cli.cli_command_helpers import (
    confirm_action,
    echo_archived_list,
    echo_batch_result,
    ensure_entity_exists,
    invoke,
    projection_warning,
    require_initialized,
)
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.domain.failures import DomainFailure


@dataclass
class _Item:
    id: str
    name: str


@dataclass
class _Issue:
    id: str
    title: str


def _raise(error: Exception) -> None:
    raise error


class _FakeCollection:
    def __init__(self, items: dict[str, Any]) -> None:
        self._items = items

    def get(self, entity_id: str) -> Any:
        return self._items.get(entity_id)


class _FakeCore:
    def __init__(self, **collections: dict[str, Any]) -> None:
        for name, items in collections.items():
            setattr(self, f"{name}s", _FakeCollection(items))


class _InitializableCore:
    def __init__(self, initialized: bool) -> None:
        self._initialized = initialized

    def is_initialized(self) -> bool:
        return self._initialized


def _context(obj: dict[str, Any]) -> click.Context:
    ctx = click.Context(click.Command("test"))
    ctx.obj = obj
    return ctx


class TestInvoke:
    def test_returns_operation_result_on_success(self) -> None:
        assert invoke(lambda: 1 + 1) == 2

    @pytest.mark.parametrize(
        "error",
        [
            ApplicationFailure(FailureCategory.CONFLICT, "already archived"),
            DomainFailure("invalid transition"),
            ValueError("bad value"),
        ],
        ids=["application-failure", "domain-failure", "value-error"],
    )
    def test_translates_known_failures_to_click_exception(self, error) -> None:
        with pytest.raises(click.ClickException) as excinfo:
            invoke(lambda: _raise(error))
        assert str(excinfo.value.message) == str(error)

    def test_lets_unrelated_exceptions_propagate(self) -> None:
        with pytest.raises(RuntimeError, match="boom"):
            invoke(lambda: _raise(RuntimeError("boom")))


class TestProjectionWarning:
    def test_prints_warning_when_stale(self, capsys) -> None:
        class Result:
            projection_stale = True

        projection_warning(Result())
        assert "stale" in capsys.readouterr().out.lower()

    @pytest.mark.parametrize(
        "result",
        [type("Result", (), {"projection_stale": False})(), object()],
        ids=["explicitly-false", "attribute-missing"],
    )
    def test_silent_when_not_stale(self, capsys, result) -> None:
        projection_warning(result)
        assert capsys.readouterr().out == ""


class TestEchoBatchResult:
    def test_dry_run_uses_would_prefix_with_base_verb(self, capsys) -> None:
        echo_batch_result(
            "project", [_Item("p-1", "Alpha")], dry_run=True, action="archive"
        )
        assert capsys.readouterr().out == "Would archive project p-1: Alpha\n"

    @pytest.mark.parametrize(
        "action,expected_verb",
        [("archive", "Archived"), ("restore", "Restored")],
    )
    def test_completed_run_uses_past_tense_verb(
        self, capsys, action, expected_verb
    ) -> None:
        echo_batch_result(
            "project", [_Item("p-1", "Alpha")], dry_run=False, action=action
        )
        assert capsys.readouterr().out == f"{expected_verb} project p-1: Alpha\n"

    def test_multiple_items_each_get_their_own_line(self, capsys) -> None:
        items = [_Item("p-1", "Alpha"), _Item("p-2", "Beta")]
        echo_batch_result("project", items, dry_run=False, action="archive")
        assert capsys.readouterr().out == (
            "Archived project p-1: Alpha\nArchived project p-2: Beta\n"
        )

    def test_empty_items_prints_pluralized_no_matching_message(self, capsys) -> None:
        echo_batch_result("project", [], dry_run=False, action="archive")
        assert capsys.readouterr().out == "No matching projects.\n"

    def test_custom_label_callable_is_used_for_display_text(self, capsys) -> None:
        echo_batch_result(
            "issue",
            [_Issue("i-1", "Fix bug")],
            dry_run=False,
            action="archive",
            label=lambda issue: issue.title,
        )
        assert capsys.readouterr().out == "Archived issue i-1: Fix bug\n"


class TestEchoArchivedList:
    def test_lists_id_and_label_per_row(self, capsys) -> None:
        echo_archived_list("milestone", [_Item("m-1", "v1.0"), _Item("m-2", "v2.0")])
        assert capsys.readouterr().out == "m-1  v1.0\nm-2  v2.0\n"

    def test_empty_values_prints_pluralized_no_archived_message(self, capsys) -> None:
        echo_archived_list("milestone", [])
        assert capsys.readouterr().out == "No archived milestones.\n"

    def test_custom_label_callable_is_used_for_display_text(self, capsys) -> None:
        echo_archived_list(
            "issue", [_Issue("i-1", "Fix bug")], label=lambda issue: issue.title
        )
        assert capsys.readouterr().out == "i-1  Fix bug\n"


class TestRequireInitialized:
    def test_calls_wrapped_function_when_core_is_initialized(self) -> None:
        @require_initialized
        def command(ctx: click.Context) -> str:
            return "ran"

        result = command(_context({"core": _InitializableCore(True)}))
        assert result == "ran"

    def test_exits_1_and_prints_message_when_not_initialized(self, capsys) -> None:
        @require_initialized
        def command(ctx: click.Context) -> str:
            raise AssertionError("should not run when uninitialized")

        with pytest.raises(click.exceptions.Exit) as excinfo:
            command(_context({"core": _InitializableCore(False)}))
        assert excinfo.value.exit_code == 1
        assert "not initialized" in capsys.readouterr().out.lower()

    def test_exits_1_when_core_is_missing_entirely(self) -> None:
        @require_initialized
        def command(ctx: click.Context) -> str:
            raise AssertionError("should not run without a core")

        with pytest.raises(click.exceptions.Exit) as excinfo:
            command(_context({}))
        assert excinfo.value.exit_code == 1


class TestEnsureEntityExists:
    def test_returns_prefetched_entity_without_lookup(self) -> None:
        core = _FakeCore()
        result = ensure_entity_exists(core, "issue", "i-1", entity="prefetched")
        assert result == "prefetched"

    def test_looks_up_entity_via_matching_core_collection(self) -> None:
        core = _FakeCore(issue={"i-1": "the-issue"})
        result = ensure_entity_exists(core, "issue", "i-1")
        assert result == "the-issue"

    def test_exits_1_when_entity_not_found(self, capsys) -> None:
        core = _FakeCore(issue={})
        with pytest.raises(SystemExit) as excinfo:
            ensure_entity_exists(core, "issue", "missing")
        assert excinfo.value.code == 1
        assert "Issue not found: missing" in capsys.readouterr().out

    def test_exits_1_for_unknown_entity_type(self, capsys) -> None:
        core = _FakeCore()
        with pytest.raises(SystemExit) as excinfo:
            ensure_entity_exists(core, "widget", "id-1")
        assert excinfo.value.code == 1
        assert "Invalid entity type: widget" in capsys.readouterr().out


class TestConfirmAction:
    def test_force_skips_prompt_and_returns_true(self, monkeypatch) -> None:
        def unexpected_prompt(*_args: Any, **_kwargs: Any) -> bool:
            raise AssertionError("click.confirm should not be called when force=True")

        monkeypatch.setattr(click, "confirm", unexpected_prompt)
        assert confirm_action("Proceed?", force=True) is True

    def test_returns_true_when_user_confirms(self, monkeypatch) -> None:
        monkeypatch.setattr(click, "confirm", lambda *_a, **_k: True)
        assert confirm_action("Proceed?") is True

    def test_returns_false_and_prints_cancelled_when_user_declines(
        self, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(click, "confirm", lambda *_a, **_k: False)
        assert confirm_action("Proceed?") is False
        assert "Cancelled" in capsys.readouterr().out
