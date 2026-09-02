"""Stub composition-root wiring for the planned Requirements entity (TR-045 fixture)."""

from roadmap.adapters.inbound.requirement_cli.command import create
from roadmap.adapters.outbound.requirements.writer import dump


def run(id_value: str) -> str:
    """Wire fixture Requirements adapters."""
    return dump(create(id_value))
