"""Unresolved Git hunks are invalid canonical records, including body-only hunks."""

import pytest

from roadmap.adapters.outbound.persistence.documents import (
    DocumentError,
    has_git_conflict,
    parse_document,
)
from tests.unit.adapters.persistence.test_canonical_persistence import (
    _issue_values,
    _milestone_values,
    _project_values,
    _write,
)


@pytest.mark.parametrize(
    "kind,values",
    [
        ("issue", _issue_values(status="closed")),
        ("milestone", _milestone_values()),
        ("project", _project_values()),
    ],
)
@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_unresolved_body_conflict_refuses_read_without_rewrite(
    tmp_path, kind, values, ending
):
    body = "<<<<<<< HEAD\nOur context\n=======\nTheir context\n>>>>>>> origin/master\n"
    path = _write(tmp_path / f"{kind}.md", values, body)
    path.write_bytes(path.read_bytes().replace(b"\n", ending.encode()))
    before = path.read_bytes()
    with pytest.raises(DocumentError, match="unresolved Git conflict"):
        parse_document(path, kind)
    assert path.read_bytes() == before
    _write(path, values, "Resolved context\n")
    assert parse_document(path, kind).aggregate.content.strip() == "Resolved context"


def test_inline_marker_mentions_are_not_git_hunks():
    assert not has_git_conflict("Describe <<<<<<<, ======= and >>>>>>> in prose.")


def test_diff3_and_custom_marker_width_are_rejected():
    assert has_git_conflict(
        "<<<<<<<< ours\nours\n|||||||| base\nbase\n========\ntheirs\n>>>>>>>> theirs\n"
    )
