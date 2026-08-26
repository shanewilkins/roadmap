"""Guard the retained suite against low-signal test debt."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"
REMOVED_TEST_IMPORTS = (
    "roadmap.application.services",
    "roadmap.common",
    "roadmap.core",
    "roadmap.infrastructure",
    "roadmap.presentation",
    "tests.unit.common",
)


def _test_sources() -> list[Path]:
    return sorted(TESTS.rglob("test_*.py"))


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_suite_contains_no_silent_skip_or_xfail() -> None:
    offenders = []
    for path in _test_sources():
        for node in ast.walk(_tree(path)):
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            if node.func.attr in {"skip", "xfail"}:
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert offenders == []


def test_suite_contains_no_disabled_test_files() -> None:
    assert sorted(TESTS.rglob("test_*.py.skip")) == []


def test_test_module_names_are_unique() -> None:
    names = Counter(path.name for path in _test_sources())
    assert sorted(name for name, count in names.items() if count > 1) == []


def test_tests_do_not_import_removed_namespaces_or_old_test_utilities() -> None:
    offenders = []
    for path in _test_sources():
        for node in ast.walk(_tree(path)):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            if node.module.startswith(REMOVED_TEST_IMPORTS):
                offenders.append(
                    f"{path.relative_to(ROOT)}:{node.lineno}:{node.module}"
                )
    assert offenders == []


def test_assertions_do_not_accept_both_a_condition_and_its_negation() -> None:
    offenders = []
    for path in _test_sources():
        for node in ast.walk(_tree(path)):
            if not isinstance(node, ast.Assert) or not isinstance(
                node.test, ast.BoolOp
            ):
                continue
            if not isinstance(node.test.op, ast.Or) or len(node.test.values) != 2:
                continue
            left, right = node.test.values
            if not isinstance(left, ast.Compare) or not isinstance(right, ast.Compare):
                continue
            same_operands = ast.dump(left.left) == ast.dump(right.left) and tuple(
                ast.dump(item) for item in left.comparators
            ) == tuple(ast.dump(item) for item in right.comparators)
            operators = {type(left.ops[0]), type(right.ops[0])}
            if same_operands and operators == {ast.Eq, ast.NotEq}:
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert offenders == []
