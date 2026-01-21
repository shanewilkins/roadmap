"""Project Initialization Service - Backward Compatibility Facade.

DEPRECATED: This module is maintained for backward compatibility.
Use roadmap.core.services.project_init package instead.

New structure:
- roadmap.core.services.project_init.detection - ProjectDetectionService
- roadmap.core.services.project_init.context_detection - ProjectContextDetectionService
- roadmap.core.services.project_init.template - ProjectTemplateService
- roadmap.core.services.project_init.creation - ProjectCreationService
"""

from roadmap.adapters.persistence.parser import ProjectParser
from roadmap.core.services.project_init import (
    ProjectContextDetectionService,
    ProjectCreationService,
    ProjectDetectionService,
    ProjectTemplateService,
)
from roadmap.infrastructure.coordination.core import RoadmapCore

__all__ = [
    "ProjectDetectionService",
    "ProjectContextDetectionService",
    "ProjectTemplateService",
    "ProjectCreationService",
    "ProjectParser",
    "RoadmapCore",
]
