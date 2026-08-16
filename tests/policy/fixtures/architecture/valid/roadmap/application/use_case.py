"""Valid inward Application dependencies."""

from roadmap.application.dto import Request
from roadmap.domain.value import WorkId


def execute(request: Request) -> WorkId:
    """Map a fixture request to a Domain value."""
    return WorkId(request.work_id)
