"""Policy checks for the reviewed 0.2 public-contract inventory."""

from __future__ import annotations

import csv
import dataclasses
import re
from pathlib import Path
from typing import Any

import click
import pytest
from pydantic import BaseModel

from roadmap.adapters.cli import main
from roadmap.common.configuration.config_schema import RoadmapConfig as LegacyConfig
from roadmap.common.models.config_models import RoadmapConfig as ActiveConfig
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs/architecture/compatibility-inventory-0.2.csv"
USER_REQUIREMENTS = ROOT / "docs/requirements/user-requirements.csv"
TECHNICAL_REQUIREMENTS = ROOT / "docs/requirements/technical-requirements.csv"

INVENTORY_COLUMNS = [
    "id",
    "category",
    "surface",
    "current_signature",
    "disposition",
    "target_contract",
    "target_phase",
    "owner",
    "requirements",
    "evidence",
    "migration_guidance",
]
USER_COLUMNS = [
    "id",
    "journey_id",
    "journey",
    "stage",
    "title",
    "persona",
    "requirement",
    "acceptance_criteria",
    "depends_on",
    "priority",
    "status",
    "owner",
    "source",
    "linked_work_items",
    "roadmap_target",
    "last_updated",
]
TECHNICAL_COLUMNS = [
    "id",
    "title",
    "area",
    "requirement",
    "rationale",
    "verification",
    "supports_user_requirements",
    "priority",
    "status",
    "owner",
    "source",
    "depends_on",
    "roadmap_target",
    "last_updated",
]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _split_references(value: str) -> set[str]:
    return {item.strip() for item in value.split(";") if item.strip()}


def _command_signature(command: click.Command) -> str:
    parts: list[str] = []
    for parameter in command.params:
        if isinstance(parameter, click.Argument):
            requirement = "required" if parameter.required else "optional"
            parts.append(f"arg:{parameter.name}:{requirement}")
        elif isinstance(parameter, click.Option):
            names = "|".join([*parameter.opts, *parameter.secondary_opts])
            choices = getattr(parameter.type, "choices", None)
            suffix = f"[{'|'.join(map(str, choices))}]" if choices else ""
            parts.append(f"opt:{names}{suffix}")
    return ";".join(parts) or "none"


def _cli_surfaces() -> dict[str, str]:
    surfaces: dict[str, str] = {}

    def walk(command: click.Command, path: list[str]) -> None:
        surfaces[" ".join(path)] = _command_signature(command)
        if isinstance(command, click.Group):
            for name, child in sorted(command.commands.items()):
                walk(child, [*path, name])

    walk(main, ["roadmap"])
    return surfaces


def _pydantic_keys(model: type[BaseModel], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for name, field in model.model_fields.items():
        key = f"{prefix}.{name}" if prefix else name
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            keys.update(_pydantic_keys(annotation, key))
        else:
            keys.add(key)
    return keys


def _dataclass_keys(model: type[Any], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for field in dataclasses.fields(model):
        key = f"{prefix}.{field.name}" if prefix else field.name
        annotation = field.type
        if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
            keys.update(_dataclass_keys(annotation, key))
        else:
            keys.add(key)
    return keys


def _config_surfaces() -> set[str]:
    keys = _pydantic_keys(ActiveConfig) | _dataclass_keys(LegacyConfig)
    return {f"config.{key}" for key in keys}


def _canonical_surfaces() -> set[str]:
    models = {"issue": Issue, "milestone": Milestone, "project": Project}
    return {
        f"canonical.{entity}.{field}"
        for entity, model in models.items()
        for field in model.model_fields
    }


def _assert_complete(actual: set[str], inventoried: set[str], label: str) -> None:
    missing = actual - inventoried
    extra = inventoried - actual
    assert not missing and not extra, (
        f"{label} inventory mismatch; missing={sorted(missing)}, stale={sorted(extra)}"
    )


def test_requirement_registers_are_fully_triaged_and_referentially_valid() -> None:
    """Phase 1 leaves no implicit Draft/TBD scope or broken requirement links."""
    user_header, users = _read_csv(USER_REQUIREMENTS)
    technical_header, technical = _read_csv(TECHNICAL_REQUIREMENTS)
    assert user_header == USER_COLUMNS
    assert technical_header == TECHNICAL_COLUMNS

    user_ids = {row["id"] for row in users}
    technical_ids = {row["id"] for row in technical}
    user_status = {row["id"]: row["status"] for row in users}
    technical_status = {row["id"]: row["status"] for row in technical}
    assert len(user_ids) == len(users)
    assert len(technical_ids) == len(technical)
    assert all(re.fullmatch(r"UR-\d{3}", item) for item in user_ids)
    assert all(re.fullmatch(r"TR-\d{3}", item) for item in technical_ids)

    for row in [*users, *technical]:
        assert row["status"] in {"Accepted", "Deferred", "Rejected"}
        assert row["roadmap_target"] != "TBD"
        assert row["last_updated"] == "2026-08-16"
        if row["priority"] == "Must":
            assert row["status"] == "Accepted", row["id"]
        if row["status"] == "Accepted":
            assert row["roadmap_target"].startswith("0.2.0 / Phase")
        elif row["status"] == "Deferred":
            assert row["roadmap_target"] == "Post-0.2"

    for row in users:
        dependencies = _split_references(row["depends_on"])
        assert dependencies <= user_ids
        if row["status"] == "Accepted":
            assert all(user_status[item] == "Accepted" for item in dependencies)
    for row in technical:
        dependencies = _split_references(row["depends_on"])
        supported_users = _split_references(row["supports_user_requirements"])
        assert dependencies <= technical_ids
        assert supported_users <= user_ids
        if row["status"] == "Accepted":
            assert all(technical_status[item] == "Accepted" for item in dependencies)
            assert all(user_status[item] == "Accepted" for item in supported_users)


def test_inventory_schema_references_and_remove_guidance() -> None:
    """Every reviewed surface has ownership, evidence, and a valid disposition."""
    header, rows = _read_csv(INVENTORY)
    assert header == INVENTORY_COLUMNS
    assert rows
    assert len({row["id"] for row in rows}) == len(rows)
    assert len({row["surface"] for row in rows}) == len(rows)

    _, users = _read_csv(USER_REQUIREMENTS)
    _, technical = _read_csv(TECHNICAL_REQUIREMENTS)
    requirement_ids = {row["id"] for row in [*users, *technical]}

    for row in rows:
        assert row["disposition"] in {"Preserve", "Replace", "Remove", "Internal"}
        assert row["current_signature"]
        assert row["target_contract"]
        assert row["target_phase"]
        assert row["owner"] == "Maintainer"
        assert _split_references(row["requirements"]) <= requirement_ids
        assert row["evidence"]
        if row["disposition"] == "Remove":
            assert row["migration_guidance"], row["surface"]

        for evidence in _split_references(row["evidence"]):
            assert (ROOT / evidence).exists(), (row["surface"], evidence)


def test_current_cli_config_and_canonical_surfaces_are_exactly_inventoried() -> None:
    """Actual 0.1.1 surfaces cannot grow or disappear without a contract decision."""
    _, rows = _read_csv(INVENTORY)

    cli_rows = {row["surface"]: row for row in rows if row["category"] == "cli"}
    actual_cli = _cli_surfaces()
    _assert_complete(set(actual_cli), set(cli_rows), "CLI")
    for surface, signature in actual_cli.items():
        assert cli_rows[surface]["current_signature"] == signature

    config_rows = {row["surface"] for row in rows if row["category"] == "config"}
    _assert_complete(_config_surfaces(), config_rows, "configuration")

    canonical_rows = {row["surface"] for row in rows if row["category"] == "canonical"}
    _assert_complete(_canonical_surfaces(), canonical_rows, "canonical field")


def test_inventory_guard_rejects_an_unreviewed_documented_command() -> None:
    """Negative proof: a new public command fails until inventoried."""
    actual = set(_cli_surfaces()) | {"roadmap unreviewed-command"}
    _, rows = _read_csv(INVENTORY)
    inventoried = {row["surface"] for row in rows if row["category"] == "cli"}
    with pytest.raises(AssertionError, match="unreviewed-command"):
        _assert_complete(actual, inventoried, "CLI")


def test_inventory_guard_rejects_an_unreviewed_documented_config_key() -> None:
    """Negative proof: a new public config key fails until inventoried."""
    actual = _config_surfaces() | {"config.unreviewed.key"}
    _, rows = _read_csv(INVENTORY)
    inventoried = {row["surface"] for row in rows if row["category"] == "config"}
    with pytest.raises(AssertionError, match="unreviewed.key"):
        _assert_complete(actual, inventoried, "configuration")
