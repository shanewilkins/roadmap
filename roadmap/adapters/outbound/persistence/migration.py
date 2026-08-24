"""Narrow filesystem adapter for the 0.1.1-to-0.2 workspace migration."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from roadmap.application.contracts import (
    MigrationChange,
    MigrationPlan,
    MigrationResult,
)

from .canonical import CanonicalUnitOfWork
from .documents import (
    DocumentEnvelope,
    DocumentError,
    DocumentKind,
    DocumentRepository,
    parse_document,
    serialize_document,
)
from .projection import SQLiteProjection

WORKSPACE_SCHEMA_VERSION = 1
DOCUMENT_SCHEMA_VERSION = 1


class MigrationError(RuntimeError):
    """The workspace cannot be migrated without user intervention."""


@dataclass(frozen=True, slots=True)
class _DocumentMove:
    envelope: DocumentEnvelope
    source: Path
    target: Path
    content: bytes
    duplicates: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class _Prepared:
    plan: MigrationPlan
    moves: tuple[_DocumentMove, ...]
    project_config: bytes | None
    user_config: bytes | None


def _yaml_bytes(data: dict[str, Any]) -> bytes:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).encode("utf-8")


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def _validate_legacy_config(data: dict[str, Any]) -> tuple[str, ...]:
    conflicts: list[str] = []
    behavior = _section(data, "behavior")
    display = _section(data, "display")
    output = _section(data, "output")
    for key in (
        "auto_branch_on_start",
        "confirm_destructive",
        "show_tips",
        "include_closed_in_critical_path",
    ):
        value = behavior.get(key)
        if value is not None and not isinstance(value, bool):
            conflicts.append(f"configuration key behavior.{key} must be a boolean")
    default_project = behavior.get("default_project_id")
    if default_project is not None and not isinstance(default_project, str):
        conflicts.append(
            "configuration key behavior.default_project_id must be text or null"
        )
    width = display.get("table_width")
    if width is not None and (
        not isinstance(width, int) or isinstance(width, bool) or width < 20
    ):
        conflicts.append("configuration key display.table_width must be >= 20")
    columns = output.get("columns")
    if columns is not None and (
        not isinstance(columns, list)
        or any(not isinstance(item, str) for item in columns)
    ):
        conflicts.append("configuration key output.columns must be a list of text")
    return tuple(conflicts)


def _mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise MigrationError(
            f"cannot read configuration {path.name}: {error}"
        ) from error
    if not isinstance(loaded, dict):
        raise MigrationError(f"configuration {path.name} must be a mapping")
    return dict(loaded)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class FilesystemWorkspaceMigration:
    """Perform only the concrete schema-zero to schema-one migration."""

    _patterns: dict[DocumentKind, tuple[str, ...]] = {
        "project": ("projects/**/*.md", "archive/projects/**/*.md"),
        "milestone": ("milestones/**/*.md", "archive/milestones/**/*.md"),
        "issue": ("issues/**/*.md", "archive/issues/**/*.md"),
    }

    def __init__(
        self,
        roadmap_dir: Path,
        projection: SQLiteProjection,
        user_config_path: Path,
        *,
        failure_injector: Callable[[str, Path | None], None] | None = None,
    ):
        self.roadmap_dir = roadmap_dir
        self.project_config_path = roadmap_dir / "config.yaml"
        self.user_config_path = user_config_path
        self.repository = DocumentRepository(roadmap_dir)
        self.projection = projection
        self._inject = failure_injector or (lambda _stage, _path: None)

    def preflight(self) -> MigrationPlan:
        return self._prepare().plan

    def execute(self, fingerprint: str) -> MigrationResult:
        prepared = self._prepare()
        plan = prepared.plan
        if plan.fingerprint != fingerprint:
            raise MigrationError(
                "workspace changed after migration preflight; run the dry-run again"
            )
        if plan.conflicts:
            raise MigrationError("; ".join(plan.conflicts))
        if not plan.required:
            return MigrationResult(
                plan.source_version,
                plan.target_version,
                0,
                False,
                already_current=True,
            )

        if prepared.user_config is not None:
            self._inject("before_user_config", self.user_config_path)
            _atomic_write(self.user_config_path, prepared.user_config)
        self._inject("before_transaction", None)
        with CanonicalUnitOfWork(
            self.repository, failure_injector=self._inject
        ) as unit:
            for move in prepared.moves:
                target = str(move.target.relative_to(self.roadmap_dir))
                unit.stage_file(target, move.content)
                for source in (move.source, *move.duplicates):
                    if source != move.target:
                        unit.stage_delete(str(source.relative_to(self.roadmap_dir)))
            if prepared.project_config is not None:
                unit.stage_file("config.yaml", prepared.project_config, final=True)
            unit.commit()

        self._inject("after_canonical_commit", None)
        self._inject("before_projection_rebuild", self.projection.path)
        self.projection.rebuild()
        return MigrationResult(
            plan.source_version,
            plan.target_version,
            len(plan.changes),
            True,
        )

    def _prepare(self) -> _Prepared:
        conflicts: list[str] = []
        warnings: list[str] = []
        legacy_config, source_version = self._source_config(conflicts)

        moves = self._document_moves(conflicts)
        if source_version == WORKSPACE_SCHEMA_VERSION:
            unexpected = [
                str(move.source.relative_to(self.roadmap_dir))
                for move in moves
                if move.source != move.target
                or move.envelope.schema_version != DOCUMENT_SCHEMA_VERSION
            ]
            if unexpected:
                conflicts.append(
                    "current workspace schema contains legacy canonical paths: "
                    + ", ".join(unexpected)
                )
            moves = []

        project_config = None
        user_config = None
        changes: list[MigrationChange] = []
        if source_version < WORKSPACE_SCHEMA_VERSION and not conflicts:
            for move in moves:
                source = str(move.source.relative_to(self.roadmap_dir))
                target = str(move.target.relative_to(self.roadmap_dir))
                operation = "rewrite" if move.source == move.target else "move"
                changes.append(
                    MigrationChange(
                        operation,
                        source,
                        target,
                        move.envelope.kind,
                        move.envelope.identity,
                    )
                )
                changes.extend(
                    MigrationChange(
                        "delete-duplicate",
                        str(path.relative_to(self.roadmap_dir)),
                        target,
                        move.envelope.kind,
                        move.envelope.identity,
                    )
                    for path in move.duplicates
                    if path != move.target
                )
            project_config = self._project_config(legacy_config)
            user_config = self._user_config(legacy_config, conflicts)
            changes.append(MigrationChange("rewrite", "config.yaml", "config.yaml"))
            if user_config is not None:
                changes.append(
                    MigrationChange("merge", "config.yaml", "<user-config>/config.yaml")
                )
            changes.append(MigrationChange("rebuild", None, "db/projection.db"))
            if any(key in legacy_config for key in ("github", "git", "paths")):
                warnings.append(
                    "provider, Git transport, secret, and machine-path settings are "
                    "not copied into the 0.2 project configuration"
                )
        elif (
            source_version == WORKSPACE_SCHEMA_VERSION
            and not conflicts
            and (self.projection.path.exists() or self.projection.stale_path.exists())
            and self.projection.needs_rebuild()
        ):
            changes.append(MigrationChange("rebuild", None, "db/projection.db"))

        fingerprint = self._fingerprint()
        return _Prepared(
            MigrationPlan(
                source_version,
                WORKSPACE_SCHEMA_VERSION,
                fingerprint,
                tuple(changes),
                tuple(conflicts),
                tuple(warnings),
            ),
            tuple(moves),
            project_config,
            user_config,
        )

    def _source_config(self, conflicts: list[str]) -> tuple[dict[str, Any], int]:
        try:
            legacy_config = _mapping(self.project_config_path)
        except MigrationError as error:
            legacy_config = {}
            conflicts.append(str(error))
        source_version = legacy_config.get("workspace_schema_version", 0)
        if (
            not isinstance(source_version, int)
            or isinstance(source_version, bool)
            or source_version < 0
        ):
            conflicts.append("workspace_schema_version must be a non-negative integer")
            source_version = 0
        if source_version > WORKSPACE_SCHEMA_VERSION:
            conflicts.append(
                f"workspace schema {source_version} is newer than supported schema "
                f"{WORKSPACE_SCHEMA_VERSION}"
            )
        conflicts.extend(_validate_legacy_config(legacy_config))
        return legacy_config, source_version

    def _document_moves(self, conflicts: list[str]) -> list[_DocumentMove]:
        grouped: dict[tuple[DocumentKind, str], list[DocumentEnvelope]] = defaultdict(
            list
        )
        paths: set[Path] = set()
        for kind, patterns in self._patterns.items():
            for pattern in patterns:
                for path in sorted(self.roadmap_dir.glob(pattern)):
                    if path in paths:
                        continue
                    paths.add(path)
                    if path.is_symlink() or not path.resolve().is_relative_to(
                        self.roadmap_dir.resolve()
                    ):
                        conflicts.append(f"canonical path escapes workspace: {path}")
                        continue
                    try:
                        envelope = parse_document(path, kind)
                        grouped[(kind, envelope.identity)].append(envelope)
                    except DocumentError as error:
                        conflicts.append(str(error))

        moves: list[_DocumentMove] = []
        claimed: dict[str, tuple[DocumentKind, str]] = {}
        for key, envelopes in sorted(grouped.items(), key=lambda item: item[0]):
            kind, identity = key
            target = self.roadmap_dir / f"{kind}s" / f"{identity}.md"
            case_key = str(target.relative_to(self.roadmap_dir)).casefold()
            if case_key in claimed and claimed[case_key] != key:
                conflicts.append(f"case-insensitive target collision for {target.name}")
                continue
            claimed[case_key] = key
            rendered = [
                serialize_document(
                    replace(item, path=target, schema_version=DOCUMENT_SCHEMA_VERSION)
                )
                for item in envelopes
            ]
            if any(content != rendered[0] for content in rendered[1:]):
                conflicts.append(f"non-identical duplicate {kind} id {identity}")
                continue
            preferred_index = next(
                (index for index, item in enumerate(envelopes) if item.path == target),
                0,
            )
            preferred = envelopes[preferred_index]
            duplicates = tuple(
                item.path
                for index, item in enumerate(envelopes)
                if index != preferred_index
            )
            moves.append(
                _DocumentMove(
                    preferred,
                    preferred.path,
                    target,
                    rendered[preferred_index],
                    duplicates,
                )
            )
        return moves

    @staticmethod
    def _project_config(legacy: dict[str, Any]) -> bytes:
        behavior = legacy.get("behavior")
        behavior = behavior if isinstance(behavior, dict) else {}
        return _yaml_bytes(
            {
                "schema_version": 1,
                "workspace_schema_version": WORKSPACE_SCHEMA_VERSION,
                "behavior": {
                    "default_project_id": behavior.get("default_project_id"),
                    "include_closed_in_critical_path": bool(
                        behavior.get("include_closed_in_critical_path", False)
                    ),
                },
            }
        )

    def _user_config(
        self, legacy: dict[str, Any], conflicts: list[str]
    ) -> bytes | None:
        try:
            existing = _mapping(self.user_config_path)
        except MigrationError as error:
            conflicts.append(str(error))
            return None
        version = existing.get("schema_version", 1)
        if not isinstance(version, int) or version > 1 or version < 0:
            conflicts.append("user configuration has an unsupported schema version")
            return None
        user = _section(legacy, "user")
        display = _section(legacy, "display")
        behavior = _section(legacy, "behavior")
        output = _section(legacy, "output")
        export = _section(legacy, "export")
        migrated = {
            "schema_version": 1,
            "identity": {
                "name": user.get("name"),
                "email": user.get("email"),
            },
            "display": {
                "default_milestone": display.get("default_milestone"),
                "table_width": display.get("table_width", 100),
            },
            "behavior": {
                "auto_branch_on_start": bool(
                    behavior.get("auto_branch_on_start", False)
                ),
                "confirm_destructive": bool(behavior.get("confirm_destructive", True)),
                "show_tips": bool(behavior.get("show_tips", True)),
            },
            "output": {
                "format": output.get("format", "rich"),
                "columns": output.get("columns", []),
                "sort_by": output.get("sort_by", ""),
            },
            "export": {
                "directory": export.get("directory", ".roadmap/exports"),
                "format": export.get("format", "json"),
                "include_metadata": bool(export.get("include_metadata", True)),
                "auto_gitignore": bool(export.get("auto_gitignore", True)),
            },
        }
        merged = dict(existing)
        for key, value in migrated.items():
            if key == "schema_version":
                merged[key] = value
                continue
            current = merged.get(key)
            merged[key] = {**value, **current} if isinstance(current, dict) else value
        return _yaml_bytes(merged)

    def _fingerprint(self) -> str:
        digest = hashlib.sha256()
        candidates = [self.project_config_path]
        for patterns in self._patterns.values():
            for pattern in patterns:
                candidates.extend(self.roadmap_dir.glob(pattern))
        if self.user_config_path.exists():
            candidates.append(self.user_config_path)
        for path in sorted(set(candidates), key=lambda item: str(item)):
            digest.update(str(path).encode("utf-8"))
            if path.exists() and path.is_file():
                digest.update(path.read_bytes())
        return digest.hexdigest()
