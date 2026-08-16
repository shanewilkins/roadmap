"""Valid outbound adapter dependencies."""

import yaml
from roadmap.application.dto import Request


def dump(request: Request) -> str:
    """Serialize a fixture request."""
    return yaml.safe_dump({"work_id": request.work_id})
