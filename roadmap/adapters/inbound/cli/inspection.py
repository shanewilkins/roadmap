"""Versioned, lossless JSON inspection of application query results."""

import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import click

from roadmap.domain.types import Timestamp


def _value(value: Any) -> Any:
    if isinstance(value, Timestamp):
        return value.value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _value(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, (tuple, list)):
        return [_value(item) for item in value]
    return value


def inspect_json(kind: str, record: Any, **extra: Any) -> None:
    click.echo(
        json.dumps(
            {
                "schema_version": 1,
                "kind": f"roadmap.{kind}",
                "record": _value(record),
                **{key: _value(value) for key, value in extra.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )
