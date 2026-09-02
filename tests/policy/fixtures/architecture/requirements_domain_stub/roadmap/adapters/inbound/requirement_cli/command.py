"""Stub inbound adapter for the planned Requirements entity (TR-045 fixture).

Deliberately a new adapter boundary (not nested under the existing cli
boundary) to prove a brand-new adapter package needs no architecture.toml
registration.
"""

import click
from roadmap.application.requirements import CreateRequirementRequest


def create(id_value: str) -> CreateRequirementRequest:
    """Translate fixture CLI input into an Application request."""
    click.echo(f"creating requirement {id_value}")
    return CreateRequirementRequest(id_value)
