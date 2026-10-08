"""Keep active documentation links usable without making network requests."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[2]
PARSER = MarkdownIt("commonmark")


def _anchors(path: Path) -> set[str]:
    anchors = set()
    counts: dict[str, int] = {}
    tokens = PARSER.parse(path.read_text(encoding="utf-8"))
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        children = tokens[index + 1].children or []
        title = "".join(
            child.content for child in children if child.type in {"text", "code_inline"}
        )
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(f"{slug}-{count}" if count else slug)
    return anchors


def _broken_links(paths: list[Path]) -> list[str]:
    failures = []
    cache: dict[Path, set[str]] = {}
    for source in paths:
        for token in PARSER.parse(source.read_text(encoding="utf-8")):
            for child in token.children or []:
                attribute = "src" if child.type == "image" else "href"
                destination = child.attrGet(attribute)
                if not isinstance(destination, str) or not destination:
                    continue
                url = urlsplit(destination)
                if url.scheme or url.netloc:
                    continue
                target = (source.parent / unquote(url.path)).resolve()
                if not url.path:
                    target = source
                if not target.exists():
                    failures.append(f"{source}: missing target {destination}")
                elif url.fragment and target.suffix.lower() == ".md":
                    if target not in cache:
                        cache[target] = _anchors(target)
                    if unquote(url.fragment) not in cache[target]:
                        failures.append(f"{source}: missing heading {destination}")
    return failures


def test_active_documentation_links_resolve():
    paths = [ROOT / name for name in ("README.md", "CONTRIBUTING.md", "SECURITY.md")]
    paths.extend(sorted((ROOT / "docs").rglob("*.md")))
    paths.append(ROOT / "scripts/README.md")
    assert not (failures := _broken_links(paths)), "\n".join(failures)


@pytest.mark.parametrize(
    "link",
    ["missing.md", "target%20file.md#missing", "missing.png"],
)
def test_link_audit_rejects_missing_targets_and_headings(tmp_path, link):
    source = tmp_path / "README.md"
    source.write_text(f"[reference]({link})\n![image]({link})\n")
    (tmp_path / "target file.md").write_text("# Present\n")
    assert _broken_links([source])


def test_link_audit_handles_reference_links_unicode_and_duplicate_headings(tmp_path):
    source = tmp_path / "README.md"
    source.write_text(
        "# Local\n[local](#local)\n[reference][target]\n"
        "[duplicate](target%20file.md#café-code-1)\n"
        "[remote](https://example.com/missing#heading)\n"
        "[email](mailto:maintainer@example.com)\n"
        "[target]: target%20file.md#café-code\n"
    )
    (tmp_path / "target file.md").write_text("# Café `code`\n# Café `code`\n")
    assert _broken_links([source]) == []
