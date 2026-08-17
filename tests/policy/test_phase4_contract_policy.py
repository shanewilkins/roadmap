"""Phase 4 contract and mapping policy."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_domain_and_application_contracts_import_only_inward() -> None:
    domain_imports: set[str] = set()
    application_imports: set[str] = set()
    for path in (ROOT / "roadmap/domain").glob("*.py"):
        domain_imports.update(_imports(path))
    for path in (ROOT / "roadmap/application").glob("*.py"):
        application_imports.update(_imports(path))

    assert not {name for name in domain_imports if name.startswith("roadmap.")}
    assert not {
        name
        for name in application_imports
        if name.startswith("roadmap.") and not name.startswith("roadmap.domain")
    }


def test_every_inventory_field_has_a_phase4_target_mapping() -> None:
    mapping = (
        ROOT / "docs/architecture/domain-application-contracts-0.2.md"
    ).read_text(encoding="utf-8")

    covered: set[int] = set()
    for start, end in re.findall(r"CAN-(\d{3})(?:–CAN-(\d{3}))?", mapping):
        covered.update(range(int(start), int(end or start) + 1))

    assert covered == set(range(1, 73))
