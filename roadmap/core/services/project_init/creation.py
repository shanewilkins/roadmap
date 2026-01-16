"""Service for creating projects."""

import uuid

from roadmap.common.logging import get_logger
from roadmap.core.services.project_init.template import ProjectTemplateService
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger(__name__)


class ProjectCreationService:
    """Service for creating projects."""

    @staticmethod
    def create_project(
        core: RoadmapCore,
        project_name: str,
        description: str,
        detected_info: dict,
        template: str,
        template_path: str | None = None,
    ) -> dict | None:
        """Create a new project with given parameters.

        Args:
            core: RoadmapCore instance
            project_name: Name of the project
            description: Project description
            detected_info: Detected project context
            template: Template type to use
            template_path: Optional path to custom template

        Returns:
            Dictionary with project info (id, name, filename) or None if failed
        """
        try:
            # Generate or load project content
            if template_path:
                project_content = ProjectTemplateService.load_custom_template(
                    template_path
                )
                if not project_content:
                    project_content = ProjectTemplateService.generate_project_template(
                        project_name, description, template, detected_info
                    )
            else:
                project_content = ProjectTemplateService.generate_project_template(
                    project_name, description, template, detected_info
                )

            # Save project file
            project_id = str(uuid.uuid4())[:8]
            project_filename = (
                f"{project_id}-{project_name.lower().replace(' ', '-')}.md"
            )
            project_file = core.roadmap_dir / "projects" / project_filename

            # Ensure projects directory exists
            (core.roadmap_dir / "projects").mkdir(parents=True, exist_ok=True)

            project_file.write_text(project_content)

            return {
                "id": project_id,
                "name": project_name,
                "filename": project_filename,
            }

        except Exception as e:
            logger.error("project_creation_failed", error=str(e))
            return None
