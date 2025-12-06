"""
Service layer for project initialization logic.

Handles all business logic related to:
- Creating new projects
- Detecting existing projects
- Generating project templates
- Parsing project context from git and file system
"""

import getpass
import re
import subprocess
from datetime import datetime
from pathlib import Path

from roadmap.adapters.persistence.parser import ProjectParser
from roadmap.common.logging import get_logger
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger(__name__)


class ProjectDetectionService:
    """Service for detecting and analyzing existing projects."""

    @staticmethod
    def detect_existing_projects(projects_dir: Path) -> list[dict]:
        """Detect existing projects in the projects directory.

        Args:
            projects_dir: Path to the projects directory

        Returns:
            List of dicts with 'name', 'id', and 'file' for each existing project
        """
        existing_projects = []

        if not projects_dir.exists():
            return existing_projects

        for project_file in projects_dir.glob("*.md"):
            try:
                project = ProjectParser.parse_project_file(project_file)
                existing_projects.append(
                    {
                        "name": project.name,
                        "id": project.id,
                        "file": project_file.name,
                    }
                )
            except Exception:
                # Skip projects that can't be parsed
                continue

        return existing_projects


class ProjectContextDetectionService:
    """Service for detecting project context from git and file system."""

    @staticmethod
    def detect_project_context() -> dict:
        """Detect project context from git repository and directory structure.

        Returns:
            Dictionary with detected context:
            - git_repo: Repository in owner/repo format if detected
            - project_name: Project name from git, package files, or directory
            - git_user: Git user name if available
            - has_git: Whether in a git repository
        """
        context = {
            "git_repo": None,
            "project_name": None,
            "git_user": None,
            "has_git": False,
        }

        try:
            # Check if we're in a git repository
            git_check = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            context["has_git"] = git_check.returncode == 0

            if context["has_git"]:
                ProjectContextDetectionService._detect_git_repo(context)
                ProjectContextDetectionService._detect_git_user(context)

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass

        # Fallback to directory name if no git repo detected
        if not context["project_name"]:
            context["project_name"] = Path.cwd().name

        # Try to detect from package files
        if not context["project_name"] or context["project_name"] == ".":
            ProjectContextDetectionService._detect_from_package_files(context)

        return context

    @staticmethod
    def _detect_git_repo(context: dict) -> None:
        """Detect git repository and populate context."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                origin_url = result.stdout.strip()
                # Parse GitHub repository from URL
                if "github.com" in origin_url:
                    # Handle both SSH and HTTPS URLs
                    if origin_url.startswith("git@github.com:"):
                        repo_part = origin_url.replace("git@github.com:", "").replace(
                            ".git", ""
                        )
                    elif "github.com/" in origin_url:
                        repo_part = origin_url.split("github.com/")[1].replace(
                            ".git", ""
                        )
                    else:
                        repo_part = None

                    if repo_part and "/" in repo_part:
                        context["git_repo"] = repo_part
                        context["project_name"] = repo_part.split("/")[1]
        except Exception:
            pass

    @staticmethod
    def _detect_git_user(context: dict) -> None:
        """Detect git user name and populate context."""
        try:
            user_result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if user_result.returncode == 0:
                context["git_user"] = user_result.stdout.strip()
        except Exception:
            pass

    @staticmethod
    def _detect_from_package_files(context: dict) -> None:
        """Try to detect project name from package files."""
        import json

        for config_file in ["pyproject.toml", "package.json", "Cargo.toml"]:
            if Path(config_file).exists():
                try:
                    content = Path(config_file).read_text()
                    if config_file == "pyproject.toml":
                        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            context["project_name"] = match.group(1)
                            break
                    elif config_file == "package.json":
                        data = json.loads(content)
                        if "name" in data:
                            context["project_name"] = data["name"]
                            break
                except Exception:
                    pass


class ProjectTemplateService:
    """Service for generating project templates."""

    # Template snippets for different types
    SOFTWARE_TEMPLATE = """
- [ ] Develop core functionality
- [ ] Implement user interface
- [ ] Write comprehensive tests
- [ ] Deploy to production
- [ ] Document API and usage

## Technical Stack

- **Language**: Python
- **Framework**: TBD
- **Database**: TBD
- **Deployment**: TBD

## Development Phases

### Phase 1: Foundation
- Project setup and architecture
- Core functionality implementation
- Basic testing framework

### Phase 2: Features
- Feature development
- User interface implementation
- Integration testing

### Phase 3: Polish
- Performance optimization
- Documentation
- Production deployment
"""

    RESEARCH_TEMPLATE = """
- [ ] Literature review
- [ ] Hypothesis formation
- [ ] Methodology design
- [ ] Data collection
- [ ] Analysis and findings
- [ ] Publication preparation

## Research Questions

1. [Primary research question]
2. [Secondary research questions]

## Methodology

[Research methodology and approach]

## Timeline

- **Phase 1**: Literature review (4 weeks)
- **Phase 2**: Data collection (8 weeks)
- **Phase 3**: Analysis (4 weeks)
- **Phase 4**: Writing (4 weeks)
"""

    TEAM_TEMPLATE = """
- [ ] Team onboarding
- [ ] Process documentation
- [ ] Workflow optimization
- [ ] Knowledge sharing
- [ ] Regular retrospectives

## Team Structure

- **Project Lead**: [Name]
- **Development Team**: [Names]
- **Stakeholders**: [Names]

## Communication

- **Daily Standups**: [Time/Location]
- **Sprint Planning**: [Schedule]
- **Retrospectives**: [Schedule]

## Processes

### Development Workflow
1. Issue creation and planning
2. Feature branch development
3. Code review process
4. Testing and validation
5. Deployment and monitoring
"""

    BASIC_TEMPLATE = """
- [ ] Define project scope
- [ ] Create initial roadmap
- [ ] Begin implementation
- [ ] Regular progress reviews
- [ ] Project completion

## Milestones

### Milestone 1: Setup
- Initial project structure
- Team alignment on goals

### Milestone 2: Development
- Core functionality implementation
- Regular progress tracking

### Milestone 3: Completion
- Final deliverables
- Project retrospective
"""

    TEMPLATE_FOOTER = """

## Resources

- [Link to documentation]
- [Link to repository]
- [Link to project tools]

## Notes

[Additional project notes and context]
"""

    @staticmethod
    def generate_project_template(
        project_name: str, description: str, template: str, detected_info: dict
    ) -> str:
        """Generate project content based on template.

        Args:
            project_name: Name of the project
            description: Project description
            template: Template type (basic, software, research, team)
            detected_info: Detected project context

        Returns:
            Project content as markdown string
        """
        current_date = datetime.now().isoformat()
        owner = detected_info.get("git_user", getpass.getuser())

        # Base project content
        content = f"""---
name: {project_name}
description: {description}
owner: {owner}
priority: high
status: active
created: {current_date}
updated: {current_date}
"""

        if detected_info.get("git_repo"):
            content += f"github_repo: {detected_info['git_repo']}\n"

        content += (
            """timeline:
  start_date: """
            + current_date
            + """
  target_end_date: null
tags: []
---

# """
            + project_name
            + """

## Overview

"""
            + description
            + """

## Project Goals

"""
        )

        # Template-specific content
        if template == "software":
            content += ProjectTemplateService.SOFTWARE_TEMPLATE
        elif template == "research":
            content += ProjectTemplateService.RESEARCH_TEMPLATE
        elif template == "team":
            content += ProjectTemplateService.TEAM_TEMPLATE
        else:  # basic
            content += ProjectTemplateService.BASIC_TEMPLATE

        content += ProjectTemplateService.TEMPLATE_FOOTER
        return content

    @staticmethod
    def load_custom_template(template_path: str) -> str | None:
        """Load custom template from file.

        Args:
            template_path: Path to template file

        Returns:
            Template content if valid, None otherwise
        """
        try:
            tpl_path = Path(template_path)
            if tpl_path.exists() and tpl_path.is_file():
                return tpl_path.read_text()
        except Exception:
            pass
        return None


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
            project_id = core._generate_id()[:8]
            project_filename = (
                f"{project_id}-{core._normalize_filename(project_name)}.md"
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
