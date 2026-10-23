"""Optional requirement capture and identity operations over canonical ports."""

from dataclasses import dataclass, replace

from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.ports import (
    Clock,
    CurrentIdentity,
    RequirementUnitOfWorkFactory,
)
from roadmap.domain.requirement_governance import EvidenceResult
from roadmap.domain.requirements import (
    Requirement,
    RequirementCriterion,
    RequirementDefinition,
    RequirementKey,
    RequirementKind,
    RequirementStatus,
)
from roadmap.domain.types import EntityId, Priority, RequiredText


def invalid(message: str) -> ApplicationFailure:
    return ApplicationFailure(FailureCategory.INVALID_REQUEST, message)


_METADATA = {"rationale", "priority", "owner", "journey", "stage"}


def _check_fields(fields, allowed: set[str]) -> None:
    unexpected = set(fields) - allowed
    if unexpected:
        raise invalid(f"Unsupported requirement fields: {sorted(unexpected)}")


def criteria(values: tuple[str, ...]) -> tuple[RequirementCriterion, ...]:
    result = []
    for value in values:
        identity, separator, text = value.partition("=")
        if not separator:
            raise invalid("Criteria must be ID=TEXT")
        result.append(RequirementCriterion(identity, text))
    return tuple(result)


def unique(records: tuple[Requirement, ...]) -> None:
    aliases: dict[str, list[str]] = {}
    for item in records:
        aliases.setdefault(str(item.key), []).append(str(item.id))
    collisions = [
        f"{key}: {', '.join(sorted(identities))}"
        for key, identities in sorted(aliases.items())
        if len(identities) > 1
    ]
    if collisions:
        raise invalid(
            "Requirement alias collision; inspect and rekey by full UUID: "
            + "; ".join(collisions)
        )


def select(records: tuple[Requirement, ...], selector: str) -> Requirement:
    by_id = [item for item in records if str(item.id) == selector]
    if by_id:
        return by_id[0]
    unique(records)
    found = [item for item in records if item.key == selector]
    if not found:
        raise ApplicationFailure(
            FailureCategory.NOT_FOUND, f"Requirement not found: {selector}"
        )
    return found[0]


def _sort_key(item: Requirement, sort: str):
    if sort == "title":
        value = str(item.definition.title).casefold()
    elif sort == "key":
        value = (str(item.key)[:2], int(str(item.key)[3:]))
    elif sort == "priority":
        value = list(Priority).index(item.priority)
    else:
        value = getattr(item, sort)
    return value, str(item.id)


@dataclass(frozen=True)
class RequirementMutationResult:
    requirement: Requirement
    projection_stale: bool = False


@dataclass(frozen=True)
class RequirementAdoptionResult:
    enabled: bool
    apply: bool
    changes: tuple[str, ...]
    projection_stale: bool = False


class Requirements:
    def __init__(
        self,
        units: RequirementUnitOfWorkFactory,
        clock: Clock,
        identity: CurrentIdentity,
    ):
        self._units, self._clock, self._identity = units, clock, identity

    def enable(self, *, apply: bool = False) -> RequirementAdoptionResult:
        with self._units.create(read_only=not apply) as unit:
            enabled = unit.enable_requirements(apply=apply)
            if apply and not enabled:
                unit.commit()
            return RequirementAdoptionResult(
                enabled or apply,
                apply,
                ()
                if enabled
                else (
                    "Upgrade project configuration/workspace to version 2; older versions refuse",
                ),
                unit.projection_stale,
            )

    @staticmethod
    def _require_enabled(unit) -> None:
        if not unit.enable_requirements():
            raise invalid(
                "Enable requirements explicitly: roadmap requirement enable --apply"
            )

    def list(
        self,
        *,
        filters: dict[str, str] | None = None,
        search: str = "",
        sort: str = "key",
    ) -> tuple[Requirement, ...]:
        with self._units.create(read_only=True) as unit:
            records = unit.list_requirements()
            unique(records)
        for name, value in (filters or {}).items():
            records = tuple(
                item for item in records if str(self._filter_value(item, name)) == value
            )
        term = search.casefold()
        records = tuple(
            item
            for item in records
            if term
            in "\n".join(
                (
                    str(item.key),
                    str(item.definition.title),
                    item.content,
                    item.rationale,
                )
            ).casefold()
        )
        if sort not in {"key", "title", "priority", "created", "updated"}:
            raise invalid("Unsupported requirement sort")
        return tuple(sorted(records, key=lambda item: _sort_key(item, sort)))

    @staticmethod
    def _filter_value(item: Requirement, name: str):
        if name == "type":
            return item.definition.kind
        if name == "status":
            return item.effective_status
        if name not in _METADATA | {"key"}:
            raise invalid("Unsupported requirement filter")
        return getattr(item, name)

    def view(self, selector: str) -> Requirement:
        with self._units.create(read_only=True) as unit:
            return select(unit.list_requirements(), selector)

    def create(
        self,
        *,
        kind: str,
        title: str,
        statement: str,
        criterion_values: tuple[str, ...],
        key: str | None = None,
        **metadata,
    ) -> RequirementMutationResult:
        _check_fields(metadata, _METADATA | {"scope"})
        definition = RequirementDefinition(
            RequirementKind(kind),
            RequiredText(title),
            statement,
            criteria(criterion_values),
            metadata.pop("scope", ""),
        )
        with self._units.create() as unit:
            self._require_enabled(unit)
            records = unit.list_requirements()
            unique(records)
            if key is None:
                number = (
                    max(
                        (
                            int(str(x.key)[3:])
                            for x in records
                            if x.definition.kind == definition.kind
                        ),
                        default=0,
                    )
                    + 1
                )
                key = f"{definition.kind.prefix}-{number:03d}"
            alias = RequirementKey(key)
            if any(item.key == alias for item in records):
                raise invalid(f"Requirement key already exists: {alias}")
            now = self._clock.now()
            value = Requirement(EntityId.new(), now, now, alias, definition, **metadata)
            value = value.record("created", now, self._actor())
            unit.save_requirement(value)
            unit.commit()
            return RequirementMutationResult(value, unit.projection_stale)

    def _actor(self) -> str:
        return self._identity.current_identity() or "unconfigured local user"

    def update(
        self, selector: str, *, expected_revision: str | None = None, **changes
    ) -> RequirementMutationResult:
        _check_fields(changes, _METADATA | {"title", "statement", "scope", "criteria"})
        with self._units.create() as unit:
            self._require_enabled(unit)
            records = unit.list_requirements()
            unique(records)
            value = select(records, selector)
            if (
                expected_revision is not None
                and expected_revision != value.current_revision
            ):
                raise invalid(
                    "Requirement intent changed; inspect current revision before retry"
                )
            now, actor = self._clock.now(), self._actor()
            original_value = value
            if value.uncaptured_intent:
                value = value.record("manual-intent-captured", now, actor)
            value = value.withdraw_stale_acceptance(now, actor)
            definition_changes = {
                name: changes.pop(name)
                for name in ("title", "statement", "scope", "criteria")
                if name in changes
            }
            definition = replace(value.definition, **definition_changes)
            changed = replace(value, definition=definition, **changes)
            if changed == original_value:
                return RequirementMutationResult(value)
            changed = changed.record(
                "updated",
                now,
                actor,
                "Changed fields: "
                + ", ".join(sorted(set(changes) | set(definition_changes))),
            )
            changed = changed.withdraw_stale_acceptance(now, actor)
            unit.save_requirement(changed)
            unit.commit()
            return RequirementMutationResult(changed, unit.projection_stale)

    def rekey(self, identity: str, key: str) -> RequirementMutationResult:
        with self._units.create() as unit:
            self._require_enabled(unit)
            records = unit.list_requirements()
            found = [x for x in records if str(x.id) == identity]
            if not found:
                raise invalid("Rekey requires an exact full requirement UUID")
            alias = RequirementKey(key)
            if any(x.key == alias and str(x.id) != identity for x in records):
                raise invalid("Destination requirement alias is already occupied")
            if (
                found[0].key == alias
                and not found[0].uncaptured_intent
                and found[0].effective_status == found[0].status
            ):
                return RequirementMutationResult(found[0])
            now, actor = self._clock.now(), self._actor()
            value = (
                found[0].withdraw_stale_acceptance(now, actor).rekey(alias, now, actor)
            )
            unit.save_requirement(value)
            unit.commit()
            return RequirementMutationResult(value, unit.projection_stale)

    def _reviewed(self, unit, selector: str, expected_revision: str) -> Requirement:
        self._require_enabled(unit)
        records = unit.list_requirements()
        unique(records)
        value = select(records, selector)
        if expected_revision != value.current_revision:
            raise invalid(
                "Requirement intent changed; inspect current revision before retry"
            )
        return value

    def transition(
        self, selector: str, *, status: str, expected_revision: str, reason: str
    ) -> RequirementMutationResult:
        with self._units.create() as unit:
            value = self._reviewed(unit, selector, expected_revision)
            changed = value.transition(
                RequirementStatus(status), self._clock.now(), self._actor(), reason
            )
            unit.save_requirement(changed)
            unit.commit()
            return RequirementMutationResult(changed, unit.projection_stale)

    def record_evidence(
        self,
        selector: str,
        *,
        criterion: str,
        result: str,
        reference: str,
        acceptance_id: str,
        expected_revision: str,
        note: str = "",
    ) -> RequirementMutationResult:
        with self._units.create() as unit:
            value = self._reviewed(unit, selector, expected_revision)
            if acceptance_id != value.active_acceptance_id:
                raise invalid(
                    "Requirement acceptance changed; inspect the active acceptance before retry"
                )
            changed = value.add_evidence(
                criterion,
                EvidenceResult(result),
                reference,
                self._clock.now(),
                self._actor(),
                note,
            )
            unit.save_requirement(changed)
            unit.commit()
            return RequirementMutationResult(changed, unit.projection_stale)
