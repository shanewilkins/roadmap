"""Phase 5 contracts for canonical documents and disposable projections."""

from __future__ import annotations

import gc
import shutil
import sqlite3
import threading
import warnings
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from roadmap.adapters.outbound.persistence.canonical import (
    CanonicalConflict,
    CanonicalUnitOfWork,
    WorkspaceBusy,
    WorkspaceLock,
)
from roadmap.adapters.outbound.persistence.documents import (
    DocumentError,
    DocumentRepository,
    DuplicateDocument,
    parse_document,
    serialize_document,
)
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.domain.aggregates import Issue, Milestone
from roadmap.domain.types import EntityId, IssueComment, Name, Timestamp, Title

NOW = Timestamp(datetime(2026, 8, 17, 12, tzinfo=UTC))
LATER = Timestamp(NOW.value + timedelta(minutes=1))


def _write(path: Path, values: dict, body: str = "Body\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = yaml.safe_dump(values, sort_keys=False, allow_unicode=True).rstrip()
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")
    return path


def _issue_values(identity: str = "issue-1", **updates) -> dict:
    values = {
        "schema_version": 1,
        "id": identity,
        "title": "A useful issue",
        "status": "todo",
        "priority": "medium",
        "issue_type": "feature",
        "created": NOW.value.isoformat(),
        "updated": NOW.value.isoformat(),
    }
    values.update(updates)
    return values


def _milestone_values(identity: str = "milestone-1") -> dict:
    return {
        "schema_version": 1,
        "id": identity,
        "name": "Version One",
        "status": "open",
        "created": NOW.value.isoformat(),
        "updated": NOW.value.isoformat(),
    }


def _project_values(identity: str = "project-1") -> dict:
    return {
        "schema_version": 1,
        "id": identity,
        "name": "Roadmap",
        "status": "planning",
        "priority": "high",
        "created": NOW.value.isoformat(),
        "updated": NOW.value.isoformat(),
    }


def _repository(tmp_path: Path) -> DocumentRepository:
    return DocumentRepository(tmp_path / ".roadmap")


def test_document_mapping_preserves_unicode_unknown_fields_and_markdown(tmp_path):
    path = _write(
        tmp_path / ".roadmap/issues/backlog/issue-1.md",
        _issue_values(custom={"nested": "café ☕"}, remote_ids={"tracker": 42}),
        "# Héllo\n\n- authored  \n- markdown\n",
    )

    envelope = parse_document(path, "issue")

    assert envelope.aggregate.content == "# Héllo\n\n- authored  \n- markdown\n"
    assert envelope.extra_frontmatter["custom"] == {"nested": "café ☕"}
    assert envelope.extra_frontmatter["remote_ids"] == {"tracker": 42}


def test_empty_document_serialization_has_exactly_one_final_newline(tmp_path):
    path = _write(
        tmp_path / ".roadmap/milestones/milestone-1.md",
        _milestone_values(),
        body="",
    )

    rendered = serialize_document(parse_document(path, "milestone"))

    assert rendered.endswith(b"\n")
    assert not rendered.endswith(b"\n\n")


def test_workspace_lock_metadata_has_final_newline(tmp_path):
    path = tmp_path / ".roadmap/db/canonical-write.lock"

    with WorkspaceLock(path):
        assert path.read_text().endswith("\n")


def test_legacy_naive_timestamps_are_normalized_at_the_boundary(tmp_path):
    path = _write(
        tmp_path / ".roadmap/issues/backlog/issue-1.md",
        _issue_values(created="2026-08-17T12:00:00", updated="2026-08-17T12:00:00"),
    )

    issue = parse_document(path, "issue").aggregate

    assert issue.created.value.tzinfo is UTC


@pytest.mark.parametrize(
    "values, message",
    [
        (_issue_values(schema_version=99), "unsupported schema_version"),
        (_issue_values(created="not-a-time"), "invalid created timestamp"),
        (_issue_values(title=""), "invalid issue document"),
        (_issue_values(comments="not-a-list"), "comments must be a list"),
        (
            _issue_values(comments=["not-a-mapping"]),
            "every issue comment must be a mapping",
        ),
        (_issue_values(history=[42]), "every issue history entry must be a mapping"),
    ],
)
def test_malformed_documents_fail_without_rewrite(tmp_path, values, message):
    path = _write(tmp_path / ".roadmap/issues/backlog/issue-1.md", values)
    before = path.read_bytes()

    with pytest.raises(DocumentError, match=message):
        parse_document(path, "issue")

    assert path.read_bytes() == before


def test_missing_document_returns_none(tmp_path):
    assert _repository(tmp_path).load("issue", EntityId("absent")) is None


@pytest.mark.parametrize(
    "updates,message",
    [
        ({"created": None}, "missing created timestamp"),
        ({"priority": "urgent"}, "invalid priority"),
        ({"retention": "deleted"}, "invalid retention"),
        ({"id": "../outside"}, "invalid id"),
        ({"id": None}, "missing id"),
        ({"depends_on": "issue-2"}, "depends_on must be a list"),
        ({"blocks": ["../outside"]}, "invalid blocks"),
        ({"comments": [{"id": "bad"}]}, "invalid issue comment"),
        ({"history": "not-a-list"}, "history must be a list"),
        ({"history": [{}]}, "invalid issue history"),
        ({"due_date": 42}, "missing due_date timestamp"),
        ({"schema_version": -1}, "unsupported schema_version"),
    ],
)
def test_invalid_canonical_fields_never_rewrite_user_content(
    tmp_path, updates, message
):
    path = _write(
        tmp_path / ".roadmap/issues/issue-1.md",
        _issue_values(**updates),
        "Authored content ☕\n",
    )
    before = path.read_bytes()
    with pytest.raises(DocumentError, match=message):
        parse_document(path, "issue")
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "yaml_text,message",
    [("- list", "must be a mapping"), ("title: [", "invalid YAML frontmatter")],
)
def test_invalid_frontmatter_is_rejected_without_modification(
    tmp_path, yaml_text, message
):
    path = tmp_path / "issue.md"
    path.write_text(f"---\n{yaml_text}\n---\nAuthored content\n")
    before = path.read_bytes()
    with pytest.raises(DocumentError, match=message):
        parse_document(path, "issue")
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "kind,values", [("milestone", _milestone_values()), ("project", _project_values())]
)
def test_invalid_planning_status_is_a_document_error(tmp_path, kind, values):
    path = _write(tmp_path / f"{kind}.md", {**values, "status": "invalid"})
    before = path.read_bytes()
    with pytest.raises(DocumentError, match=f"invalid {kind} document"):
        parse_document(path, kind)
    assert path.read_bytes() == before


def test_legacy_archive_layout_and_unknown_issue_type_round_trip(tmp_path):
    path = _write(
        tmp_path / ".roadmap/archive/issues/issue-1.md",
        _issue_values(
            status="archived", issue_type="legacy-type", custom={"review": "retain"}
        ),
        "Preserved body\n",
    )
    before = path.read_bytes()
    envelope = parse_document(path, "issue")
    assert isinstance(envelope.aggregate, Issue)
    assert envelope.aggregate.retention.value == "archived"
    assert envelope.aggregate.status.value == "closed"
    assert envelope.aggregate.issue_type.value == "other"
    assert path.read_bytes() == before
    path.write_bytes(serialize_document(envelope))
    reread = parse_document(path, "issue")
    assert reread.aggregate == envelope.aggregate
    assert reread.extra_frontmatter == {"custom": {"review": "retain"}}


def test_duplicate_identity_is_rejected(tmp_path):
    root = tmp_path / ".roadmap/issues"
    _write(root / "backlog/one.md", _issue_values())
    _write(root / "other/two.md", _issue_values())

    with pytest.raises(DuplicateDocument, match="duplicate issue id issue-1"):
        _repository(tmp_path).scan("issue")


def test_unit_of_work_round_trips_envelope_and_commits_canonical_first(tmp_path):
    path = _write(
        tmp_path / ".roadmap/issues/backlog/issue-1.md",
        _issue_values(custom="keep-me"),
    )
    repository = _repository(tmp_path)

    with CanonicalUnitOfWork(repository) as unit:
        issue = unit.load_issue(EntityId("issue-1"))
        assert issue is not None
        unit.save_issue(issue.rename(Title("Renamed"), LATER))
        unit.commit()

    saved = parse_document(path, "issue")
    assert isinstance(saved.aggregate, Issue)
    assert saved.aggregate.title == "Renamed"
    assert saved.aggregate.content == "Body\n"
    assert saved.extra_frontmatter["custom"] == "keep-me"


def test_serialized_comments_remain_readable_by_released_legacy_model(tmp_path):
    repository = _repository(tmp_path)
    issue = Issue(
        EntityId("issue-1"),
        NOW,
        NOW,
        title=Title("Commented"),
        comments=(IssueComment(1, "alice", "Hello", NOW, NOW),),
    )

    with CanonicalUnitOfWork(repository) as unit:
        unit.save_issue(issue)
        unit.commit()

    raw = yaml.safe_load(
        (tmp_path / ".roadmap/issues/issue-1.md").read_text().split("---", 2)[1]
    )
    assert raw["comments"][0]["issue_id"] == "issue-1"
    assert "github_url" in raw["comments"][0]


def test_unexpected_external_edit_conflicts_instead_of_overwriting(tmp_path):
    path = _write(tmp_path / ".roadmap/issues/backlog/issue-1.md", _issue_values())
    repository = _repository(tmp_path)

    with CanonicalUnitOfWork(repository) as unit:
        issue = unit.load_issue(EntityId("issue-1"))
        assert issue is not None
        unit.save_issue(issue.rename(Title("Roadmap edit"), LATER))
        path.write_text(path.read_text().replace("Body", "External edit"))
        with pytest.raises(CanonicalConflict):
            unit.commit()

    assert "External edit" in path.read_text()


def test_unit_of_work_deletes_canonical_issue_and_refreshes_projection(tmp_path):
    class Projection:
        changed = ()

        def refresh(self, changed_ids):
            self.changed = changed_ids

        def mark_stale(self):
            raise AssertionError("projection refresh should succeed")

    path = _write(tmp_path / ".roadmap/issues/backlog/issue-1.md", _issue_values())
    projection = Projection()

    with CanonicalUnitOfWork(_repository(tmp_path), projection) as unit:
        assert unit.delete_issue(EntityId("issue-1"))
        unit.commit()

    assert not path.exists()
    assert projection.changed == (EntityId("issue-1"),)


def test_delete_failure_restores_canonical_document(tmp_path):
    path = _write(tmp_path / ".roadmap/issues/backlog/issue-1.md", _issue_values())
    before = path.read_bytes()

    def fail(stage: str, _path: Path | None) -> None:
        if stage == "after_replace":
            raise OSError("delete failed")

    with CanonicalUnitOfWork(_repository(tmp_path), failure_injector=fail) as unit:
        assert unit.delete_issue(EntityId("issue-1"))
        with pytest.raises(OSError, match="delete failed"):
            unit.commit()

    assert path.read_bytes() == before


def test_interrupted_delete_recovers_to_complete_deleted_state(tmp_path):
    path = _write(tmp_path / ".roadmap/issues/backlog/issue-1.md", _issue_values())

    def crash(stage: str, _path: Path | None) -> None:
        if stage == "after_replace":
            raise SystemExit("simulated process death")

    with pytest.raises(SystemExit):
        with CanonicalUnitOfWork(_repository(tmp_path), failure_injector=crash) as unit:
            assert unit.delete_issue(EntityId("issue-1"))
            unit.commit()

    with CanonicalUnitOfWork(_repository(tmp_path)):
        pass

    assert not path.exists()


def test_write_failure_restores_complete_old_multi_document_state(tmp_path):
    issue_path = _write(
        tmp_path / ".roadmap/issues/backlog/issue-1.md", _issue_values()
    )
    milestone_path = _write(
        tmp_path / ".roadmap/milestones/milestone-1.md", _milestone_values()
    )
    before = {path: path.read_bytes() for path in (issue_path, milestone_path)}
    calls = 0

    def fail_after_first_replace(stage: str, _path: Path | None) -> None:
        nonlocal calls
        if stage == "after_replace":
            calls += 1
            if calls == 1:
                raise OSError("injected replacement failure")

    with CanonicalUnitOfWork(
        _repository(tmp_path), failure_injector=fail_after_first_replace
    ) as unit:
        issue = unit.load_issue(EntityId("issue-1"))
        milestone = unit.load_milestone(EntityId("milestone-1"))
        assert issue is not None and milestone is not None
        unit.save_issue(issue.rename(Title("New issue"), LATER))
        unit.save_milestone(milestone.rename(Name("New milestone"), LATER))
        with pytest.raises(OSError, match="injected"):
            unit.commit()

    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize(
    "failed_stage",
    ["before_validate", "after_validate", "after_journal", "before_replace"],
)
def test_failure_at_each_commit_stage_never_accepts_partial_state(
    tmp_path, failed_stage
):
    path = _write(tmp_path / ".roadmap/issues/backlog/issue-1.md", _issue_values())
    before = path.read_bytes()

    def fail(stage: str, _path: Path | None) -> None:
        if stage == failed_stage:
            raise OSError(f"failed at {stage}")

    with CanonicalUnitOfWork(_repository(tmp_path), failure_injector=fail) as unit:
        issue = unit.load_issue(EntityId("issue-1"))
        assert issue is not None
        unit.save_issue(issue.rename(Title("Never partial"), LATER))
        with pytest.raises(OSError, match=failed_stage):
            unit.commit()

    assert path.read_bytes() == before


def test_interrupted_transaction_recovers_to_complete_new_state(tmp_path):
    issue_path = _write(
        tmp_path / ".roadmap/issues/backlog/issue-1.md", _issue_values()
    )
    milestone_path = _write(
        tmp_path / ".roadmap/milestones/milestone-1.md", _milestone_values()
    )

    def crash(stage: str, _path: Path | None) -> None:
        if stage == "after_replace":
            raise SystemExit("simulated process death")

    with pytest.raises(SystemExit):
        with CanonicalUnitOfWork(_repository(tmp_path), failure_injector=crash) as unit:
            issue = unit.load_issue(EntityId("issue-1"))
            milestone = unit.load_milestone(EntityId("milestone-1"))
            assert issue is not None and milestone is not None
            unit.save_issue(issue.rename(Title("Recovered issue"), LATER))
            unit.save_milestone(milestone.rename(Name("Recovered milestone"), LATER))
            unit.commit()

    with CanonicalUnitOfWork(_repository(tmp_path)) as recovery:
        assert recovery.recover() == 0  # __enter__ already recovered it

    recovered_issue = parse_document(issue_path, "issue").aggregate
    recovered_milestone = parse_document(milestone_path, "milestone").aggregate
    assert isinstance(recovered_issue, Issue)
    assert isinstance(recovered_milestone, Milestone)
    assert recovered_issue.title == "Recovered issue"
    assert recovered_milestone.name == "Recovered milestone"


def test_concurrent_writer_times_out_without_stealing_lock(tmp_path):
    repository = _repository(tmp_path)
    result: list[type[BaseException]] = []

    with CanonicalUnitOfWork(repository):

        def contend() -> None:
            try:
                with CanonicalUnitOfWork(repository, timeout=0.05):
                    pass
            except BaseException as error:
                result.append(type(error))

        thread = threading.Thread(target=contend)
        thread.start()
        thread.join()

    assert result == [WorkspaceBusy]


def test_canonical_write_refuses_symlink_escape(tmp_path):
    repository = _repository(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("do not replace")
    target = repository.roadmap_dir / "issues/backlog/issue-1.md"
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)
    issue = Issue(EntityId("issue-1"), NOW, NOW, title=Title("Contained"))

    with CanonicalUnitOfWork(repository) as unit:
        with pytest.raises(DocumentError, match="missing YAML frontmatter"):
            unit.save_issue(issue)

    assert outside.read_text() == "do not replace"


def _canonical_set(tmp_path: Path) -> tuple[DocumentRepository, dict[Path, bytes]]:
    root = tmp_path / ".roadmap"
    paths = [
        _write(root / "projects/project-1.md", _project_values()),
        _write(root / "milestones/milestone-1.md", _milestone_values()),
        _write(root / "issues/backlog/issue-1.md", _issue_values()),
    ]
    return DocumentRepository(root), {path: path.read_bytes() for path in paths}


@pytest.mark.parametrize("damage", ["missing", "corrupt", "truncated", "old-schema"])
def test_projection_is_disposable_and_rebuilds_without_canonical_writes(
    tmp_path, damage
):
    repository, canonical = _canonical_set(tmp_path)
    projection = SQLiteProjection(tmp_path / ".roadmap/db/projection.db", repository)
    projection.rebuild()

    if damage == "missing":
        projection.path.unlink()
    elif damage == "corrupt":
        projection.path.write_bytes(b"not sqlite")
    elif damage == "truncated":
        projection.path.write_bytes(projection.path.read_bytes()[:40])
    else:
        with closing(sqlite3.connect(projection.path)) as connection:
            connection.execute(
                "UPDATE projection_meta SET value = '0' WHERE key = 'schema_version'"
            )
            connection.commit()

    assert projection.ensure_current() == "rebuilt"
    assert len(projection.query()) == 3
    assert {path: path.read_bytes() for path in canonical} == canonical


def test_manual_canonical_edit_incrementally_refreshes_projection(tmp_path):
    repository, _ = _canonical_set(tmp_path)
    projection = SQLiteProjection(tmp_path / ".roadmap/db/projection.db", repository)
    projection.rebuild()
    issue_path = tmp_path / ".roadmap/issues/backlog/issue-1.md"
    issue_path.write_text(issue_path.read_text().replace("A useful issue", "Manual"))

    assert projection.ensure_current() == "refreshed"
    issue_row = next(row for row in projection.query() if row["kind"] == "issue")
    assert issue_row["name"] == "Manual"


def test_current_projection_checks_content_without_parsing_documents(
    tmp_path, monkeypatch
):
    repository, _ = _canonical_set(tmp_path)
    projection = SQLiteProjection(tmp_path / ".roadmap/db/projection.db", repository)
    projection.rebuild()

    def fail_scan(*_args, **_kwargs):
        raise AssertionError("current documents should not be reparsed")

    monkeypatch.setattr(repository, "scan", fail_scan)

    assert projection.ensure_current() == "current"
    assert len(projection.query()) == 3


@pytest.mark.parametrize(
    "error", [sqlite3.OperationalError("disk full"), RuntimeError("projection bug")]
)
def test_projection_failure_does_not_rollback_canonical_commit(tmp_path, caplog, error):
    class FailedProjection:
        stale = False

        def refresh(self, _ids) -> None:
            raise error

        def mark_stale(self) -> None:
            self.stale = True

    projection = FailedProjection()
    repository = _repository(tmp_path)
    issue = Issue(EntityId("issue-1"), NOW, NOW, title=Title("Canonical wins"))

    with CanonicalUnitOfWork(repository, projection) as unit:
        unit.save_issue(issue)
        unit.commit()
        assert unit.projection_stale

    assert repository.load("issue", EntityId("issue-1")) is not None
    assert projection.stale
    record = next(r for r in caplog.records if "projection refresh failed" in r.message)
    assert record.exc_info is not None
    assert record.exc_info[1] is error


def test_projection_connections_emit_no_resource_warnings(tmp_path):
    repository, _ = _canonical_set(tmp_path)
    projection = SQLiteProjection(tmp_path / ".roadmap/db/projection.db", repository)

    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        projection.rebuild()
        for _ in range(10):
            projection.query()
        gc.collect()


def test_released_0_1_1_fixture_rebuilds_without_canonical_changes(tmp_path):
    fixture = Path(__file__).parents[3] / "fixtures/compatibility/v0_1_1/.roadmap"
    roadmap_dir = tmp_path / ".roadmap"
    shutil.copytree(fixture, roadmap_dir)
    canonical = {
        path.relative_to(roadmap_dir): path.read_bytes()
        for path in roadmap_dir.rglob("*.md")
    }
    projection = SQLiteProjection(
        roadmap_dir / "db/phase-5-projection.db", DocumentRepository(roadmap_dir)
    )

    projection.rebuild()

    assert len(projection.query()) == len(canonical)
    assert {
        path.relative_to(roadmap_dir): path.read_bytes()
        for path in roadmap_dir.rglob("*.md")
    } == canonical


@pytest.mark.parametrize("failure", ["rename", "cleanup", "sync"])
def test_post_commit_cleanup_failure_acknowledges_commit_and_recovers(
    tmp_path, monkeypatch, failure
):
    repository = _repository(tmp_path)
    projection = SQLiteProjection(
        repository.roadmap_dir / "db/projection.db", repository
    )
    issue = Issue(EntityId("issue-1"), NOW, NOW, title=Title("Committed exactly once"))
    with CanonicalUnitOfWork(repository, projection) as unit:
        unit.save_issue(issue)
        with monkeypatch.context() as patch:
            if failure == "cleanup":

                def inject(stage, _path):
                    if stage == "before_cleanup":
                        raise OSError("injected cleanup denial")

                patch.setattr(unit, "_inject", inject)
            elif failure == "rename":
                original = Path.rename

                def rename(path, target):
                    if Path(target).name.startswith(".completed-"):
                        raise PermissionError("injected rename denial")
                    return original(path, target)

                patch.setattr(Path, "rename", rename)
            else:
                from roadmap.adapters.outbound.persistence import canonical

                original_sync = canonical._sync_directory

                def sync(path):
                    if path == unit._transactions and any(path.glob(".completed-*")):
                        raise OSError("injected cleanup sync failure")
                    return original_sync(path)

                patch.setattr(canonical, "_sync_directory", sync)
            unit.commit()
            assert unit.cleanup_pending
            # Cleared writes mean an explicit repeated commit is a no-op.
            unit.commit()
        assert len(projection.query()) == 1
    before = repository.default_path("issue", issue).read_bytes()
    with CanonicalUnitOfWork(repository, projection):
        pass
    assert repository.default_path("issue", issue).read_bytes() == before
    assert not tuple((repository.roadmap_dir / "db/transactions").iterdir())


def test_projection_and_stale_marker_failures_preserve_commit_and_rebuild(tmp_path):
    repository = _repository(tmp_path)
    projection = SQLiteProjection(
        repository.roadmap_dir / "db/projection.db", repository
    )
    projection.rebuild()

    class FailedProjection:
        def refresh(self, _ids):
            raise sqlite3.OperationalError("disk full")

        def mark_stale(self):
            raise PermissionError("stale marker cannot be written")

    issue = Issue(EntityId("issue-1"), NOW, NOW, title=Title("Canonical wins twice"))
    with CanonicalUnitOfWork(repository, FailedProjection()) as unit:
        unit.save_issue(issue)
        unit.commit()
        assert unit.projection_stale
    before = repository.default_path("issue", issue).read_bytes()
    assert projection.ensure_current() == "refreshed"
    assert len(projection.query()) == 1
    assert repository.default_path("issue", issue).read_bytes() == before
