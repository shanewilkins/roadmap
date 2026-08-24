"""Service for creating projects."""

import uuid

import yaml

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
            project_id = str(uuid.uuid4())
            # Generate or load project content
            if template_path:
                project_content = ProjectTemplateService.load_custom_template(
                    template_path
                )
                if not project_content:
                    project_content = ProjectTemplateService.generate_project_template(
                        project_name,
                        description,
                        template,
                        detected_info,
                        project_id,
                    )
                else:
                    project_content = ProjectCreationService._with_identity(
                        project_content,
                        project_id,
                        project_name,
                        description,
                        detected_info,
                    )
            else:
                project_content = ProjectTemplateService.generate_project_template(
                    project_name, description, template, detected_info, project_id
                )

            # Save project file
            project_filename = f"{project_id}.md"
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
            logger.error(
                "project_creation_failed",
                error=str(e),
                severity="system_error",
            )
            return None

    @staticmethod
    def _with_identity(
        content: str,
        project_id: str,
        project_name: str,
        description: str,
        detected_info: dict,
    ) -> str:
        """Add target schema identity to a valid custom Markdown template."""
        parts = content.split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            generated = ProjectTemplateService.generate_project_template(
                project_name, description, "basic", detected_info, project_id
            )
            generated_parts = generated.split("---", 2)
            return f"---{generated_parts[1]}---\n\n{content}"
        loaded = yaml.safe_load(parts[1])
        if not isinstance(loaded, dict):
            raise ValueError("custom project template frontmatter must be a mapping")
        loaded.update(
            schema_version=1,
            id=project_id,
            retention=loaded.get("retention", "visible"),
        )
        frontmatter = yaml.safe_dump(loaded, sort_keys=False).rstrip()
        return f"---\n{frontmatter}\n---{parts[2]}"
