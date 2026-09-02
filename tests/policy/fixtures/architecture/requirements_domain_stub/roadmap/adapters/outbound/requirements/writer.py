"""Stub outbound persistence adapter for the planned Requirements entity (TR-045 fixture)."""

import yaml
from roadmap.application.requirements import CreateRequirementRequest


def dump(request: CreateRequirementRequest) -> str:
    """Serialize a fixture requirement request."""
    return yaml.safe_dump({"id": request.id_value})
