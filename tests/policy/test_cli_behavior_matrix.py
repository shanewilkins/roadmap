"""Require reviewed contracts and real evidence when the CLI surface changes."""

import ast
import json
from pathlib import Path

import click

from roadmap.bootstrap import cli
from tests.policy.test_public_contract_inventory_policy import _cli_surfaces

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs/architecture/cli-behavior-matrix.json"
SAFETY_PARAMETERS = {
    "roadmap health fix": {"repair_type", "dry_run", "confirmed"},
    "roadmap migrate": {"dry_run", "yes"},
    "roadmap issue archive": {"dry_run", "yes", "force"},
    "roadmap milestone archive": {"dry_run", "yes", "force"},
    "roadmap project archive": {"dry_run", "yes", "force"},
}


def _live_parameters():
    result = {}

    def walk(command, path):
        result[path] = command.params
        if isinstance(command, click.Group):
            context = click.Context(command)
            for name in command.list_commands(context):
                walk(command.get_command(context, name), f"{path} {name}")

    walk(cli, "roadmap")
    return result


def _test_ids(path: Path) -> set[str]:
    result = set()
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            result.add(node.name)
        if isinstance(node, ast.ClassDef):
            result.update(
                f"{node.name}::{child.name}"
                for child in node.body
                if isinstance(child, ast.FunctionDef) and child.name.startswith("test_")
            )
    return result


def test_live_cli_requires_reviewed_roster_and_behavioral_evidence():
    matrix = json.loads(MATRIX.read_text())
    assert matrix["schema_version"] == 1
    commands = matrix["commands"]
    actual = _cli_surfaces()
    live_parameters = _live_parameters()
    assert set(commands) == set(actual)
    for surface, signature in actual.items():
        row = commands[surface]
        assert row["signature"] == signature, surface
        assert row["contract"] and row["evidence"] and not row["unresolved"], surface
        for parameter in row["parameters"]:
            assert parameter["disposition"] in {"supported", "deprecated_until_0.4"}
            assert (
                parameter["contract"]
                and parameter["evidence"]
                and parameter["spellings"]
            )
        assert len(row["parameters"]) == len(live_parameters[surface]), surface
        for reviewed, live in zip(
            row["parameters"], live_parameters[surface], strict=True
        ):
            assert reviewed["parameter"] == live.name, surface
            assert reviewed["required"] == live.required, surface
            assert reviewed["default"] == json.loads(
                json.dumps(live.default, default=str)
            ), surface
            assert reviewed["choices"] == list(getattr(live.type, "choices", [])), (
                surface
            )
            spellings = (
                [*live.opts, *live.secondary_opts]
                if isinstance(live, click.Option)
                else [live.name]
            )
            assert reviewed["spellings"] == spellings, surface


def test_matrix_evidence_references_existing_journeys():
    commands = json.loads(MATRIX.read_text())["commands"]
    references = set()
    for surface, row in commands.items():
        references.update(row["evidence"])
        for parameter in row["parameters"]:
            evidence = parameter["evidence"]
            if parameter["parameter"] in SAFETY_PARAMETERS.get(surface, set()):
                assert isinstance(evidence, list) and evidence
            if evidence != "command":
                assert isinstance(evidence, list) and evidence
                references.update(evidence)
    cache = {}
    for reference in sorted(references):
        filename, identifier = reference.split("::", 1)
        path = ROOT / filename
        assert path.is_file(), reference
        if filename not in cache:
            cache[filename] = _test_ids(path)
        assert identifier in cache[filename], reference
        # Help is evidence for namespaces only, not a command's side effects.
        assert filename.startswith("tests/integration/") or filename.endswith(
            "test_failure_diagnostics.py"
        )
