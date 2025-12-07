"""Project initialization services package.

Provides modularized services for:
- Detecting existing projects
- Detecting project context from git and filesystem
- Generating project templates
- Creating new projects
"""

from roadmap.core.services.project_init.context_detection import (
    ProjectContextDetectionService,
)
from roadmap.core.services.project_init.creation import ProjectCreationService
from roadmap.core.services.project_init.detection import ProjectDetectionService
from roadmap.core.services.project_init.template import ProjectTemplateService

__all__ = [
    "ProjectDetectionService",
    "ProjectContextDetectionService",
    "ProjectTemplateService",
    "ProjectCreationService",
]
