"""Canonical Markdown document mapping and lookup."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import (
    EntityId,
    IssueComment,
    IssueEvent,
    IssueRelations,
    IssueStatus,
    IssueType,
    MilestoneRelation,
    MilestoneStatus,
    Name,
    Priority,
    ProjectRelations,
    ProjectStatus,
    RetentionState,
    Timestamp,
    Title,
)

type DocumentKind = Literal["issue", "milestone", "project"]
type Aggregate = Issue | Milestone | Project
_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n(.*)\Z", re.S)


class DocumentError(ValueError):
    """A canonical document is absent, malformed, or incompatible."""


class DuplicateDocument(DocumentError):
    """More than one canonical document claims the same identity."""


@dataclass(frozen=True, slots=True)
class DocumentEnvelope:
    """Mapped aggregate plus boundary-owned data that must round-trip."""

    kind: DocumentKind
    aggregate: Aggregate
    path: Path
    extra_frontmatter: dict[str, Any]
    schema_version: int = 1

    @property
    def identity(self) -> str:
        return str(self.aggregate.id)


def content_identity(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _timestamp(value: Any, field: str) -> Timestamp:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise DocumentError(f"invalid {field} timestamp: {value}") from error
    else:
        raise DocumentError(f"missing {field} timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    try:
        return Timestamp(parsed)
    except ValueError as error:
        raise DocumentError(f"invalid {field} timestamp: {value}") from error


def _optional_timestamp(value: Any, field: str) -> Timestamp | None:
    return None if value is None else _timestamp(value, field)


def _enum(enum_type, value: Any, field: str):
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise DocumentError(f"invalid {field}: {value}") from error


def _ids(value: Any, field: str) -> tuple[EntityId, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise DocumentError(f"{field} must be a list")
    try:
        return tuple(EntityId(str(item)) for item in value)
    except ValueError as error:
        raise DocumentError(f"invalid {field}") from error


def _comments(value: Any) -> tuple[IssueComment, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise DocumentError("comments must be a list")
    if any(not isinstance(item, dict) for item in value):
        raise DocumentError("every issue comment must be a mapping")
    try:
        return tuple(
            IssueComment(
                id=int(item["id"]),
                author=str(item["author"]),
                body=str(item["body"]),
                created_at=_timestamp(item.get("created_at"), "comment created_at"),
                updated_at=_timestamp(item.get("updated_at"), "comment updated_at"),
                in_reply_to=(
                    int(item["in_reply_to"])
                    if item.get("in_reply_to") is not None
                    else None
                ),
                external_url=item.get("github_url") or item.get("external_url"),
            )
            for item in value
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DocumentError(f"invalid issue comment: {error}") from error


def _history(value: Any) -> tuple[IssueEvent, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise DocumentError("history must be a list")
    if any(not isinstance(item, dict) for item in value):
        raise DocumentError("every issue history entry must be a mapping")
    try:
        return tuple(
            IssueEvent(
                action=str(item["action"]),
                at=_timestamp(item.get("at"), "history at"),
                reason=str(item["reason"]) if item.get("reason") else None,
            )
            for item in value
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DocumentError(f"invalid issue history: {error}") from error


def _base(data: dict[str, Any], fallback_id: str | None = None) -> dict[str, Any]:
    raw_id = data.pop("id", None) or fallback_id
    try:
        identity = EntityId(str(raw_id)) if raw_id is not None else None
    except ValueError as error:
        raise DocumentError(f"invalid id: {raw_id}") from error
    if identity is None:
        raise DocumentError("missing id")
    archived = bool(data.pop("archived", False))
    retention_raw = data.pop("retention", None)
    retention = (
        _enum(RetentionState, retention_raw, "retention")
        if retention_raw is not None
        else RetentionState.ARCHIVED
        if archived
        else RetentionState.VISIBLE
    )
    return {
        "id": identity,
        "created": _timestamp(data.pop("created", None), "created"),
        "updated": _timestamp(data.pop("updated", None), "updated"),
        "retention": retention,
    }


def _parse_issue(data: dict[str, Any], body: str, path: Path) -> Issue:
    base = _base(data)
    raw_status = data.pop("status", "todo")
    if raw_status == "archived":
        base["retention"] = RetentionState.ARCHIVED
        raw_status = "closed"
    raw_type = data.pop("issue_type", "other")
    if raw_type not in {item.value for item in IssueType}:
        raw_type = "other"
    milestone = data.pop("milestone", None)
    relations = IssueRelations(
        milestone_id=EntityId(str(milestone)) if milestone else None,
        depends_on=_ids(data.pop("depends_on", None), "depends_on"),
        blocks=_ids(data.pop("blocks", None), "blocks"),
    )
    try:
        return Issue(
            **base,
            title=Title(str(data.pop("title", ""))),
            headline=str(data.pop("headline", "")),
            content=body,
            priority=_enum(Priority, data.pop("priority", "medium"), "priority"),
            status=_enum(IssueStatus, raw_status, "status"),
            issue_type=IssueType(raw_type),
            relations=relations,
            labels=tuple(str(item) for item in data.pop("labels", [])),
            assignee=data.pop("assignee", None),
            estimated_hours=data.pop("estimated_hours", None),
            due_at=_optional_timestamp(data.pop("due_date", None), "due_date"),
            progress_percentage=data.pop("progress_percentage", None),
            actual_start_at=_optional_timestamp(
                data.pop("actual_start_date", None), "actual_start_date"
            ),
            actual_end_at=_optional_timestamp(
                data.pop("actual_end_date", None), "actual_end_date"
            ),
            git_branches=tuple(str(item) for item in data.pop("git_branches", [])),
            comments=_comments(data.pop("comments", None)),
            history=_history(data.pop("history", None)),
        )
    except (TypeError, ValueError) as error:
        raise DocumentError(f"invalid issue document {path}: {error}") from error


def _parse_milestone(data: dict[str, Any], body: str, path: Path) -> Milestone:
    name_raw = data.pop("name", None) or path.stem
    base = _base(data, str(name_raw))
    project = data.pop("project_id", None)
    try:
        return Milestone(
            **base,
            name=Name(str(name_raw)),
            headline=str(data.pop("headline", "")),
            content=body,
            status=_enum(MilestoneStatus, data.pop("status", "open"), "status"),
            relation=MilestoneRelation(
                project_id=EntityId(str(project)) if project else None
            ),
            due_at=_optional_timestamp(data.pop("due_date", None), "due_date"),
        )
    except (TypeError, ValueError) as error:
        raise DocumentError(f"invalid milestone document {path}: {error}") from error


def _parse_project(data: dict[str, Any], body: str, path: Path) -> Project:
    # 0.1.1 project templates did not persist the ID in frontmatter. Their
    # filename is ``<short-id>-<slug>.md``; retain that read compatibility
    # while new writes always persist the complete canonical ID.
    fallback_id = path.stem.split("-", 1)[0]
    base = _base(data, fallback_id)
    try:
        return Project(
            **base,
            name=Name(str(data.pop("name", ""))),
            headline=str(data.pop("headline", "")),
            content=body,
            status=_enum(ProjectStatus, data.pop("status", "planning"), "status"),
            priority=_enum(Priority, data.pop("priority", "medium"), "priority"),
            relations=ProjectRelations(
                _ids(data.pop("milestones", None), "milestones")
            ),
            owner=data.pop("owner", None),
            estimated_hours=data.pop("estimated_hours", None),
            start_at=_optional_timestamp(data.pop("start_date", None), "start_date"),
            target_end_at=_optional_timestamp(
                data.pop("target_end_date", None), "target_end_date"
            ),
            actual_end_at=_optional_timestamp(
                data.pop("actual_end_date", None), "actual_end_date"
            ),
            actual_hours=data.pop("actual_hours", None),
            repository_url=data.pop("repo_url", data.pop("repository", None)),
        )
    except (TypeError, ValueError) as error:
        raise DocumentError(f"invalid project document {path}: {error}") from error


def parse_document(path: Path, kind: DocumentKind) -> DocumentEnvelope:
    """Parse without rewriting, retaining supported unknown frontmatter and body."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise DocumentError(
            f"cannot read canonical document {path}: {error}"
        ) from error
    match = _FRONTMATTER.match(raw)
    if match is None:
        raise DocumentError(f"missing YAML frontmatter in {path}")
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        raise DocumentError(f"invalid YAML frontmatter in {path}: {error}") from error
    if not isinstance(loaded, dict):
        raise DocumentError(f"frontmatter must be a mapping in {path}")
    data = dict(loaded)
    if "archive" in path.parts and "retention" not in data and "archived" not in data:
        data["archived"] = True
    version = data.pop("schema_version", 0)
    if not isinstance(version, int) or version > 1 or version < 0:
        raise DocumentError(f"unsupported schema_version {version!r} in {path}")
    body = match.group(2)
    if body.startswith("\n"):
        body = body[1:]
    aggregate = {
        "issue": _parse_issue,
        "milestone": _parse_milestone,
        "project": _parse_project,
    }[kind](data, body, path)
    return DocumentEnvelope(kind, aggregate, path, data, version)


def _base_frontmatter(aggregate: Aggregate) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": str(aggregate.id),
        "created": aggregate.created.value.isoformat(),
        "updated": aggregate.updated.value.isoformat(),
        "retention": aggregate.retention.value,
    }


def serialize_document(envelope: DocumentEnvelope) -> bytes:
    """Serialize owned fields over a losslessly retained boundary envelope."""
    aggregate = envelope.aggregate
    data = dict(envelope.extra_frontmatter)
    data.update(_base_frontmatter(aggregate))
    if isinstance(aggregate, Issue):
        data.update(
            title=str(aggregate.title),
            headline=aggregate.headline,
            priority=aggregate.priority.value,
            status=aggregate.status.value,
            issue_type=aggregate.issue_type.value,
            milestone=str(aggregate.relations.milestone_id)
            if aggregate.relations.milestone_id
            else None,
            depends_on=[str(item) for item in aggregate.relations.depends_on],
            blocks=[str(item) for item in aggregate.relations.blocks],
            labels=list(aggregate.labels),
            assignee=aggregate.assignee,
            estimated_hours=aggregate.estimated_hours,
            due_date=aggregate.due_at.value.isoformat() if aggregate.due_at else None,
            progress_percentage=aggregate.progress_percentage,
            actual_start_date=(
                aggregate.actual_start_at.value.isoformat()
                if aggregate.actual_start_at
                else None
            ),
            actual_end_date=(
                aggregate.actual_end_at.value.isoformat()
                if aggregate.actual_end_at
                else None
            ),
            git_branches=list(aggregate.git_branches),
            comments=[
                {
                    "id": comment.id,
                    "issue_id": str(aggregate.id),
                    "author": comment.author,
                    "body": comment.body,
                    "created_at": comment.created_at.value.isoformat(),
                    "updated_at": comment.updated_at.value.isoformat(),
                    "in_reply_to": comment.in_reply_to,
                    # Preserve the released storage key as a bounded compatibility
                    # alias while the domain uses the provider-neutral field name.
                    "github_url": comment.external_url,
                }
                for comment in aggregate.comments
            ],
            history=[
                {
                    "action": event.action,
                    "at": event.at.value.isoformat(),
                    "reason": event.reason,
                }
                for event in aggregate.history
            ],
        )
    elif isinstance(aggregate, Milestone):
        data.update(
            name=str(aggregate.name),
            headline=aggregate.headline,
            status=aggregate.status.value,
            project_id=str(aggregate.relation.project_id)
            if aggregate.relation.project_id
            else None,
            due_date=aggregate.due_at.value.isoformat() if aggregate.due_at else None,
        )
    else:
        data.update(
            name=str(aggregate.name),
            headline=aggregate.headline,
            status=aggregate.status.value,
            priority=aggregate.priority.value,
            milestones=[str(item) for item in aggregate.relations.milestone_ids],
            owner=aggregate.owner,
            estimated_hours=aggregate.estimated_hours,
            start_date=(
                aggregate.start_at.value.isoformat() if aggregate.start_at else None
            ),
            target_end_date=(
                aggregate.target_end_at.value.isoformat()
                if aggregate.target_end_at
                else None
            ),
            actual_end_date=(
                aggregate.actual_end_at.value.isoformat()
                if aggregate.actual_end_at
                else None
            ),
            actual_hours=aggregate.actual_hours,
            repo_url=aggregate.repository_url,
        )
    yaml_text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).rstrip()
    separator = "\n\n" if aggregate.content else "\n"
    return f"---\n{yaml_text}\n---{separator}{aggregate.content}".encode()


class DocumentRepository:
    """Canonical lookup with read compatibility for the 0.1.1 layout."""

    _patterns = {
        "project": ("projects/**/*.md", "archive/projects/**/*.md"),
        "milestone": ("milestones/**/*.md", "archive/milestones/**/*.md"),
        "issue": ("issues/**/*.md", "archive/issues/**/*.md"),
    }

    def __init__(self, roadmap_dir: Path):
        self.roadmap_dir = roadmap_dir

    def scan(self, kind: DocumentKind | None = None) -> list[DocumentEnvelope]:
        found: list[DocumentEnvelope] = []
        identities: set[tuple[DocumentKind, str]] = set()
        kinds = (kind,) if kind else ("project", "milestone", "issue")
        for current_kind in kinds:
            for pattern in self._patterns[current_kind]:
                for path in sorted(self.roadmap_dir.glob(pattern)):
                    envelope = parse_document(path, current_kind)
                    key = (current_kind, envelope.identity)
                    if key in identities:
                        raise DuplicateDocument(
                            f"duplicate {current_kind} id {envelope.identity}"
                        )
                    identities.add(key)
                    found.append(envelope)
        return found

    def load(self, kind: DocumentKind, identity: EntityId) -> DocumentEnvelope | None:
        matches = [item for item in self.scan(kind) if item.aggregate.id == identity]
        return matches[0] if matches else None

    def default_path(self, kind: DocumentKind, aggregate: Aggregate) -> Path:
        return self.roadmap_dir / f"{kind}s" / f"{aggregate.id}.md"
