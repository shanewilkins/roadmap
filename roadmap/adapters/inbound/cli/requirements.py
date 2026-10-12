"""Capture optional requirements through Application-owned capabilities."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import (
    invoke,
    projection_warning,
    require_initialized,
)
from roadmap.application.use_cases.requirements import criteria
from roadmap.domain.types import Priority, RequiredText


def _json(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot encode {type(value).__name__}")


def _record(value):
    return {
        **asdict(value),
        "current_revision": value.current_revision,
        "uncaptured_intent": value.uncaptured_intent,
    }


def _emit(kind, value):
    click.echo(
        json.dumps(
            {"schema_version": 1, "kind": kind, **value},
            default=_json,
            ensure_ascii=False,
            indent=2,
        )
    )


def _statement(text, path, required=False):
    if text is not None and path is not None:
        raise click.UsageError("Choose --statement or --statement-file")
    if path is not None:
        return path.read_text(encoding="utf-8")
    if required and text is None:
        raise click.UsageError("Provide --statement or --statement-file")
    return text


@click.group()
def requirement():
    """Capture, inspect and edit optional requirements."""


@requirement.command("enable")
@click.option(
    "--apply", is_flag=True, help="Explicitly upgrade the workspace; default previews."
)
@click.pass_context
@require_initialized
def enable(ctx, apply):
    """Opt in; upgraded workspaces require a requirements-aware Roadmap version."""
    result = invoke(lambda: ctx.obj["core"].requirements.enable(apply=apply))
    projection_warning(result)
    _emit("roadmap.requirement-adoption", asdict(result))


@requirement.command("create")
@click.option("--type", "kind", type=click.Choice(["user", "technical"]), required=True)
@click.option("--title", required=True)
@click.option("--statement")
@click.option(
    "--statement-file", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--criterion",
    "criterion_values",
    multiple=True,
    required=True,
    help="Named criterion ID=TEXT; repeat as needed.",
)
@click.option("--key", help="Explicit free UR/TR alias; default allocates under lock.")
@click.option("--rationale", default="")
@click.option("--scope", default="")
@click.option(
    "--priority", type=click.Choice([x.value for x in Priority]), default="medium"
)
@click.option("--owner")
@click.option("--journey")
@click.option("--stage")
@click.pass_context
@require_initialized
def create(
    ctx,
    kind,
    title,
    statement,
    statement_file,
    criterion_values,
    key,
    rationale,
    scope,
    priority,
    owner,
    journey,
    stage,
):
    """Create a Draft requirement with stable UUID and named criteria."""
    body = _statement(statement, statement_file, True)
    result = invoke(
        lambda: ctx.obj["core"].requirements.create(
            kind=kind,
            title=title,
            statement=body,
            criterion_values=criterion_values,
            key=key,
            rationale=rationale,
            scope=scope,
            priority=Priority(priority),
            owner=owner,
            journey=journey,
            stage=stage,
        )
    )
    projection_warning(result)
    _emit("roadmap.requirement", {"requirement": _record(result.requirement)})


@requirement.command("view")
@click.argument("selector")
@click.pass_context
@require_initialized
def view(ctx, selector):
    """Inspect by exact full UUID or unambiguous readable alias."""
    result = invoke(lambda: ctx.obj["core"].requirements.view(selector))
    _emit("roadmap.requirement", {"requirement": _record(result)})


@requirement.command("list")
@click.option("--type", "kind", type=click.Choice(["user", "technical"]))
@click.option("--priority", type=click.Choice([x.value for x in Priority]))
@click.option("--status", type=click.Choice(["draft"]))
@click.option("--owner")
@click.option("--journey")
@click.option("--stage")
@click.option("--search", default="")
@click.option(
    "--sort",
    type=click.Choice(["key", "title", "priority", "created", "updated"]),
    default="key",
)
@click.pass_context
@require_initialized
def list_requirements(ctx, kind, priority, status, owner, journey, stage, search, sort):
    """Return deterministic versioned JSON; no canonical writes."""
    filters = {
        name: value
        for name, value in {
            "type": kind,
            "priority": priority,
            "status": status,
            "owner": owner,
            "journey": journey,
            "stage": stage,
        }.items()
        if value is not None
    }
    result = invoke(
        lambda: ctx.obj["core"].requirements.list(
            filters=filters, search=search, sort=sort
        )
    )
    _emit("roadmap.requirements", {"requirements": [_record(x) for x in result]})


@requirement.command("update")
@click.argument("selector")
@click.option("--title")
@click.option("--statement")
@click.option(
    "--statement-file", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--criterion",
    "criterion_values",
    multiple=True,
    help="Replace all criteria with repeated ID=TEXT values.",
)
@click.option("--scope")
@click.option("--rationale")
@click.option("--priority", type=click.Choice([x.value for x in Priority]))
@click.option("--owner")
@click.option("--clear-owner", is_flag=True)
@click.option("--journey")
@click.option("--stage")
@click.option("--expected-revision", help="Refuse if intent has changed since review.")
@click.pass_context
@require_initialized
def update(
    ctx,
    selector,
    title,
    statement,
    statement_file,
    criterion_values,
    scope,
    rationale,
    priority,
    owner,
    clear_owner,
    journey,
    stage,
    expected_revision,
):
    """Edit content/metadata while preserving identity and revision history."""
    if owner is not None and clear_owner:
        raise click.UsageError("Choose --owner or --clear-owner")
    body = _statement(statement, statement_file)
    changes = {
        name: value
        for name, value in {
            "statement": body,
            "scope": scope,
            "rationale": rationale,
            "owner": owner,
            "journey": journey,
            "stage": stage,
        }.items()
        if value is not None
    }
    if title is not None:
        changes["title"] = RequiredText(title)
    if priority is not None:
        changes["priority"] = Priority(priority)
    if criterion_values:
        changes["criteria"] = invoke(lambda: criteria(criterion_values))
    if clear_owner:
        changes["owner"] = None
    if not changes:
        raise click.UsageError("Choose at least one field to update")
    result = invoke(
        lambda: ctx.obj["core"].requirements.update(
            selector, expected_revision=expected_revision, **changes
        )
    )
    projection_warning(result)
    _emit("roadmap.requirement", {"requirement": _record(result.requirement)})


@requirement.command("rekey")
@click.argument("identity")
@click.option("--key", required=True)
@click.pass_context
@require_initialized
def rekey(ctx, identity, key):
    """Resolve an alias collision by exact full UUID; preserve its file and links."""
    result = invoke(lambda: ctx.obj["core"].requirements.rekey(identity, key))
    projection_warning(result)
    _emit("roadmap.requirement", {"requirement": _record(result.requirement)})
