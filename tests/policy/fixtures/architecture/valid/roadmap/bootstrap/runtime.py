"""Valid composition-root wiring."""

from roadmap.adapters.inbound.cli.command import request
from roadmap.adapters.outbound.documents.writer import dump


def run(value: str) -> str:
    """Wire fixture adapters."""
    return dump(request(value))
