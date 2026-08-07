"""Service for generating project templates."""

import getpass
from datetime import UTC, datetime
from pathlib import Path

import structlog

logger = structlog.get_logger()


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
        current_date = datetime.now(UTC).isoformat()
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
        except Exception as e:
            logger.debug(
                "template_load_failed",
                operation="load_template",
                template_path=str(template_path),
                error=str(e),
                action="Returning None",
            )
        return None
