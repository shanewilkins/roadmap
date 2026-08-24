"""Canonical workspace initialization."""

from roadmap.application.contracts import (
    ProjectCreateCommand,
    WorkspaceInitializationRequest,
    WorkspaceInitializationResult,
)
from roadmap.application.ports import WorkspaceLayoutPort

from .planning import Planning


class WorkspaceInitialization:
    """Establish the local layout and optional first canonical project."""

    def __init__(self, layout: WorkspaceLayoutPort, planning: Planning):
        self._layout = layout
        self._planning = planning

    def execute(
        self, request: WorkspaceInitializationRequest
    ) -> WorkspaceInitializationResult:
        existed = self._layout.is_initialized()
        if request.dry_run:
            return WorkspaceInitializationResult(not existed, dry_run=True)
        self._layout.prepare()
        project = None
        if not request.skip_project and not self._planning.all_projects():
            if request.project_name is None:
                raise ValueError("project_name is required when creating a project")
            project = self._planning.create_project(
                ProjectCreateCommand(request.project_name, request.description)
            ).aggregate
        return WorkspaceInitializationResult(not existed, project)
